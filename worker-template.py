#!/usr/bin/env python3.6
import argparse
import json
import zmq


def main():
  while True:
    [_, raw_data] = sub_sock.recv_multipart()
    raw_data = json.loads(raw_data.decode('utf-8'))
    print(f"Received data: {raw_data}")


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
  # ZMQ REQ worker
  req_sock = ctx.socket(zmq.REQ)
  req_sock.connect(f'tcp://{args.host}:{args.req_port}')
  main()
