# pymon

## Installation

```shell
pip install pymon
```

## Model

- Server
  - {`pymon`}\*n
  - `pymon proxy` \*1
- Client
  - {`pymon worker example`}\*m
  - or a customized one

## Grafana

## InfluxDB

- set `auth-enabled = true` in `influxdb.conf`

```
create database pymon
use pymon
# create user admin with password 'admin' with all PRIVILEGES
create user grafana with password 'grafana'
grant read on pymon to grafana
create user worker with password 'worker-password'
grant write on pymon to worker
```
