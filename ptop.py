#!/usr/bin/env python3.6
import argparse
import requests
import zmq

def main():
  while True:
    raw_data = sock.recv_json()
    print(f"Received data: {raw_data}")
    tag = f',host={raw_data["host"]}'
    for item in ['cpu', 'gpu']:
      for k, stats in raw_data[item].items():
        field_data = ','.join([f'{item}_{i}={v}' for i,v in enumerate(stats)])
        data = f'{item}_{k}{tag} {field_data}'
        #print(data)
        #response = requests.post('http://localhost:8086/write', params={'db': 'ptopdb'}, data=data.encode())
        #assert(response.status_code == 204)

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument('-p', '--port', default=6666, type=int)
  args = parser.parse_args()
  ctx = zmq.Context()
  sock = ctx.socket(zmq.SUB)
  sock.setsockopt(zmq.SUBSCRIBE, b"")
  sock.bind(f'tcp://*:{args.port}')
  main()
