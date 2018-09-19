# arzela

## Installation

```shell
pip install arzela
```

## Model

- Server
  - {`arzela`}\*n
  - `arzela proxy` \*1
- Client
  - {`arzela worker example`}\*m
  - or a customized one

## Grafana

## InfluxDB

- set `auth-enabled = true` in `influxdb.conf`

```
create database arzela
use arzela
# create user admin with password 'admin' with all PRIVILEGES
create user grafana with password 'grafana'
grant read on arzela to grafana
create user worker with password 'ascoli'
grant write on arzela to worker
```
