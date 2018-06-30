#!/usr/bin/env python3.6
import argparse
import json
import requests
import zmq


def main():
  while True:
    [node, raw_data] = sub_sock.recv_multipart()
    node = node.decode('utf-8')
    raw_data = json.loads(raw_data.decode('utf-8'))
    print(f"Received data: {raw_data}")
    for item in ['cpu', 'gpu']:
      for k, stats in raw_data[item].items():
        field_data = ','.join([f'{item}_{i}={v}' for i, v in enumerate(stats)])
        data = f'{item}_{k},host={node} {field_data}'
        #print(data)
        response = requests.post(
            'http://localhost:8086/write',
            params={'db': 'ptopdb'},
            data=data.encode())


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '-sub',
      '--sub-port',
      help='SUB worker (default: %(default)s)',
      default=6666,
      type=int)
  parser.add_argument(
      '-req',
      '--req-port',
      help='REQ worker (default: %(default)s)',
      default=6667,
      type=int)
  parser.add_argument('--host', help='proxy', default='localhost', type=str)
  args = parser.parse_args()
  # ZMQ SUB worker
  ctx = zmq.Context()
  sub_sock = ctx.socket(zmq.SUB)
  sub_sock.setsockopt(zmq.SUBSCRIBE, b"")
  sub_sock.connect(f'tcp://{args.host}:{args.sub_port}')
  main()
