from .errors  import *
from .info    import *
from .login   import *
from .message import *
from .packet  import *


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

	def request(self, request):
		self.number += 1
		self.send(self.number, request)
		(_, reply), = self.recv(request.replies(self.number))  # pylint: disable=unbalanced-tuple-unpacking
		DVRIPRequestError.signal(request, reply)
		return reply


class Client(Connection):
	__slots__ = ('username', '_logininfo')

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.username   = None
		self._logininfo = None

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
		self.session    = reply.session
		self.username   = username
		self._logininfo = reply

	def logout(self):
		assert self.session is not None
		request = ClientLogout(username=self.username,
		                       session=self.session)
		self.request(request)
		self.session = None

	def connect(self, address, *args, **named):
		self.socket.connect(address)
		return self.login(*args, **named)

	def systeminfo(self):
		reply = self.request(GetInfo(category=Info.SYSTEM,
		                             session=self.session))
		if reply.system is NotImplemented:
			raise DVRIPDecodeError('invalid system info reply')
		reply.system.chassis = self._logininfo.chassis
		return reply.system

	def storageinfo(self):
		reply = self.request(GetInfo(category=Info.STORAGE,
		                             session=self.session))
		if reply.storage is NotImplemented:
			raise DVRIPDecodeError('invalid system info reply')
		return reply.storage

	def activityinfo(self):
		reply = self.request(GetInfo(category=Info.ACTIVITY,
		                             session=self.session))
		if reply.activity is NotImplemented:
			raise DVRIPDecodeError('invalid system info reply')
		return reply.activity


class Server(Connection):
	pass
