from .errors import DVRIPDecodeError, DVRIPRequestError
from .info import GetInfo, Info
from .login import ClientLogin, ClientLogout, Hash
from .message import Session, Status
from .packet import Packet
from .search import GetFile, FileQuery
from .operation import GetTime, Machine, MachineOperation, Operation, \
                       PerformOperation

__all__ = ('DVRIPConnection', 'DVRIPClient', 'DVRIPServer')


class DVRIPConnection(object):
	__slots__ = ('socket', 'file', 'session', 'number')

	def __init__(self, socket, session=None, number=0):
		self.socket   = socket
		self.file     = socket.makefile('rwb', buffering=0)
		self.session  = session
		self.number   = number

	def send(self, number, message):
		file = self.file
		for packet in message.topackets(self.session, number):
			packet.dump(file)

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


class DVRIPClient(DVRIPConnection):
	__slots__ = ('_logininfo',)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
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
			self.request(PerformOperation(
			    command=Operation.SETTIME,
			    session=self.session,
			    settime=time))
		if reply.gettime is NotImplemented:
			return None
		return reply.gettime

	def reboot(self):
		self.request(PerformOperation(
		    command=Operation.MACHINE,
		    machine=MachineOperation(action=Machine.REBOOT),
		    session=self.session))
		self.socket.close()  # FIXME reset?
		self.socket = self.file = self.session = None

	def search(self, start, **kwargs):
		last = None
		while True:
			reply = self.request(GetFile(
				     session=self.session,
				     filequery=FileQuery(start=start,
				                         **kwargs)))
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


class DVRIPServer(DVRIPConnection):
	pass
