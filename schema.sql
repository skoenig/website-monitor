CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

CREATE TABLE IF NOT EXISTS jobs (
    id      SERIAL PRIMARY KEY,
    url     TEXT    NOT NULL,
    regex   TEXT    NULL,
    UNIQUE (url, regex)
);

CREATE TABLE IF NOT EXISTS metrics (
    time            TIMESTAMPTZ(3)  NOT NULL,
    response_time   INTEGER         NOT NULL,
    status_code     SMALLINT        NOT NULL,
    regex_matched   BOOL            NULL,
    job_id          SERIAL REFERENCES jobs(id)
);

SELECT create_hypertable('metrics', 'time', if_not_exists => TRUE);
