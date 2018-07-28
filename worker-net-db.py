#!/usr/bin/env python3.6
import argparse
import json
import requests
import zmq


def main():
  prev_data = {}
  while True:
    try:
      [node, raw_data] = sub_sock.recv_multipart()
    except ValueError:
      continue
    node = node.decode('utf-8')
    raw_data = json.loads(raw_data.decode('utf-8'))
    #print(f"Received data: {raw_data}")
    data = {
        f'{types},host={node},interface={name}': (int(net['rx_data']), int(net['tx_data']))
        for types in ['eth', 'ib'] for name, net in raw_data[types].items()
    }
    if list(data.keys())[0] not in prev_data:
      prev_data.update(data)
    for key, (rx, tx) in data.items():
      prev_rx, prev_tx = prev_data[key]
      drx, dtx = rx - prev_rx, tx - prev_tx
      req = f'{key} rx={drx},tx={dtx}'
      print(req)
      response = requests.post(
            'http://localhost:8086/write',
            auth=('worker', 'nthu-scc'),
            params={'db': 'ptop'},
            data=req.encode())
    prev_data.update(data)


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
  # ZMQ SUB worker
  ctx = zmq.Context()
  sub_sock = ctx.socket(zmq.SUB)
  sub_sock.setsockopt(zmq.SUBSCRIBE, b"")
  sub_sock.connect(f'tcp://{args.host}:{args.sub_port}')
  main()
