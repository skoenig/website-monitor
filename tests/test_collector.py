import pytest
from unittest.mock import MagicMock

from monitor.collector import MetricsCollector
from monitor.config import config as global_config


@pytest.fixture(autouse=True)
def reset_collector_producer():
    """Auto-use fixture to reset the class-level producer for test isolation"""
    original_producer = MetricsCollector.producer
    MetricsCollector.producer = None
    yield
    MetricsCollector.producer = original_producer


@pytest.fixture
def mock_kafka_producer_class(mocker):
    """Fixture for mocking the KafkaProducer class"""
    mock_producer_class = mocker.patch('monitor.collector.KafkaProducer')
    return mock_producer_class


@pytest.fixture
def mock_requests_get_func(mocker):
    """Fixture for mocking requests.get with a default successful response"""
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.elapsed.microseconds = 100000
    mock_response.text = '<html><body>Hello, world!</body></html>'
    mock_get = mocker.patch(
        'monitor.collector.requests.get', return_value=mock_response
    )
    return mock_get


def test_collector_init(mock_kafka_config, mock_kafka_producer_class, mocker):
    mocker.patch.dict(global_config, mock_kafka_config)
    collector = MetricsCollector()
    mock_kafka_producer_class.assert_called_once_with(
        bootstrap_servers=mock_kafka_config['kafka']['host'],
        retries=5,
        value_serializer=mocker.ANY,
    )
    assert collector.producer == mock_kafka_producer_class.return_value


def test_collector_collect_success(mock_requests_get_func):
    url = 'https://example.com'
    result = MetricsCollector.collect(url)
    mock_requests_get_func.assert_called_once_with(url)
    assert result == {
        'response_time': 100000,
        'status_code': 200,
    }


def test_collector_collect_with_regex_match(mock_requests_get_func, mocker):
    mock_re_search = mocker.patch(
        'monitor.collector.re.search', return_value=MagicMock()
    )
    url = 'https://example.com'
    regex = 'Hello'
    result = MetricsCollector.collect(url, regex)
    mock_requests_get_func.assert_called_once_with(url)
    assert result == {
        'response_time': 100000,
        'status_code': 200,
        'regex_matched': True,
    }
    mock_re_search.assert_called_once_with(
        regex, mock_requests_get_func.return_value.text
    )


def test_collector_collect_with_regex_no_match(mock_requests_get_func, mocker):
    mock_re_search = mocker.patch('monitor.collector.re.search', return_value=None)
    url = 'https://example.com'
    regex = 'Goodbye'
    result = MetricsCollector.collect(url, regex)
    mock_requests_get_func.assert_called_once_with(url)
    assert result == {
        'response_time': 100000,
        'status_code': 200,
        'regex_matched': False,
    }
    mock_re_search.assert_called_once_with(
        regex, mock_requests_get_func.return_value.text
    )


def test_collector_collect_connection_error(mocker):
    mock_requests_get = mocker.patch(
        'monitor.collector.requests.get',
        side_effect=ConnectionError('Failed to connect'),
    )
    mock_logging_warning = mocker.patch('monitor.collector.logging.warning')
    url = 'https://example.com'
    result = MetricsCollector.collect(url)
    mock_requests_get.assert_called_once_with(url)
    assert result == {}
    mock_logging_warning.assert_called_once_with(
        'network connection failed for url %s', url
    )


def test_collector_collect_non_ok_response(mocker):
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.status_code = 404
    mock_response.elapsed.microseconds = 50000
    mock_response.text = 'Page Not Found'
    mock_requests_get = mocker.patch(
        'monitor.collector.requests.get', return_value=mock_response
    )
    url = 'https://example.com/nonexistent'
    result = MetricsCollector.collect(url)
    mock_requests_get.assert_called_once_with(url)
    assert result == {}, (
        'MetricsCollector should return an empty dict for non-OK HTTP responses'
    )


def test_collector_run_success(mock_kafka_config, mock_kafka_producer_class, mocker):
    mocker.patch.dict(global_config, mock_kafka_config)
    mock_logging_info = mocker.patch('monitor.collector.logging.info')

    collector = MetricsCollector()
    job = {'url': 'https://test.com', 'name': 'Test Job'}
    expected_metrics = {
        'response_time': 100000,
        'status_code': 200,
    }
    mocker.patch.object(collector, 'collect', return_value=expected_metrics)

    collector.run(job)

    collector.collect.assert_called_once_with(job['url'], '')

    expected_job_value = job.copy()
    expected_job_value['regex'] = ''
    expected_job_value['metrics'] = expected_metrics
    mock_kafka_producer_class.return_value.send.assert_called_once_with(
        'metrics', value=expected_job_value
    )

    mock_logging_info.assert_called_once_with(
        'sent message %s to Kafka', expected_job_value
    )


def test_collector_run_kafka_timeout(
    mock_kafka_config, mock_kafka_producer_class, mocker
):
    mocker.patch.dict(global_config, mock_kafka_config)
    mock_logging_warning = mocker.patch('monitor.collector.logging.warning')

    collector = MetricsCollector()
    job = {'url': 'https://test.com', 'name': 'Test Job'}

    mock_kafka_producer_class.return_value.send.side_effect = TimeoutError(
        'Kafka send timed out'
    )

    mocker.patch.object(
        collector, 'collect', return_value={'response_time': 50000, 'status_code': 200}
    )

    collector.run(job)

    mock_kafka_producer_class.return_value.send.assert_called_once()

    mock_logging_warning.assert_called_once_with(
        'ran into a timeout while sending message to Kafka'
    )
