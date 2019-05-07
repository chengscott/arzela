#!/usr/bin/env python
f'Python >= 3.6 Required'
import argparse
import json
from os import getenv
import requests
import zmq


def run(sub_sock):
  auth = getenv('INFLUX_USERNAME', 'worker'), getenv('INFLUX_PASSWORD')

  def post(req):
    #print(req)
    response = requests.post('http://localhost:8086/write',
                             auth=auth,
                             params={'db': 'arzela'},
                             data=req.encode())

  prev_data = {'cpu_util': {}}
  while True:
    try:
      [node, raw_data] = sub_sock.recv_multipart()
    except ValueError:
      continue
    node = node.decode('utf-8')
    raw_data = json.loads(raw_data.decode('utf-8'))
    print(f'Received data: {raw_data}')
    for item in ['cpu', 'gpu']:
      if item in raw_data:
        for k, stats in raw_data[item].items():
          field_data = ','.join(
              [f'{item}_{i}={v}' for i, v in enumerate(stats)])
          post(f'{item}_{k},host={node} {field_data}')
    if 'memory' in raw_data:
      usage, util = raw_data['memory']['usage'], raw_data['memory']['util']
      post(f'mem_util,host={node} usage={usage},util={util}')
    if 'cpu_util' in raw_data:
      data = list(
          zip(raw_data['cpu_util']['idle'], raw_data['cpu_util']['total']))
      if node not in prev_data['cpu_util']:
        prev_data['cpu_util'][node] = [(0, 0)] * 30
      cpu_util = [
          (1 - (idle - prev_idle) / (total - prev_total)) * 100
          for (idle,
               total), (prev_idle,
                        prev_total) in zip(data, prev_data['cpu_util'][node])
      ]
      prev_data['cpu_util'][node] = data
      field_data = ','.join([f'cpu_{i}={v}' for i, v in enumerate(cpu_util)])
      post(f'cpu_util,host={node} {field_data}')


def connect(host, sub_port, ssh_host):
  ctx = zmq.Context()
  sub_sock = ctx.socket(zmq.SUB)
  sub_sock.setsockopt(zmq.SUBSCRIBE, b'')
  remote = f'tcp://{host}:{sub_port}'
  if ssh_host:
    from zmq import ssh
    ssh.tunnel_connection(sub_sock, remote, ssh_host)
  else:
    sub_sock.connect(remote)
  return sub_sock


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-sub',
                      '--sub-port',
                      help='SUB worker (default: %(default)s)',
                      default=6666,
                      type=int)
  parser.add_argument('--host', help='proxy', default='localhost', type=str)
  parser.add_argument('-ssh', '--ssh-host', help='ssh tunnel', type=str)
  args = parser.parse_args()
  sub_sock = connect(args.host, args.sub_port, args.ssh_host)
  run(sub_sock)
