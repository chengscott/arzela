"""Distributed System Monitor"""
__author__ = 'chengscott'
__version__ = '0.2'
import argparse


def run_proxy(proxy_port):
  from arzela.proxy import Proxy
  proxy = Proxy()
  proxy.bind(proxy_port)


def run_worker(mod, host, sub_port):
  if mod == 'example':
    import arzela.worker.example as worker
  elif mod == 'db':
    import arzela.worker.db as worker
  elif mod == 'net_db':
    import arzela.worker.net_db as worker
  sub_sock = worker.connect(host, sub_port)
  worker.run(sub_sock)


def run_arzela(host, pub_port):
  import platform
  from time import sleep

  from arzela.monitor import Monitor
  node = platform.node().encode('utf-8')
  monitor = Monitor(node)
  monitor.bind(host, pub_port)
  while True:
    monitor.run()
    sleep(1)


def valid_port(port):
  try:
    ports = port.split(':')
    assert (len(ports) == 2)
    return tuple(map(int, ports))
  except:
    raise argparse.ArgumentTypeError('Port has format 7777:6666')


def run_main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument(
      '-v', '--version', action='version', version=f'arzela {__version__}')
  parser.add_argument(
      '-pub',
      '--pub-port',
      help='PUB server (default: %(default)s)',
      default=7777,
      type=int)
  parser.add_argument('--host', help='proxy', default='localhost', type=str)
  subparsers = parser.add_subparsers(dest='command')
  proxy_parser = subparsers.add_parser('proxy')
  proxy_parser.add_argument(
      '-pp',
      '--proxy-port',
      help='SUB_proxy:PUB_worker (default: %(default)s)',
      default='7777:6666',
      type=valid_port)
  worker_parser = subparsers.add_parser('worker')
  worker_parser.add_argument(
      'type',
      help='builtin worker type (default: %(default)s)',
      choices=['db', 'net_db', 'example'])
  worker_parser.add_argument(
      '-sub',
      '--sub-port',
      help='SUB worker (default: %(default)s)',
      default=6666,
      type=int)
  worker_parser.add_argument(
      '--host', help='proxy', default='localhost', type=str)
  args = parser.parse_args()
  if args.command == 'proxy':
    run_proxy(args.proxy_port)
  elif args.command == 'worker':
    run_worker(args.type, args.host, args.sub_port)
  else:
    run_arzela(args.host, args.pub_port)


if __name__ == '__main__':
  run_main()
