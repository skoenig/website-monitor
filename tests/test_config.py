import pytest

from monitor.config import config
from monitor.config import configure


def test_config_type():

    assert type(config) == dict


def test_nonexistent_file():
    with pytest.raises(FileNotFoundError):
        configure("/tmp/foobar.yaml")
