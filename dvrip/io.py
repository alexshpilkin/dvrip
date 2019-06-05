from datetime import datetime
from io import RawIOBase
from socket import AF_INET, SO_BROADCAST, SO_REUSEADDR, SOCK_DGRAM, \
                   socket as Socket, SOL_SOCKET, timeout as Timeout
from time import monotonic
from typing import Iterable, Optional, MutableSequence, TypeVar, Union

from .discover import DiscoverReply, Host
from .errors import DVRIPDecodeError, DVRIPRequestError
from .files import GetFiles, FileQuery
from .info import ActivityInfo, GetInfo, Info, StorageInfo, SystemInfo
from .log import GetLog, LogQuery
from .login import ClientLogin, ClientLogout, Hash, KeepAlive
from .message import Message, Request, EPOCH, Filter, Session, Status
from .monitor import DoMonitor, Monitor, MonitorAction, MonitorClaim, \
                     MonitorParams
from .operation import DoOperation, GetTime, Machine, MachineOperation, \
                       Operation
from .packet import Packet
from .playback import DoPlayback, Playback, PlaybackAction, PlaybackClaim, \
                      PlaybackParams
from .ptz import DoPTZ, PTZ, PTZButton, PTZParams

__all__ = ('DVRIPConnection', 'DVRIPClient', 'DVRIPServer')

M = TypeVar('M', bound=Message)
T = TypeVar('T')


class DVRIPConnection(object):
	__slots__ = ('socket', 'file', 'session', 'number')

	def __init__(self,
	             socket: Socket,
	             session: Optional[Session] = None,
	             number: int = 0
	            ) -> None:
		self.socket   = socket
		self.file     = socket.makefile('rwb', buffering=0)
		self.session  = session
		self.number   = number & ~1

	def send(self, number: int, message: Message):
		assert self.session is not None

		file = self.file
		for packet in message.topackets(self.session, number):
			packet.dump(file)

	def recv(self, filter: Filter[T]) -> T:  # pylint: disable=redefined-builtin
		file = self.file
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

	def request(self, request: Request[M]) -> M:
		self.number += 2
		self.send(self.number, request)
		reply: M = self.recv(request.replies(self.number))
		DVRIPRequestError.signal(request, reply)
		return reply

	def reader(self,
	           socket: Socket,
	           claim: Request[M],
	           request: Request
	          ) -> RawIOBase:
		data = DVRIPConnection(socket, self.session)
		data.send(data.number, claim)
		self.request(request)
		reply: M = data.recv(claim.replies(data.number))
		DVRIPRequestError.signal(claim, reply)
		return DVRIPReader(data, claim.stream())


class DVRIPReader(RawIOBase):
	__slots__ = ('conn', 'filter', 'buffer')

	def __init__(self,
	             conn: DVRIPConnection,
	             filter: Filter[Union[bytes, bytearray, memoryview]]  # pylint: disable=redefined-builtin
	            ) -> None:
		super().__init__()
		self.conn   = conn
		self.filter = filter
		self.buffer = None

	def readable(self) -> bool:
		return True

	def readinto(self, buffer: MutableSequence[int]) -> int:
		if self.buffer is None:
			try:
				data: Union[bytes, bytearray, memoryview] = \
				      self.conn.recv(self.filter)
			except StopIteration:
				return 0
			self.buffer = memoryview(data)

		assert self.buffer is not None
		length = len(self.buffer)
		buffer[:length] = self.buffer[:len(buffer)]
		self.buffer     = self.buffer[len(buffer):]
		if not self.buffer:
			self.buffer.release()  # type: ignore
			self.buffer = None
		assert min(length, len(buffer))
		return min(length, len(buffer))


class DVRIPClient(DVRIPConnection):
	__slots__ = ('_logininfo', '_keepalive')

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._logininfo = None
		self._keepalive = None

	@staticmethod
	def discover(interface: str, timeout: float) -> Iterable[Host]:
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

	def login(self,
	          username: str,
	          password: str,
	          hash: Hash = Hash.XMMD5,  # pylint: disable=redefined-builtin
	          service: str = 'DVRIP-Web'
	         ) -> None:
		assert self.session is None
		self.session = Session(0)
		now = monotonic()
		request = ClientLogin(username=username,
		                      passhash=hash.func(password),
		                      hash=hash,
		                      service=service)
		reply = self.request(request)
		self.session    = reply.session
		self._logininfo = reply
		self._keepalive = now

	def logout(self) -> None:
		request = ClientLogout(session=self.session)
		self.request(request)
		self.session = None

	def keepalive(self) -> None:
		now = monotonic()
		if now - self._keepalive < self._logininfo.keepalive:
			return
		request = KeepAlive(session=self.session)
		self.request(request)
		self._keepalive = now

	def connect(self, address: Union[tuple, str], *args, **named) -> None:
		self.socket.connect(address)
		return self.login(*args, **named)

	def systeminfo(self) -> SystemInfo:
		reply = self.request(GetInfo(command=Info.SYSTEM,
		                             session=self.session))
		if reply.system is NotImplemented:
			raise DVRIPDecodeError('invalid system info reply')
		reply.system.chassis = self._logininfo.chassis
		return reply.system

	def storageinfo(self) -> StorageInfo:
		reply = self.request(GetInfo(command=Info.STORAGE,
		                             session=self.session))
		if reply.storage is NotImplemented:
			raise DVRIPDecodeError('invalid storage info reply')
		return reply.storage

	def activityinfo(self) -> ActivityInfo:
		reply = self.request(GetInfo(command=Info.ACTIVITY,
		                             session=self.session))
		if reply.activity is NotImplemented:
			raise DVRIPDecodeError('invalid activity info reply')
		return reply.activity

	def time(self, time: Optional[datetime] = None) -> datetime:
		reply = self.request(GetTime(session=self.session))
		if reply.gettime is NotImplemented:
			raise DVRIPDecodeError('invalid get time reply')
		if time is not None:
			request = DoOperation(command=Operation.SETTIME,
			                      session=self.session,
			                      settime=time)
			self.request(request)
		return reply.gettime

	def reboot(self) -> None:
		machine = MachineOperation(action=Machine.REBOOT)
		request = DoOperation(command=Operation.MACHINE,
		                      session=self.session,
		                      machine=machine)
		self.request(request)
		self.socket.close()  # FIXME reset?
		self.session = None

	def log(self, *, offset=0, **kwargs):
		while True:
			request = GetLog(session=self.session,
		                         logquery=LogQuery(offset=offset,
		                                           **kwargs))
			entries = self.request(request).entries
			if entries is None:
				break
			yield from entries
			offset = entries[-1].number + 1

	def files(self, start, **kwargs):
		last = None
		while True:
			request = GetFiles(session=self.session,
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

	def button(self, channel: int, button: PTZButton) -> None:
		request = DoPTZ(session=self.session,
		                ptz=PTZ(button=button,
		                        params=PTZParams(channel=channel)))
		self.request(request)

	def download(self, socket, name):
		pb = Playback(action=PlaybackAction.DOWNLOADSTART,
		              start=EPOCH,
		              end=datetime(9999, 12, 31, 23, 59, 59),  # FIXME now()?
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
