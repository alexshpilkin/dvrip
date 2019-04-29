from .errors  import *
from .packet  import *
from .message import *
from .login   import *


class Connection(object):
	PORT = 34567

	__slots__ = ('socket', 'file', 'session', 'number')

	def __init__(self, socket, session=None, number=0):
		self.socket   = socket
		self.file     = socket.makefile('rwb')
		self.session  = session
		self.number   = number

	def send(self, number, message):
		file = self.file
		for packet in message.topackets(self.session, number):
			packet.dump(file)
		file.flush()

	def recv(self, filter):  # pylint: disable=redefined-builtin
		file = self.file
		results = []
		while filter:
			packet = Packet.load(file)
			self.number = max(self.number, packet.number)
			chunk = filter.accept(packet)
			if chunk is None:
				print('unrecognized packet:', packet)  # FIXME
				continue
			results.extend(chunk)
		return results

	def request(self, message):
		self.number += 1
		self.send(self.number, message)
		(_, reply), = self.recv(message.replies(self.number))  # pylint: disable=unbalanced-tuple-unpacking
		return reply


class Client(Connection):
	__slots__ = ('username',)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.username = None

	def login(self, username, password, hash=Hash.XMMD5,  # pylint: disable=redefined-builtin
	          service='DVRIP-Web'):
		assert self.session is None

		self.session = Session(0)
		request = ClientLogin(username=username,
		                      passhash=hash.func(password),
		                      hash=hash,
		                      service=service)
		reply = self.request(request)
		DVRIPRequestError.signal(request, reply)
		self.session  = reply.session
		self.username = username

		return reply  # FIXME device info

	def logout(self):
		assert self.session is not None
		request = ClientLogout(username=self.username,
		                       session=self.session)
		reply = self.request(request)
		DVRIPRequestError.signal(request, reply)
		self.session = None

		return reply  # FIXME debug

	def connect(self, address, *args, **named):
		self.socket.connect(address)
		return self.login(*args, **named)

class Server(Connection):
	pass
