#!/usr/bin/env python3.6
import argparse
import json
import platform
import re
import subprocess
from time import sleep
import zmq

SENSORS_POWER = re.compile(r'power1_average: (\d+\.\d+)')
SENSORS_TEMP = re.compile(r'temp\d+_input: (\d+\.\d+)')


def monitor_sensors():
  res = subprocess.run(
      ['sensors', '-u'], check=True, stdout=subprocess.PIPE,
      encoding='utf-8').stdout
  return {
      'temp': list(map(float, SENSORS_TEMP.findall(res))),
      'power': sum(map(float, SENSORS_POWER.findall(res)))
  }


CPU_FREQ = re.compile(r'cpu MHz\t\t: (\d+\.\d+)')


def monitor_cpu():
  ret = []
  with open('/proc/cpuinfo', 'r') as f:
    ret.extend(map(float, CPU_FREQ.findall(f.read())))
  return ret


def monitor_rapl():
  RAPL_PATH = '/sys/devices/virtual/powercap/intel-rapl/intel-rapl:{i}/constraint_0_power_limit_uw'
  ret = []
  for j in range(2):
    with open(RAPL_PATH.format(i=j), 'r') as f:
      ret.append(int(f.read()) / 10**6)
  return ret


GPU_QUERY = {
    'freq': 'clocks.applications.gr',
    'power': 'power.draw',
    'temp': 'temperature.gpu',
    'gpu_util': 'utilization.gpu',
    'mem_util': 'utilization.memory',
}
NVIDIA_SMI_QUERY = ','.join(GPU_QUERY.values())


def monitor_gpu():
  # nvidia-smi stats -d pwrDraw,temp,gpuUtil,memUtil
  res = subprocess.run(
      [
          'nvidia-smi', f'--query-gpu={NVIDIA_SMI_QUERY}',
          '--format=csv,noheader,nounits'
      ],
      check=True,
      stdout=subprocess.PIPE,
      encoding='utf-8').stdout
  res = [map(float, row.split(", ")) for row in res.splitlines()]
  ret = list(map(list, zip(*res)))
  return dict(zip(GPU_QUERY.keys(), ret))


IB_COUNTERS = {
    'rx_data': 'port_rcv_data',
    'tx_data': 'port_xmit_data',
}


def monitor_infiniband():
  IB_PATH = '/sys/class/infiniband/mlx4_0/ports/{port}/counters/{counter}'
  ret = {}
  for k, v in IB_COUNTERS.items():
    with open(IB_PATH.format(port=1, counter=v), 'r') as f:
      ret.update({k: int(f.read())})
  return ret


def monitor_netdev():
  ret = {}
  with open('/proc/net/dev', 'r') as f:
    f.readline()
    f.readline()
    for eth in f:
      eth = eth.split()
      ret.update({eth[0]: {'rx_data': eth[1], 'tx_data': eth[9]}})
  return ret


def monitor_free_disk():
  ret = {}
  res = subprocess.run(
      ['df', '-h'], check=True, stdout=subprocess.PIPE,
      encoding='utf-8').stdout
  for part in res.splitlines():
    part = part.split()
    if part[5] in ['/', '/home/shared']:
      ret.update({
          part[5]: {
              'usage': int(part[4][:-1]),
              'avail': part[3][:-1]
          }
      })
  return ret


def monitor():
  sensors_stat = monitor_sensors()
  return {
      'cpu': {
          'freq': monitor_cpu(),
          'power': monitor_rapl(),
          'temp': sensors_stat['temp'],
      },
      'gpu': monitor_gpu(),
      'sys': {
          'power': sensors_stat['power'],
      },
      #'ib': monitor_infiniband(),
      #'net': monitor_netdev(),
      #'disk': monitor_free_disk(),
  }


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '-pub',
      '--pub-port',
      help='PUB server (default: %(default)s)',
      default=7777,
      type=int)
  parser.add_argument(
      '-rep',
      '--rep-port',
      help='REP server (default: %(default)s)',
      default=7778,
      type=int)
  parser.add_argument('--host', help='proxy', default='localhost', type=str)
  args = parser.parse_args()
  # ZMQ PUB server
  ctx = zmq.Context()
  pub_sock = ctx.socket(zmq.PUB)
  pub_sock.connect(f'tcp://{args.host}:{args.pub_port}')
  rep_sock = ctx.socket(zmq.REP)
  rep_sock.connect(f'tcp://{args.host}:{args.rep_port}')
  node = platform.node().encode('utf-8')
  data = {}
  while True:
    data.update(monitor())
    pub_sock.send_multipart([node, json.dumps(data).encode('utf-8')])
    sleep(1)
