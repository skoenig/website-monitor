import pytest
import yaml

from monitor.config import config
from monitor.config import configure


def test_config_type():
    assert type(config) is dict


def test_nonexistent_file():
    with pytest.raises(FileNotFoundError):
        configure('/tmp/foobar.yaml')


def test_configure_success(tmp_path):
    # Create a temporary dummy config file
    dummy_config_path = tmp_path / 'monitor_test.yaml'
    dummy_content = {
        'kafka': {
            'host': 'dummy_kafka:9092',
            'ssl_certfile': '',
            'ssl_keyfile': '',
            'ssl_cafile': '',
        },
        'database': {
            'host': 'dummy_db',
            'port': 5432,
            'user': 'monitor',
            'password': 'password',
            'dbname': 'monitor',
        },
        'jobs': [],
    }
    with open(dummy_config_path, 'w') as f:
        yaml.dump(dummy_content, f)

    # Configure with the dummy file
    loaded_config = configure(str(dummy_config_path))

    # Assert that the loaded config matches the dummy content
    assert loaded_config == dummy_content
    assert loaded_config['kafka']['host'] == 'dummy_kafka:9092'
    assert loaded_config['database']['user'] == 'monitor'
