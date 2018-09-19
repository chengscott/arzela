#!/usr/bin/env python3.6
import argparse
import json
import requests
import zmq


def run(sub_sock):
  def post(req):
    print(req)
    response = requests.post(
        'http://localhost:8086/write',
        auth=('worker', 'nthu-scc'),
        params={'db': 'arzela'},
        data=req.encode())

  prev_data = {}
  while True:
    try:
      [node, raw_data] = sub_sock.recv_multipart()
    except ValueError:
      continue
    node = node.decode('utf-8')
    raw_data = json.loads(raw_data.decode('utf-8'))
    print(f"Received data: {raw_data}")
    data = {
        f'{item},host={node},interface={name}': (net['rx_data'],
                                                 net['tx_data'])
        for item in ['eth', 'ib'] if item in raw_data
        for name, net in raw_data[item].items()
    }
    if node not in prev_data:
      prev_data[node] = data
    for key, (rx, tx) in data.items():
      prev_rx, prev_tx = prev_data[node][key]
      drx, dtx = rx - prev_rx, tx - prev_tx
      post(f'{key} rx={drx},tx={dtx}')
    prev_data[node] = data


def connect(host, sub_port):
  ctx = zmq.Context()
  sub_sock = ctx.socket(zmq.SUB)
  sub_sock.setsockopt(zmq.SUBSCRIBE, b"")
  sub_sock.connect(f'tcp://{host}:{sub_port}')
  return sub_sock


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '-sub',
      '--sub-port',
      help='SUB worker (default: %(default)s)',
      default=6666,
      type=int)
  parser.add_argument('--host', help='proxy', default='localhost', type=str)
  args = parser.parse_args()
  sub_sock = connect(args.host, args.sub_port)
  run(sub_sock)
