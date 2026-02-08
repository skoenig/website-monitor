import json
import logging
import re
import time

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from kafka import KafkaProducer

from monitor.config import config


class MetricsCollector:
    producer = None

    def __init__(self):
        kafka_config = {
            'bootstrap_servers': config['kafka']['host'],
            'retries': 5,
            'value_serializer': lambda x: json.dumps(x).encode('utf-8'),
        }

        # Add SSL-related configuration only if the keys exist in the config
        if 'ssl_certfile' in config['kafka'] and config['kafka']['ssl_certfile']:
            kafka_config['security_protocol'] = 'SSL'
            kafka_config['ssl_check_hostname'] = True
            kafka_config['ssl_certfile'] = config['kafka']['ssl_certfile']
            kafka_config['ssl_keyfile'] = config['kafka']['ssl_keyfile']
            kafka_config['ssl_cafile'] = config['kafka']['ssl_cafile']
        if not self.producer:
            self.producer = KafkaProducer(**kafka_config)

    def run(self, job):
        job['regex'] = job.get('regex', '')
        job['metrics'] = self.collect(job['url'], job['regex'])
        try:
            self.producer.send('metrics', value=job)
        except TimeoutError:
            logging.warning('ran into a timeout while sending message to Kafka')
        else:
            logging.info('sent message %s to Kafka', job)

    @staticmethod
    def collect(url, regex=''):
        result = {}
        try:
            response = requests.get(url)
            if response.ok:
                result = {
                    'response_time': response.elapsed.microseconds,
                    'status_code': response.status_code,
                }

                if regex:
                    result['regex_matched'] = bool(re.search(regex, response.text))

        except ConnectionError:
            logging.warning('network connection failed for url %s', url)

        return result


def monitor():
    collector = MetricsCollector()

    for job in config['websites']:
        collector.run(job)


if __name__ == '__main__':
    scheduler = BackgroundScheduler(deamon=True)
    scheduler.add_job(monitor, 'interval', seconds=config['check_interval'])

    scheduler.start()
    try:
        # keep the main thread alive
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
