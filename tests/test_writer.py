from monitor.writer import DBConnection
from monitor.writer import MetricsWriter


def test_db_connection():
    with DBConnection() as db_connection:
        db_connection.cursor.execute('SELECT 1 = 1;')
        assert db_connection.cursor.fetchone() == (True,)


def test_create_schema():
    MetricsWriter.create_schema()
