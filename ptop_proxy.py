#!/usr/bin/env python3.6
import argparse
import zmq


def valid_port(port):
  try:
    ports = port.split(':')
    assert (len(ports) == 2)
    return tuple(map(int, ports))
  except:
    raise argparse.ArgumentTypeError('Port has format 7777:6666')


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '-p',
      '--port',
      help='SUB_proxy:PUB_worker (default: %(default)s)',
      default='7777:6666',
      type=valid_port)
  args = parser.parse_args()
  # ZMQ forwarder device
  ctx = zmq.Context()
  frontend = ctx.socket(zmq.SUB)
  frontend.setsockopt(zmq.SUBSCRIBE, b"")
  frontend.bind(f'tcp://*:{args.port[0]}')
  backend = ctx.socket(zmq.PUB)
  backend.bind(f'tcp://*:{args.port[1]}')
  zmq.device(zmq.FORWARDER, frontend, backend)
