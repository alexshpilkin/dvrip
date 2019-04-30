from abc import abstractmethod
from datetime import datetime
from enum import Enum, unique
from io import RawIOBase
from json import dumps, load
from string import hexdigits
from typing import Optional
from .errors import DVRIPDecodeError
from .packet import Packet
from .typing import Value, for_json, json_to

__all__ = ('hextype', 'Session', 'Status', 'ControlMessage', 'ControlFilter',
           'ControlRequest')


class _ChunkReader(RawIOBase):
	def __init__(self, chunks):
		super().__init__()
		self.chunks = list(chunks)
		self.chunks.reverse()
	def readable(self):
		return True
	def readinto(self, buffer):
		if not self.chunks:
			return 0
		chunk = self.chunks[-1]
		assert chunk
		buffer[:len(chunk)] = chunk[:len(buffer)]
		if len(chunk) > len(buffer):
			self.chunks[-1] = chunk[len(buffer):]
		else:
			self.chunks.pop()
		return len(chunk)


def _hex_for_json(value: int) -> object:
	return for_json('0x{:08X}'.format(value))

def _json_to_hex(datum: object) -> int:
	datum = json_to(str)(datum)
	if (datum[:2] != '0x' or len(datum) > 10 or
	    not all(c in hexdigits for c in datum[2:])):
		raise DVRIPDecodeError('not a session ID')
	return int(datum[2:], 16)

hextype = (_json_to_hex, _hex_for_json)


_DTFORMAT = '%Y-%m-%d %H:%M:%S'
_NOSTRING = '0000-00-00 00:00:00'
_EPSTRING = '2000-00-00 00:00:00'
EPOCH     = datetime(2000, 1, 1, 0, 0, 0)

def _datetime_for_json(value: Optional[datetime]) -> object:
	if value is None:
		return _NOSTRING
	if value == EPOCH:
		return _EPSTRING
	if value <= EPOCH:
		raise ValueError('datetime not after the epoch')
	return for_json(value.strftime(_DTFORMAT))

def _json_to_datetime(datum: object) -> Optional[datetime]:
	datum = json_to(str)(datum)
	if datum == _NOSTRING:
		return None
	if datum == _EPSTRING:
		return EPOCH
	try:
		value = datetime.strptime(datum, _DTFORMAT)
	except ValueError:
		raise DVRIPDecodeError('not a datetime string')
	if value <= EPOCH:
		raise DVRIPDecodeError('datetime not after the epoch')
	return value

datetimetype = (_json_to_datetime, _datetime_for_json)


class Session(object):
	__slots__ = ('id',)

	def __init__(self, id):  # pylint: disable=redefined-builtin
		self.id = id

	def __repr__(self):
		return 'Session(0x{:08X})'.format(self.id)

	def __eq__(self, other):
		if not isinstance(other, Session):
			return NotImplemented
		return self.id == other.id

	def __hash__(self):
		return hash(self.id)

	def for_json(self):
		return _hex_for_json(self.id)

	@classmethod
	def json_to(cls, datum):
		return cls(id=_json_to_hex(datum))


@unique
class Status(Enum):
	__slots__ = ('code', 'success', 'message', '_value_')

	def __new__(cls, code, success, message):
		self = object.__new__(cls)
		self._value_ = code  # pylint: disable=protected-access
		self.code    = code
		self.success = success
		self.message = message
		return self

	def __repr__(self):
		return '{}({!r})'.format(type(self).__qualname__, self._value_)

	def __str__(self):
		return self.message

	def __bool__(self):
		return self.success

	def for_json(self):
		return for_json(self.code)

	@classmethod
	def json_to(cls, datum):
		try:
			return cls(json_to(int)(datum))  # pylint: disable=no-value-for-parameter
		except ValueError:
			raise DVRIPDecodeError('not a known status code')

	# pylint: disable=line-too-long
	OK       = (100, True,  'OK')
	ERROR    = (101, False, 'Unknown error')
	VERSION  = (102, False, 'Invalid version')
	REQUEST  = (103, False, 'Invalid request')  # FIXME type?
	EXLOGIN  = (104, False, 'Already logged in')
	NOLOGIN  = (105, False, 'Not logged in')
	CREDS    = (106, False, 'Wrong username or password')
	ACCESS   = (107, False, 'Access denied')
	TIMEOUT  = (108, False, 'Timed out')
	FILE     = (109, False, 'File not found')
	SRCHCOMP = (110, True,  'Complete search results')
	SRCHPART = (111, True,  'Partial search results')
	EXUSER   = (112, False, 'User already exists')
	NOUSER   = (113, False, 'User does not exist')
	EXGROUP  = (114, False, 'Group already exists')
	NOGROUP  = (115, False, 'Group does not exist')
	MESSAGE  = (117, False, 'Invalid message')   # FIXME JSON?
	PTZPROTO = (118, False, 'PTZ protocol not set')
	SRCHNONE = (119, True,  'No search results')
	DISABLED = (120, False, 'Disabled')  # FIXME 配置为启用
	CONNECT  = (121, False, 'Channel not connected')
	REBOOT   = (150, True,  'Reboot required')
	FIXME202 = (202, False, 'FIXME Error 202')  # FIXME 用户未登录
	PASSWORD = (203, False, 'Wrong password')
	USERNAME = (204, False, 'Wrong username')
	LOCKOUT  = (205, False, 'Locked out')
	BANNED   = (206, False, 'Banned')
	CONFLICT = (207, False, 'Already logged in')
	INPUT    = (208, False, 'Illegal value')  # FIXME of field?
	FIXME209 = (209, False, 'FIXME Error 209')  # FIXME 索引重复如要增加的用户已经存在等
	FIXME210 = (210, False, 'FIXME Error 210')  # FIXME 不存在对象, 用于查询时
	OBJECT   = (211, False, 'Object does not exist')
	ACCOUNT  = (212, False, 'Account in use')
	SUBSET   = (213, False, 'Subset larger than superset')
	PASSCHAR = (214, False, 'Illegal characters in password')  # FIXME 密码不合法
	PASSMTCH = (215, False, 'Passwords do not match')
	USERRESV = (216, False, 'Username reserved')
	COMMAND  = (502, False, 'Illegal command')  # FIXME 命令不合法
	INTERON  = (503, True,  'Intercom turned on')
	INTEROFF = (504, True,  'Intercom turned off')  # FIXME 对讲未开启
	OKUPGR   = (511, True,  'Upgrade started')
	NOUPGR   = (512, False, 'Upgrade not started')
	UPGRDATA = (513, False, 'Invalid upgrade data')
	OKUPGRD  = (514, True,  'Upgrade successful')
	NOUPGRD  = (515, False, 'Upgrade failed')
	NORESET  = (521, False, 'Reset failed')
	OKRESET  = (522, True,  'Reset successful--reboot required')  # FIXME 需要重启设备
	INVRESET = (523, False, 'Reset data invalid')
	OKIMPORT = (602, True,  'Import successful--restart required')  # FIXME 需要重启应用程序 (et seqq)
	REIMPORT = (603, True,  'Import successful--reboot required')
	WRITING  = (604, False, 'Configuration write failed')
	FEATURE  = (605, False, 'Unsupported feature in configuration')
	READING  = (606, False, 'Configuration read failed')
	NOIMPORT = (607, False, 'Configuration not found')
	SYNTAX   = (608, False, 'Illegal configuration syntax')


class ControlMessage(Value):
	__slots__ = ()

	@property
	@abstractmethod
	def type(self):
		raise NotImplementedError  # pragma: no cover

	def chunks(self):
		size = Packet.MAXLEN  # FIXME Don't mention Packet explicitly?
		json = dumps(self.for_json()).encode('ascii') + b'\x0A\x00'
		return [json[i:i+size] for i in range(0, len(json), size)]

	def topackets(self, session, number):
		chunks = self.chunks()
		length = len(chunks)
		if length == 1:
			yield Packet(session.id, number, self.type, chunks[0],
			             fragments=0, fragment=0)
		else:
			for i, chunk in enumerate(chunks):
				yield Packet(session.id, number, self.type,
				             chunk, fragments=length,
				             fragment=i)

	@classmethod
	def fromchunks(cls, chunks):
		chunks = list(chunks)
		if not chunks:
			raise DVRIPDecodeError('no data in DVRIP packet')
		chunks[-1] = chunks[-1].rstrip(b'\x00\\')
		return cls.json_to(load(_ChunkReader(chunks),
		                        encoding='latin-1'))

	@classmethod
	def frompackets(cls, packets):
		packets = list(packets)
		return cls.fromchunks(p.payload for p in packets if p.payload)


class ControlFilter(object):
	__slots__ = ('cls', 'number', 'count', 'limit', 'packets')

	def __init__(self, cls, number):
		self.cls     = cls
		self.number  = number
		self.count   = 0
		self.limit   = None
		self.packets = None

	def __bool__(self):
		return self.limit is None or self.count < self.limit

	def accept(self, packet):
		if packet.type != self.cls.type:
			return None
		if packet.number != self.number:
			return None
		if self.limit is None:
			self.limit   = max(packet.fragments, 1)
			self.packets = [None] * self.limit
		if max(packet.fragments, 1) != self.limit:
			raise DVRIPDecodeError('conflicting fragment counts')
		if packet.fragment >= self.limit:
			raise DVRIPDecodeError('invalid fragment number')
		if self.packets[packet.fragment] is not None:
			raise DVRIPDecodeError('overlapping fragments')

		assert self.count < self.limit
		self.packets[packet.fragment] = packet
		self.count += 1
		if self.count < self.limit:
			return ()
		return ((self.number, self.cls.frompackets(self.packets)),)


class ControlRequest(ControlMessage):
	@property
	@abstractmethod
	def reply(self):
		raise NotImplementedError  # pragma: no cover

	@classmethod
	def replies(cls, number):
		return ControlFilter(cls.reply, number)
