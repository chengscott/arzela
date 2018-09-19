#!/usr/bin/env python3.6
import argparse
import json
import zmq


def run(sub_sock):
  while True:
    try:
      [node, raw_data] = sub_sock.recv_multipart()
    except ValueError:
      continue
    node = node.decode('utf-8')
    raw_data = json.loads(raw_data.decode('utf-8'))
    print(f"Received data: {raw_data}")


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
