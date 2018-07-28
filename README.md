# ptop

## Model

- Server
  - {`ptop.py`}\*n
  - `ptop-proxy.py` \*1
- Client
  - {`worker-xyz.py`}\*m

## Grafana

## InfluxDB

- set `auth-enabled = true` in `influxdb.conf`

```
create database ptop
use ptop
# create user admin with password 'admin' with all PRIVILEGES
create user grafana with password 'grafana'
grant read on ptop to grafana
create user worker with password 'worker-auth'
grant write on ptop to worker
```
