#!/usr/bin/env python3.6
import argparse
import json
import requests
import zmq


def main():
  while True:
    [node, raw_data] = sock.recv_multipart()
    node = node.decode('utf-8')
    raw_data = json.loads(raw_data.decode('utf-8'))
    print(f"Received data: {raw_data}")
    for item in ['cpu', 'gpu']:
      for k, stats in raw_data[item].items():
        field_data = ','.join([f'{item}_{i}={v}' for i, v in enumerate(stats)])
        data = f'{item}_{k},host={node} {field_data}'
        #print(data)
        response = requests.post('http://localhost:8086/write', params={'db': 'ptopdb'}, data=data.encode())


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '-p', '--port', help='SUB worker', default=6666, type=int)
  parser.add_argument(
      '--host', help='PUB proxy', default='localhost', type=str)
  args = parser.parse_args()
  # ZMQ SUB worker
  ctx = zmq.Context()
  sock = ctx.socket(zmq.SUB)
  sock.setsockopt(zmq.SUBSCRIBE, b"")
  sock.connect(f'tcp://{args.host}:{args.port}')
  main()
