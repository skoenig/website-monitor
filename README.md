# Aiven Website Monitor

_Small conceptual website monitor using Kafka and PostgreSQL._

This tool monitors website availability over the network, produces metrics about this and passes these events through a Kafka instance into a PostgreSQL database.

A Kafka producer periodically checks (using [APScheduler](https://apscheduler.readthedocs.io/en/stable/)) the monitored websites and fetches following metrics:
- HTTP response time in microseconds
- HTTP status code
- boolean, whether a configured regexp pattern was found in the response body (optional)

These result will be sent to a Kafka topic, and written to a PostgreSQL database by a Kafka consumer.

[![License](http://img.shields.io/:license-mit-blue.svg?style=flat-square)](http://badges.mit-license.org)

## Prerequisites
You will need a Kafka instance with certificate/SSL authentication enabled.

It is also assumed that you have a running PostgreSQL database which provides the [TimescaleDB](https://www.timescale.com/) extension and a user that has all privileges on a database called `metrics`.

## Installation
You will need [Poetry](https://python-poetry.org/) to install this tool. Install dependencies and pre-commit hooks:

    make install

The configuration for both the Kafka producer and consumer is expected in `~/.config/monitor.yaml`, copy the [example config](monitor.example-config.yaml) as a starting point:

    cp monitor.example-config.yaml ~/.config/monitor.yaml

The database writer will create the needed tables with [schema.sql](schema.sql) on startup.

## Usage example

Run the collector: `poetry run python3 -m monitor.collector`

Run the database writer: `poetry run python3 -m monitor.writer`

## Development

With the virtualenv created by Poetry you should have a complete development environment.

Make sure to commit from within the Poetry virtualenv:

    poetry shell

## Contributing

1. Fork it (`<https://github.com/skoenig/aiven-website-monitor/fork>`)
2. Create your feature branch (`git checkout -b feature/my_feature`)
3. Commit your changes (`git commit -am 'implemented feature xyz'`)
4. Push to the branch (`git push origin feature/my_feature`)
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE file](LICENSE) for details
