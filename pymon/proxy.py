import zmq


class Proxy:
  def __init__(self):
    self._ctx = zmq.Context()
    self._frontend = self._ctx.socket(zmq.XSUB)
    self._backend = self._ctx.socket(zmq.XPUB)

  def bind(self, proxy_port):
    self._frontend.bind(f'tcp://*:{proxy_port[0]}')
    self._backend.bind(f'tcp://*:{proxy_port[1]}')
    zmq.proxy(self._frontend, self._backend)
