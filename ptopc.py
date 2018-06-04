#!/usr/bin/env python3.6
import argparse
import platform
import re
import subprocess
from time import sleep
import zmq

SENSORS_POWER = re.compile(r'power1_average: (\d+\.\d+)')
SENSORS_TEMP = re.compile(r'temp\d+_input: (\d+\.\d+)')
def monitor_sensors():
  res = subprocess.run(['sensors', '-u'], check=True, stdout=subprocess.PIPE, encoding='utf-8').stdout
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
  RAPL_PATH_TEMPLATE = '/sys/devices/virtual/powercap/intel-rapl/intel-rapl:{i}/constraint_0_power_limit_uw'
  ret = []
  for j in range(2):
    with open(RAPL_PATH_TEMPLATE.format(i=j), 'r') as f:
      ret.append(int(f.read()) / 10 ** 6)
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
  res = subprocess.run(['nvidia-smi',
      f'--query-gpu={NVIDIA_SMI_QUERY}', '--format=csv,noheader,nounits'],
      check=True,
      stdout=subprocess.PIPE,
      encoding='utf-8').stdout
  res = [map(float, row.split(", ")) for row in res.splitlines()]
  ret = list(map(list, zip(*res)))
  return dict(zip(GPU_QUERY.keys(), ret))

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
    }
  }

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--host', default='localhost', type=str)
  parser.add_argument('-p', '--port', default=6666, type=int)
  args = parser.parse_args()
  # ZMQ PUB to proxy
  ctx = zmq.Context()
  sock = ctx.socket(zmq.PUB)
  sock.connect(f'tcp://{args.host}:{args.port}')
  data = {'host': platform.node()}
  while True:
    data.update(monitor())
    sock.send_json(data)
    break
    sleep(1)
