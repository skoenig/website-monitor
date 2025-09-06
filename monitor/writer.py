import json
import logging

import psycopg2
from kafka import KafkaConsumer

from monitor.config import config


class MetricsWriter:
    consumer = None

    def __init__(self):
        kafka_config = {
            'bootstrap_servers': config['kafka']['host'],
            'auto_offset_reset': 'earliest',
            'enable_auto_commit': True,
            'group_id': 'website-monitor',
            'value_deserializer': lambda x: json.loads(x.decode('utf-8')),
        }

        # Add SSL-related configuration only if the keys exist in the config
        if 'ssl_certfile' in config['kafka'] and config['kafka']['ssl_certfile']:
            kafka_config['security_protocol'] = 'SSL'
            kafka_config['ssl_check_hostname'] = True
            kafka_config['ssl_certfile'] = config['kafka']['ssl_certfile']
            kafka_config['ssl_keyfile'] = config['kafka']['ssl_keyfile']
            kafka_config['ssl_cafile'] = config['kafka']['ssl_cafile']

        if not self.consumer:
            self.consumer = KafkaConsumer(**kafka_config)

    @staticmethod
    def create_schema():
        with DBConnection() as db, open('schema.sql') as fh:
            schema = fh.read()
            db.cursor.execute(schema)
            db.connection.commit()

    @staticmethod
    def get_job_id(db, message):
        query_insert_job = """INSERT INTO jobs (url, regex) VALUES (%(url)s, %(regex)s)
        ON CONFLICT DO NOTHING RETURNING id;"""
        query_select_job = (
            """SELECT id FROM jobs WHERE url = %(url)s AND regex = %(regex)s;"""
        )

        db.cursor.execute(query_insert_job, message.value)
        job = db.cursor.fetchone()
        if not job:
            db.cursor.execute(query_select_job, message.value)
            job = db.cursor.fetchone()
        return job[0]

    @staticmethod
    def insert_metric(db, metrics):
        if 'regex_matched' in metrics:
            query_insert_metric = """INSERT INTO metrics (
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
        else:
            query_insert_metric = """INSERT INTO metrics (
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

        db.cursor.execute(query_insert_metric, metrics)

    def run(self):
        self.consumer.subscribe(['metrics'])
        with DBConnection() as db:
            for message in self.consumer:
                logging.info(
                    '%s:%d:%d:%d: key=%s value=%s',
                    message.topic,
                    message.partition,
                    message.offset,
                    message.timestamp,
                    message.key,
                    message.value,
                )

                job_id = self.get_job_id(db, message)
                metrics = message.value['metrics']
                metrics['job_id'] = job_id
                metrics['timestamp'] = message.timestamp

                self.insert_metric(db, metrics)

                db.connection.commit()
        self.consumer.close()


class DBConnection:
    def __init__(self):
        self.connection = None
        self.cursor = None

    def __enter__(self):
        self.connection = psycopg2.connect(config['postgres']['uri'])
        self.cursor = self.connection.cursor()
        return self

    def __exit__(self, exception_type, exception_val, trace):
        self.connection.close()
        self.cursor.close()


if __name__ == '__main__':
    writer = MetricsWriter()
    writer.create_schema()
    writer.run()
