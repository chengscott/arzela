from glob import glob
import json
import re
import subprocess
import zmq


class Monitor:
  def __init__(self, node):
    self.node = node
    self._ctx = zmq.Context()
    self._pub_sock = self._ctx.socket(zmq.PUB)
    # precompiled regex
    reg = {
        'sensors_power':
        r'power1_average: (\d+\.\d+)',
        'sensors_temp':
        r'temp\d+_input: (\d+\.\d+)',
        'cpufreq':
        r'cpu MHz\t\t: (\d+\.\d+)',
        'cpu':
        r'cpu\d+ (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)',
        'meminfo':
        r'(\d+) kB',
    }
    self.__re = {}
    for name, r in reg.items():
      self.__re[name] = re.compile(r)
    self.__rapl_path = glob(
        '/sys/devices/virtual/powercap/intel-rapl/intel-rapl:[0-7]/'
        'constraint_0_power_limit_uw')
    self.__ib_path = glob('/sys/class/infiniband/*/ports/*/counters/')

  def bind(self, host, pub_port):
    self._pub_sock.connect(f'tcp://{host}:{pub_port}')

  def run_sensors(self):
    """run `sensors` to collect cpu temperature by core and system power"""
    # /sys/class/hwmon/hwmon*/temp*_input
    res = subprocess.run(['sensors', '-u'],
                         check=True,
                         stdout=subprocess.PIPE,
                         encoding='utf-8').stdout
    temp = map(float, self.__re['sensors_temp'].findall(res))
    power = map(float, self.__re['sensors_power'].findall(res))
    return {'temp': list(temp), 'power': sum(power)}

  def collect_cpufreq(self):
    """collect cpu frequency (MHz) by core"""
    # /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq
    with open('/proc/cpuinfo', 'r') as f:
      for freq in self.__re['cpufreq'].findall(f.read()):
        yield float(freq)

  def collect_rapl(self):
    """collect cpu power (Watt) by socket"""
    for path in self.__rapl_path:
      with open(path, 'r') as f:
        yield int(f.read()) / 10**6

  def collect_cpu_time(self):
    """collect cummulated cpu idle / total time by core"""

    def read():
      with open('/proc/stat', 'r') as f:
        for t in self.__re['cpu'].findall(f.read()):
          yield tuple(map(int, t))

    res = [
        (idle + iowait,
         user + nice + sys + idle + iowait + irq + softirq + steal)
        for user, nice, sys, idle, iowait, irq, softirq, steal, _, _ in read()
    ]
    idle, total = map(list, zip(*res))
    return {'idle': idle, 'total': total}

  def collect_memory(self):
    """collect free / total memory usage (MB)"""
    total, free = 1, 1
    with open('/proc/meminfo', 'r') as f:
      total = int(self.__re['meminfo'].findall(f.readline())[0])
      f.readline()
      free = int(self.__re['meminfo'].findall(f.readline())[0])
    return {
        'total': total,
        'free': free,
        'usage': total - free,
        'util': (1 - free / total) * 100,
    }

  @staticmethod
  def collect_process():
    """collect process cpu usage"""
    from heapq import nlargest
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
    for pid, name, usage in res:
      try:
        with open(f'/proc/{pid}/cmdline') as f:
          cmd = f.read().replace('\x00', ' ').strip()
          if cmd:
            yield cmd, usage
          else:
            yield name, usage
      except FileNotFoundError:
        continue

  @staticmethod
  def run_nvidia_smi():
    query = {
        'freq': 'clocks.gr',
        'power': 'power.draw',
        'temp': 'temperature.gpu',
        'gpu_util': 'utilization.gpu',
        'mem_util': 'utilization.memory',
    }
    gpu_query = ','.join(query.values())
    res = subprocess.run([
        'nvidia-smi', f'--query-gpu={gpu_query}',
        '--format=csv,noheader,nounits'
    ],
                         check=True,
                         stdout=subprocess.PIPE,
                         encoding='utf-8').stdout
    res = [map(float, row.split(', ')) for row in res.splitlines()]
    ret = list(map(list, zip(*res)))
    return dict(zip(query.keys(), ret))

  def collect_ib(self):
    """collect cummulated Infiniband Rx/Tx bytes"""
    counters = {
        'rx_data': 'port_rcv_data',
        'tx_data': 'port_xmit_data',
    }

    def read(path):
      for key, counter in counters.items():
        with open(path + counter, 'r') as f:
          yield key, int(f.read())

    for path in self.__ib_path:
      port = int(path.split('/')[-3])
      yield port, dict(read(path))

  @staticmethod
  def collect_netdev():
    """collect cummulated network device Rx/Tx bytes"""
    with open('/proc/net/dev', 'r') as f:
      f.readline()
      f.readline()
      for net in f:
        net = net.split()
        interface, rx, tx = net[0][:-1], int(net[1]), int(net[9])
        yield interface, {'rx_data': rx, 'tx_data': tx}

  @staticmethod
  def run_disk():
    """run `df` to collect disk usage"""
    res = subprocess.run(['df', '-h'],
                         check=True,
                         stdout=subprocess.PIPE,
                         encoding='utf-8').stdout
    for part in res.splitlines():
      part = part.split()
      if part[5] in ['/', '/home/shared']:
        loc, usage, avail = part[5], int(part[4][:-1]), part[3]
        yield loc, {'usage': usage, 'avail': avail}

  def run_all(self):
    sensors_stat = self.run_sensors()
    return {
        'cpu': {
            'freq': list(self.collect_cpufreq()),
            'power': list(self.collect_rapl()),
            'temp': sensors_stat['temp'],
        },
        'gpu': self.run_nvidia_smi(),
        'memory': self.collect_memory(),
        'cpu_util': self.collect_cpu_time(),
        'power': sensors_stat['power'],
        'ib': dict(self.collect_ib()),
        'eth': dict(self.collect_netdev()),
        #'process': list(self.collect_process()),
        #'disk': dict(self.run_disk()),
    }

  def run(self):
    data = self.run_all()
    self._pub_sock.send_multipart(
        [self.node, json.dumps(data).encode('utf-8')])
