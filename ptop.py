#!/usr/bin/env python3.6
import argparse
from heapq import nlargest
from glob import glob
import json
import platform
import re
import subprocess
from time import sleep
import zmq


def static(**kwargs):
  def decorate(func):
    for k in kwargs:
      setattr(func, k, kwargs[k])
    return func

  return decorate


@static(
    re_power=re.compile(r'power1_average: (\d+\.\d+)'),
    re_temp=re.compile(r'temp\d+_input: (\d+\.\d+)'))
def monitor_sensors():
  # /sys/class/hwmon/hwmon*/temp*_input
  res = subprocess.run(
      ['sensors', '-u'], check=True, stdout=subprocess.PIPE,
      encoding='utf-8').stdout
  return {
      'temp': list(map(float, monitor_sensors.re_temp.findall(res))),
      'power': sum(map(float, monitor_sensors.re_power.findall(res)))
  }


@static(re_freq=re.compile(r'cpu MHz\t\t: (\d+\.\d+)'))
def monitor_cpufreq():
  ret = []
  # /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq
  with open('/proc/cpuinfo', 'r') as f:
    ret.extend(map(float, monitor_cpufreq.re_freq.findall(f.read())))
  return ret


@static(path='/sys/devices/virtual/powercap/intel-rapl/intel-rapl:{i}/'
        'constraint_0_power_limit_uw')
def monitor_rapl():
  ret = []
  for i in range(2):
    with open(monitor_rapl.path.format(i=i), 'r') as f:
      ret.append(int(f.read()) / 10**6)
  return ret


@static(
    re_stat=re.compile(
        r'cpu\d+ (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)'))
def monitor_cpu():
  ret = []
  with open('/proc/stat', 'r') as f:
    ret = monitor_cpu.re_stat.findall(f.read())
  ret = [tuple(map(int, t)) for t in ret]
  ret = [(idle + iowait,
          user + nice + sys + idle + iowait + irq + softirq + steal)
         for user, nice, sys, idle, iowait, irq, softirq, steal, _, _ in ret]
  ret = list(map(list, zip(*ret)))
  return dict(zip(['idle', 'total'], ret))


@static(re_mem=re.compile(r'(\d+) kB'))
def monitor_memory():
  ret = {}
  with open('/proc/meminfo', 'r') as f:
    ret['total'] = int(monitor_memory.re_mem.findall(f.readline())[0])
    f.readline()
    ret['free'] = int(monitor_memory.re_mem.findall(f.readline())[0])
  return ret


def monitor_process():
  res = []
  uptime = 0
  with open('/proc/uptime') as f:
    uptime = float(f.read().split()[0])
  for proc in glob('/proc/*[0-9]*/stat'):
    try:
      with open(proc, 'r') as f:
        stat = f.read().split()
        pid, name = int(stat[0]), stat[1][1:-1]
        total = sum(map(int, stat[13:15]))
        seconds = uptime - (int(stat[21]) / 100)
        usage = 100 * ((total / 100) / seconds)
        res.append((pid, name, usage))
    except FileNotFoundError:
      continue
  res = nlargest(10, res, key=lambda kv: kv[2])
  ret = []
  for pid, name, usage in res:
    try:
      with open(f'/proc/{pid}/cmdline') as f:
        cmd = f.read().replace('\x00', ' ').strip()
        if cmd:
          ret.append((cmd, usage))
        else:
          ret.append((name, usage))
    except FileNotFoundError:
      continue
  return ret


@static(
    ret=['freq', 'power', 'temp', 'gpu_util', 'mem_util'],
    query=','.join([
        'clocks.gr', 'power.draw', 'temperature.gpu', 'utilization.gpu',
        'utilization.memory'
    ]))
def monitor_gpu():
  def use_nvidia_smi():
    res = subprocess.run(
        [
            'nvidia-smi', f'--query-gpu={monitor_gpu.query}',
            '--format=csv,noheader,nounits'
        ],
        check=True,
        stdout=subprocess.PIPE,
        encoding='utf-8').stdout
    res = [map(float, row.split(", ")) for row in res.splitlines()]
    return list(map(list, zip(*res)))

  ret = use_nvidia_smi()
  return dict(zip(monitor_gpu.ret, ret))


@static(
    path=glob('/sys/class/infiniband/*/ports/*/counters/'),
    counters={
        'rx_data': 'port_rcv_data',
        'tx_data': 'port_xmit_data',
    })
def monitor_ib():
  def read(path, counter):
    with open(path + counter, 'r') as f:
      return int(f.read())

  return {
      int(p.split('/')[-3]):
      {k: read(p, v)
       for k, v in monitor_ib.counters.items()}
      for p in monitor_ib.path
  }


def monitor_netdev():
  ret = {}
  with open('/proc/net/dev', 'r') as f:
    f.readline()
    f.readline()
    for eth in f:
      eth = eth.split()
      ret[eth[0][:-1]] = {
          'rx_data': int(eth[1]),
          'tx_data': int(eth[9]),
      }
  return ret


def monitor_free_disk():
  ret = {}
  res = subprocess.run(
      ['df', '-h'], check=True, stdout=subprocess.PIPE,
      encoding='utf-8').stdout
  for part in res.splitlines():
    part = part.split()
    if part[5] in ['/', '/home/shared']:
      ret[part[5]] = {'usage': int(part[4][:-1]), 'available': part[3]}
  return ret


def monitor():
  sensors_stat = monitor_sensors()
  return {
      'cpu': {
          'freq': monitor_cpufreq(),
          'power': monitor_rapl(),
          'temp': sensors_stat['temp'],
      },
      'gpu': monitor_gpu(),
      'mem': monitor_memory(),
      'cpu_util': monitor_cpu(),
      #'process': monitor_process(),
      'sys': {
          'power': sensors_stat['power'],
      },
      'ib': monitor_ib(),
      'eth': monitor_netdev(),
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
    data = monitor()
    pub_sock.send_multipart([node, json.dumps(data).encode('utf-8')])
    sleep(1)
