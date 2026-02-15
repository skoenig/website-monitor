import pytest


@pytest.fixture
def mock_kafka_config():
    """Fixture for mocking a basic global Kafka configuration (non-SSL)."""
    return {
        'kafka': {
            'host': 'localhost:9092',
            'ssl_certfile': '',
            'ssl_keyfile': '',
            'ssl_cafile': '',
        }
    }
