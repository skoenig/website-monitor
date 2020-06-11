# Aiven Website Monitor

_Small conceptual website monitor using Kafka and PostgreSQL._

This tool monitors website availability over the network, produces metrics about this and passes these events through a Kafka instance into a PostgreSQL database.

A Kafka producer periodically checks the target websites and sends the check results (HTTP response time, error code and optionally, whether a regexp pattern was found in the response body) to a Kafka topic, and a Kafka consumer stores the data to a PostgreSQL database.
