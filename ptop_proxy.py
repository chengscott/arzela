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
      '-pp',
      '--proxy-port',
      help='SUB_proxy:PUB_worker (default: %(default)s)',
      default='7777:6666',
      type=valid_port)
  parser.add_argument(
      '-bp',
      '--broker-port',
      help='ROUTER_worker:DEALER_broker (default: %(default)s)',
      default='6667:7778',
      type=valid_port)
  args = parser.parse_args()
  # ZMQ forwarder
  ctx = zmq.Context()
  proxy_frontend = ctx.socket(zmq.XSUB)
  proxy_frontend.bind(f'tcp://*:{args.proxy_port[0]}')
  proxy_backend = ctx.socket(zmq.XPUB)
  proxy_backend.bind(f'tcp://*:{args.proxy_port[1]}')
  zmq.proxy(proxy_frontend, proxy_backend)
  # ZMQ proxy
  #broker_frontend = ctx.socket(zmq.ROUTER)
  #broker_frontend.bind(f'tcp://*:{args.broker_port[0]}')
  #broker_backend = ctx.socket(zmq.DEALER)
  #broker_backend.bind(f'tcp://*:{args.broker_port[1]}')
  #zmq.proxy(broker_frontend, broker_backend)
