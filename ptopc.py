#!/usr/bin/env python3.6
import argparse
import platform
import re
import subprocess
from time import sleep
import zmq

ctx = zmq.Context()
sock = ctx.socket(zmq.PUB)
RE_P = re.compile(r'power1_average: (\d+\.\d+)\n')

def monitor_sensors():
  ret = subprocess.run(['sensors', '-u'], check=True, stdout=subprocess.PIPE, encoding='utf-8')
  res = ret.stdout
  match = RE_P.search(res)
  assert(match is not None)
  #temp = [t for line in res if res.search('temp: ', line)]
  return {
    'temp': [0] * 16,
    'power': float(match.group(1))
  }

def monitor_cpu():
  ret = []
  with open('/proc/cpuinfo', 'r') as f:
    ret = [line.split()[3] for line in f if re.search('MHz', line)]
  return ret

def monitor_rapl():
  RAPL_PATH_TEMPLATE = '/sys/devices/virtual/powercap/intel-rapl/intel-rapl:{i}/constraint_0_power_limit_uw'
  ret = []
  for j in range(2):
    with open(RAPL_PATH_TEMPLATE.format(i=j), 'r') as f:
      ret.append(int(f.read()) / 10 ** 6)
  return ret

def monitor_gpu():
  res = subprocess.run(['nvidia-smi',
      '--query-gpu=clocks.applications.gr,power.draw,temperature.gpu', '--format=csv,noheader,nounits'],
      check=True,
      stdout=subprocess.PIPE,
      encoding='utf-8').stdout
  res = [map(float, row.split(", ")) for row in res.splitlines()]
  ret = list(map(list, zip(*res)))
  return dict(zip(['freq', 'power', 'temp'], ret))

def monitor():
  sensors_stat = monitor_sensors()
  return {
    'cpu': {
      'freq': monitor_cpu(),
      'power': monitor_rapl(),
      #'temp': sensors_stat['temp'],
    },
    'gpu': monitor_gpu(),
    'sys': {
      'power': sensors_stat['power'],
    }
  }

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--host', default='localhost', type=str)
  parser.add_argument('-p', '--port', default=6666, type=int)
  args = parser.parse_args()
  sock.connect(f'tcp://{args.host}:{args.port}')
  data = {'host': platform.node()}
  while True:
    data.update(monitor())
    sock.send_json(data)
    break
    sleep(1)
