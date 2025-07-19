import logging
import os

import yaml


CONFIG_FILE = os.path.expanduser('~/.config/monitor.yaml')


def configure(config_file=None):
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)

    if not os.path.isfile(config_file):
        raise FileNotFoundError(
            f'config file {config_file} not found, unable to start the services'
        )
    with open(config_file, 'r') as file_handle:
        configuration = yaml.load(file_handle, Loader=yaml.FullLoader)

    return configuration


config = configure(CONFIG_FILE)
