#!/usr/bin/env python3.6
import argparse
import zmq


def main():
  while True:
    raw_data = sock.recv_json()
    print(f"Received data: {raw_data}")


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
