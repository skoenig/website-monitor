import pytest
from unittest.mock import MagicMock, mock_open

from monitor.writer import DBConnection, MetricsWriter
from monitor.config import config as global_config


@pytest.fixture
def mock_postgres_config():
    """Returns a PostgreSQL configuration for DBConnection initialization."""
    return {'postgres': {'uri': 'postgresql://user:pass@host:5432/dbname_test'}}


@pytest.fixture
def mock_kafka_consumer_class(mocker):
    """Mocks the KafkaConsumer class used in MetricsWriter."""
    mock_consumer_class = mocker.patch('monitor.writer.KafkaConsumer')
    mock_consumer_instance = MagicMock()
    mock_consumer_class.return_value = mock_consumer_instance
    return mock_consumer_class


@pytest.fixture
def mock_psycopg2_connect(mocker):
    """Mocks psycopg2.connect and its return value (connection and cursor)."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.commit = MagicMock()
    mock_conn.close = MagicMock()
    mock_cursor.close = MagicMock()
    patched_connect_func = mocker.patch(
        'monitor.writer.psycopg2.connect', return_value=mock_conn
    )
    patched_connect_func.mock_cursor_obj = mock_cursor
    return patched_connect_func


@pytest.fixture
def mock_db_connection_class(mocker, mock_postgres_config):
    """Mocks the DBConnection class as a context manager."""
    mocker.patch.dict(global_config, mock_postgres_config)

    mock_db_conn_instance = MagicMock()
    mock_db_conn_instance.connection = MagicMock()
    mock_db_conn_instance.cursor = MagicMock()

    mock_db_class = mocker.patch('monitor.writer.DBConnection')
    mock_db_class.return_value.__enter__.return_value = mock_db_conn_instance
    mock_db_class.return_value.__exit__.return_value = (
        None  # No exception handling in __exit__ by default
    )
    return mock_db_class


def test_db_connection(mock_psycopg2_connect, mock_postgres_config, mocker):
    """Tests that DBConnection establishes and closes a connection correctly."""
    mocker.patch.dict(global_config, {'postgres': mock_postgres_config['postgres']})

    with DBConnection() as db_connection:
        db_connection.cursor.execute('SELECT 1 = 1;')
        db_connection.cursor.fetchone.return_value = (True,)
        assert db_connection.cursor.fetchone() == (True,)

        mock_psycopg2_connect.assert_called_once_with(
            mock_postgres_config['postgres']['uri']
        )
        mock_psycopg2_connect.return_value.cursor.assert_called_once()
        db_connection.cursor.execute.assert_called_once_with('SELECT 1 = 1;')
        db_connection.cursor.fetchone.assert_called_once()

    mock_psycopg2_connect.return_value.close.assert_called_once()
    mock_psycopg2_connect.mock_cursor_obj.close.assert_called_once()


def test_create_schema(mock_db_connection_class, mocker):
    """Tests that create_schema reads the schema file and executes it."""
    mock_file_content = 'CREATE TABLE jobs (id SERIAL PRIMARY KEY);'
    mock_open_func = mocker.patch(
        'builtins.open', mock_open(read_data=mock_file_content)
    )

    MetricsWriter.create_schema()

    mock_db_instance = mock_db_connection_class.return_value.__enter__.return_value

    mock_open_func.assert_called_once_with('schema.sql')
    mock_open_func().read.assert_called_once()
    mock_db_instance.cursor.execute.assert_called_once_with(mock_file_content)
    mock_db_instance.connection.commit.assert_called_once()


def test_kafka_connection(mock_kafka_config, mock_kafka_consumer_class, mocker):
    """Tests that MetricsWriter initializes KafkaConsumer correctly."""
    mocker.patch.dict(global_config, mock_kafka_config)
    writer = MetricsWriter()

    mock_kafka_consumer_class.assert_called_once_with(
        bootstrap_servers=mock_kafka_config['kafka']['host'],
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id='website-monitor',
        value_deserializer=mocker.ANY,
    )

    assert writer.consumer == mock_kafka_consumer_class.return_value

    writer.consumer.topics.return_value = {'metrics'}
    assert writer.consumer.topics() == {'metrics'}
    writer.consumer.topics.assert_called_once()

    writer.consumer.close()
    writer.consumer.close.assert_called_once()


def test_get_job_id_new_job(mock_db_connection_class):
    """Tests get_job_id when a new job is inserted."""
    mock_db = mock_db_connection_class.return_value.__enter__.return_value
    mock_message = MagicMock()
    mock_message.value = {'url': 'http://new.com', 'regex': ''}
    new_job_id = 101

    mock_db.cursor.fetchone.return_value = (new_job_id,)

    job_id = MetricsWriter.get_job_id(mock_db, mock_message)

    expected_insert_query = """INSERT INTO jobs (url, regex) VALUES (%(url)s, %(regex)s)
        ON CONFLICT DO NOTHING RETURNING id;"""
    mock_db.cursor.execute.assert_called_once_with(
        expected_insert_query, mock_message.value
    )
    mock_db.cursor.fetchone.assert_called_once()
    assert job_id == new_job_id


def test_get_job_id_existing_job(mock_db_connection_class):
    """Tests get_job_id when a job already exists."""
    mock_db = mock_db_connection_class.return_value.__enter__.return_value
    mock_message = MagicMock()
    mock_message.value = {'url': 'http://existing.com', 'regex': 'test'}
    existing_job_id = 202

    mock_db.cursor.fetchone.side_effect = [None, (existing_job_id,)]

    job_id = MetricsWriter.get_job_id(mock_db, mock_message)

    expected_insert_query = """INSERT INTO jobs (url, regex) VALUES (%(url)s, %(regex)s)
        ON CONFLICT DO NOTHING RETURNING id;"""
    expected_select_query = (
        """SELECT id FROM jobs WHERE url = %(url)s AND regex = %(regex)s;"""
    )

    # Verify calls in order
    calls = mock_db.cursor.execute.call_args_list
    assert len(calls) == 2
    assert calls[0].args == (expected_insert_query, mock_message.value)
    assert calls[1].args == (expected_select_query, mock_message.value)

    assert mock_db.cursor.fetchone.call_count == 2
    assert job_id == existing_job_id


def test_insert_metric_no_regex(mock_db_connection_class):
    """Tests insert_metric for metrics without regex_matched."""
    mock_db = mock_db_connection_class.return_value.__enter__.return_value
    metrics = {
        'job_id': 1,
        'timestamp': 1678886400000,
        'response_time': 150000,
        'status_code': 200,
    }
    MetricsWriter.insert_metric(mock_db, metrics)

    expected_query = """INSERT INTO metrics (
                        job_id,
                        time,
                        response_time,
                        status_code
                    ) VALUES (
                        %(job_id)s,
                        to_timestamp(%(timestamp)s/1000),
                        %(response_time)s,
                        %(status_code)s
                    );
                """
    mock_db.cursor.execute.assert_called_once_with(expected_query, metrics)


def test_insert_metric_with_regex(mock_db_connection_class):
    """Tests insert_metric for metrics including regex_matched."""
    mock_db = mock_db_connection_class.return_value.__enter__.return_value
    metrics = {
        'job_id': 2,
        'timestamp': 1678886400000,
        'response_time': 200000,
        'status_code': 200,
        'regex_matched': True,
    }
    MetricsWriter.insert_metric(mock_db, metrics)

    expected_query = """INSERT INTO metrics (
                        job_id,
                        time,
                        response_time,
                        status_code,
                        regex_matched
                    ) VALUES (
                        %(job_id)s,
                        to_timestamp(%(timestamp)s/1000),
                        %(response_time)s,
                        %(status_code)s,
                        %(regex_matched)s
                    );
                """
    mock_db.cursor.execute.assert_called_once_with(expected_query, metrics)


def test_writer_run_single_message(
    mock_kafka_config, mock_kafka_consumer_class, mock_db_connection_class, mocker
):
    """Tests MetricsWriter.run processing a single Kafka message."""
    mocker.patch.dict(global_config, mock_kafka_config)
    mock_logging_info = mocker.patch('monitor.writer.logging.info')

    # Configure the mocked consumer to yield one message
    mock_message = MagicMock()
    mock_message.topic = 'metrics'
    mock_message.partition = 0
    mock_message.offset = 123
    mock_message.timestamp = 1678886400000
    mock_message.key = b'some_key'
    mock_message.value = {
        'url': 'http://example.com',
        'regex': '',
        'metrics': {'response_time': 100000, 'status_code': 200},
    }
    mock_kafka_consumer_class.return_value.__iter__.return_value = [mock_message]

    mock_db = mock_db_connection_class.return_value.__enter__.return_value
    mocker.patch.object(MetricsWriter, 'get_job_id', return_value=1)
    mocker.patch.object(MetricsWriter, 'insert_metric')

    writer = MetricsWriter()
    writer.run()

    writer.consumer.subscribe.assert_called_once_with(['metrics'])
    mock_logging_info.assert_called_once()
    writer.consumer.close.assert_called_once()

    MetricsWriter.get_job_id.assert_called_once_with(mock_db, mock_message)
    expected_metrics_for_insert = {
        'response_time': 100000,
        'status_code': 200,
        'job_id': 1,
        'timestamp': 1678886400000,
    }
    MetricsWriter.insert_metric.assert_called_once_with(
        mock_db, expected_metrics_for_insert
    )
    mock_db.connection.commit.assert_called_once()


def test_writer_run_multiple_messages(
    mock_kafka_config, mock_kafka_consumer_class, mock_db_connection_class, mocker
):
    """Tests MetricsWriter.run processing multiple Kafka messages."""
    mocker.patch.dict(global_config, mock_kafka_config)
    mocker.patch('monitor.writer.logging.info')

    # Configure the mocked consumer to yield two messages
    mock_message_1 = MagicMock()
    mock_message_1.topic = 'metrics'
    mock_message_1.partition = 0
    mock_message_1.offset = 123
    mock_message_1.timestamp = 1678886400000
    mock_message_1.key = b'key1'
    mock_message_1.value = {
        'url': 'http://example1.com',
        'regex': '',
        'metrics': {'response_time': 100, 'status_code': 200},
    }

    mock_message_2 = MagicMock()
    mock_message_2.topic = 'metrics'
    mock_message_2.partition = 0
    mock_message_2.offset = 124
    mock_message_2.timestamp = 1678886401000
    mock_message_2.key = b'key2'
    mock_message_2.value = {
        'url': 'http://example2.com',
        'regex': 'foo',
        'metrics': {'response_time': 200, 'status_code': 404, 'regex_matched': False},
    }
    mock_kafka_consumer_class.return_value.__iter__.return_value = [
        mock_message_1,
        mock_message_2,
    ]

    mock_db = mock_db_connection_class.return_value.__enter__.return_value
    mocker.patch.object(MetricsWriter, 'get_job_id', side_effect=[1, 2])
    mocker.patch.object(MetricsWriter, 'insert_metric')

    writer = MetricsWriter()
    writer.run()

    writer.consumer.subscribe.assert_called_once_with(['metrics'])
    writer.consumer.close.assert_called_once()

    assert MetricsWriter.get_job_id.call_count == 2
    MetricsWriter.get_job_id.assert_any_call(mock_db, mock_message_1)
    MetricsWriter.get_job_id.assert_any_call(mock_db, mock_message_2)

    assert MetricsWriter.insert_metric.call_count == 2
    expected_metrics_1 = {
        'response_time': 100,
        'status_code': 200,
        'job_id': 1,
        'timestamp': 1678886400000,
    }
    MetricsWriter.insert_metric.assert_any_call(mock_db, expected_metrics_1)

    expected_metrics_2 = {
        'response_time': 200,
        'status_code': 404,
        'regex_matched': False,
        'job_id': 2,
        'timestamp': 1678886401000,
    }
    MetricsWriter.insert_metric.assert_any_call(mock_db, expected_metrics_2)
    assert mock_db.connection.commit.call_count == 2
