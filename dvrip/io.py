from datetime import datetime
from io import RawIOBase
from socket import AF_INET, SO_BROADCAST, SO_REUSEADDR, SOCK_DGRAM, \
                   socket as Socket, SOL_SOCKET, timeout as Timeout

from .discover import DiscoverReply
from .errors import DVRIPDecodeError, DVRIPRequestError
from .info import GetInfo, Info
from .login import ClientLogin, ClientLogout, Hash
from .message import EPOCH, Session, Status
from .monitor import DoMonitor, Monitor, MonitorAction, MonitorClaim, \
                     MonitorParams
from .operation import GetTime, Machine, MachineOperation, Operation, \
                       PerformOperation
from .packet import Packet
from .playback import DoPlayback, Playback, PlaybackAction, PlaybackClaim, \
                      PlaybackParams
from .search import GetFile, FileQuery

__all__ = ('DVRIPConnection', 'DVRIPClient', 'DVRIPServer')


class DVRIPConnection(object):
	__slots__ = ('socket', 'file', 'session', 'number')

	def __init__(self, socket, session=None, number=0):
		self.socket   = socket
		self.file     = socket.makefile('rwb', buffering=0)
		self.session  = session
		self.number   = number & ~1

	def send(self, number, message):
		file = self.file
		for packet in message.topackets(self.session, number):
			packet.dump(file)

	def recv(self, filter):  # pylint: disable=redefined-builtin
		file   = self.file
		filter = iter(filter)
		filter.send(None)  # prime the pump
		while True:
			packet = Packet.load(file)
			self.number = max(self.number, packet.number & ~1)
			reply = filter.send(packet)  # raises StopIteration
			if reply is NotImplemented:
				raise DVRIPDecodeError('stray packet')
			if reply is not None:
				return reply
			filter.send(None)

	def request(self, request):
		self.number += 2
		self.send(self.number, request)
		reply = self.recv(request.replies(self.number))
		DVRIPRequestError.signal(request, reply)
		return reply

	def reader(self, socket, claim, request):
		data = DVRIPConnection(socket, self.session)
		data.send(data.number, claim)
		self.request(request)
		reply = data.recv(claim.replies(data.number))
		DVRIPRequestError.signal(claim, reply)
		return DVRIPReader(data, claim.stream())


class DVRIPReader(RawIOBase):
	__slots__ = ('conn', 'filter', 'buffer')

	def __init__(self, conn, filter):  # pylint: disable=redefined-builtin
		super().__init__()
		self.conn   = conn
		self.filter = filter
		self.buffer = b''

	def readable(self):
		return True

	def readinto(self, buffer):
		if not self.buffer:
			try:
				data = self.conn.recv(self.filter)
			except StopIteration:
				return 0
			self.buffer = memoryview(data)

		length = len(self.buffer)
		buffer[:length] = self.buffer[:len(buffer)]
		self.buffer     = self.buffer[len(buffer):]
		assert min(length, len(buffer))
		return min(length, len(buffer))


class DVRIPClient(DVRIPConnection):
	__slots__ = ('_logininfo',)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._logininfo = None

	@staticmethod
	def discover(interface, timeout):
		sock = Socket(AF_INET, SOCK_DGRAM)
		sock.settimeout(timeout)
		sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
		sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
		sock.bind((interface, 34569))

		request = Packet(0, 0, 1530, b'', fragments=0, fragment=0)
		sock.sendto(request.encode(), ('255.255.255.255', 34569))

		while True:
			try:
				data, (host, _) = sock.recvfrom(Packet.MAXLEN)
			except Timeout:
				break
			packet = Packet.decode(data)
			if not packet.payload: continue
			reply = DiscoverReply.frompackets([packet]).host
			if reply.host != host:
				raise DVRIPDecodeError('wrong IP address '
				                       'reported')
			yield reply

	def login(self, username, password, hash=Hash.XMMD5,  # pylint: disable=redefined-builtin
	          service='DVRIP-Web'):
		assert self.session is None

		self.session = Session(0)
		request = ClientLogin(username=username,
		                      passhash=hash.func(password),
		                      hash=hash,
		                      service=service)
		reply = self.request(request)
		self.session    = reply.session
		self._logininfo = reply

	def logout(self):
		assert self.session is not None
		request = ClientLogout(session=self.session)
		self.request(request)
		self.session = None

	def connect(self, address, *args, **named):
		self.socket.connect(address)
		return self.login(*args, **named)

	def systeminfo(self):
		reply = self.request(GetInfo(command=Info.SYSTEM,
		                             session=self.session))
		if reply.system is NotImplemented:
			raise DVRIPDecodeError('invalid system info reply')
		reply.system.chassis = self._logininfo.chassis
		return reply.system

	def storageinfo(self):
		reply = self.request(GetInfo(command=Info.STORAGE,
		                             session=self.session))
		if reply.storage is NotImplemented:
			raise DVRIPDecodeError('invalid system info reply')
		return reply.storage

	def activityinfo(self):
		reply = self.request(GetInfo(command=Info.ACTIVITY,
		                             session=self.session))
		if reply.activity is NotImplemented:
			raise DVRIPDecodeError('invalid system info reply')
		return reply.activity

	def time(self, time=None):
		reply = self.request(GetTime(session=self.session))
		if time is not None:
			request = PerformOperation(command=Operation.SETTIME,
			                           session=self.session,
			                           settime=time)
			self.request(request)
		if reply.gettime is NotImplemented:
			return None
		return reply.gettime

	def reboot(self):
		machine = MachineOperation(action=Machine.REBOOT)
		request = PerformOperation(command=Operation.MACHINE,
		                           session=self.session,
		                           machine=machine)
		self.request(request)
		self.socket.close()  # FIXME reset?
		self.socket = self.file = self.session = None

	def search(self, start, **kwargs):
		last = None
		while True:
			request = GetFile(session=self.session,
				          filequery=FileQuery(start=start,
				                              **kwargs))
			reply = self.request(request)
			if reply.files is NotImplemented:
				return
			drop = True
			for file in reply.files:
				if file == last:
					drop = False
				elif last is None or not drop:
					yield file
			if (reply.status == Status.SRCHCOMP or
			    not reply.files or
			    reply.files[-1] == last):
				return
			last  = reply.files[-1]
			start = last.start

	def download(self, socket, name):
		pb = Playback(action=PlaybackAction.DOWNLOADSTART,
		              start=EPOCH,
		              end=datetime(9999, 12, 31, 23, 59, 59),
		              params=PlaybackParams(name=name))
		claim = PlaybackClaim(session=self.session, playback=pb)
		request = DoPlayback(session=self.session, playback=pb)
		return self.reader(socket, claim, request)

	def monitor(self, socket, channel, stream):
		monitor = Monitor(action=MonitorAction.START,
		                  params=MonitorParams(channel=channel,
		                                       stream=stream))
		claim = MonitorClaim(session=self.session, monitor=monitor)
		request = DoMonitor(session=self.session, monitor=monitor)
		return self.reader(socket, claim, request)


class DVRIPServer(DVRIPConnection):
	pass
