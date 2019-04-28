from .errors  import *
from .packet  import *
from .message import *
from .login   import *
from .typing  import String
from .utils   import init as _init


class Sequence(object):  # pylint: disable=too-few-public-methods
	__slots__ = ('session', 'number')

	def __init__(self, session, number):  # pylint: disable=unused-argument
		_init(Sequence, self)

	def packet(self, *args, **named):
		packet = Packet(self.session.id, self.number, *args, **named)
		return packet


class Connection(object):
	PORT = 34567

	__slots__ = ('socket', 'file', 'session', 'number', 'username')

	def __init__(self, socket, session=None, number=0):  # pylint: disable=unused-argument
		# pylint: disable=unused-variable
		file     = socket.makefile('rwb')
		username = None
		_init(Connection, self)

	def sequence(self):
		s = Sequence(self.session, self.number)
		self.number += 1
		return s

	def request(self, message):
		file = self.file
		for packet in message.topackets(self):
			packet.dump(file)
		file.flush()
		replies = message.replies(packet.number)  # pylint: disable=undefined-loop-variable
		results = []
		while replies.open():
			packet = Packet.load(file)
			self.number = max(self.number, packet.number + 1)
			chunk = replies.accept(packet)
			if chunk is None:
				print('unrecognized packet:', packet)  # FIXME
				continue
			results.extend(chunk)
		return results

	def login(self, username, *args, **named):
		assert self.session is None

		self.session = Session(0)
		request = ClientLogin(username, *args, **named)
		reply, = self.request(request)  # pylint: disable=unbalanced-tuple-unpacking
		DVRIPRequestError.signal(request, reply)
		self.session  = reply.session
		self.username = username

		return reply  # FIXME device info

	def logout(self):
		assert self.session is not None
		request = ClientLogout(String(self.username), self.session)
		reply, = self.request(request)  # pylint: disable=unbalanced-tuple-unpacking
		DVRIPRequestError.signal(request, reply)
		self.session = None

		return reply  # FIXME debug

	def connect(self, address, *args, **named):
		self.socket.connect(address)
		return self.login(*args, **named)
