from abc import abstractmethod
from datetime import datetime, timedelta
from enum import Enum, unique
from io import RawIOBase
from json import dumps, load
from string import hexdigits
from typing import ClassVar, Generator, Generic, Iterable, List, Optional, \
                   Sequence, Type, TypeVar, Union, cast

from .errors import DVRIPDecodeError
from .packet import Packet
from .typing import Value, for_json, json_to

_C = TypeVar('_C', bound='Choice')
_M = TypeVar('_M', bound='Message')
_R = TypeVar('_R', bound='Status')
_S = TypeVar('_S', bound='Session')
_T = TypeVar('_T')


class _ChunkReader(RawIOBase):
	def __init__(self, chunks: Iterable[bytes]) -> None:
		super().__init__()
		self.chunks = list(chunks)
		self.chunks.reverse()
	def readable(self) -> bool:
		return True
	def readinto(self, buffer: bytearray) -> int:
		if not self.chunks:
			return 0  # EOF
		chunk = self.chunks[-1]
		assert chunk
		buffer[:len(chunk)] = chunk[:len(buffer)]
		if len(chunk) > len(buffer):  # pylint: disable=no-else-return
			self.chunks[-1] = chunk[len(buffer):]
			return len(buffer)
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


_DTFORMAT  = '%Y-%m-%d %H:%M:%S'
_NOSTRING  = '0000-00-00 00:00:00'
_EPSTRING  = '2000-00-00 00:00:00'
EPOCH      = datetime(2000, 1, 1, 0, 0, 0)
RESOLUTION = timedelta(seconds=1)

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


class Choice(Enum):
	def __repr__(self) -> str:
		return '{}.{}'.format(type(self).__qualname__, self.name)

	def __str__(self) -> str:
		return self.value

	def for_json(self) -> object:
		return for_json(self.value)

	@classmethod
	def json_to(cls: Type[_C], datum: object) -> _C:
		try:
			return cls(json_to(str)(datum))
		except ValueError:
			raise DVRIPDecodeError('not a known choice')


class Session(object):
	__slots__ = ('id',)

	def __init__(self, id: int) -> None:  # pylint: disable=redefined-builtin
		self.id = id

	def __repr__(self) -> str:
		return 'Session(0x{:08X})'.format(self.id)

	def __eq__(self, other: object):
		if not isinstance(other, Session):
			return NotImplemented
		return self.id == other.id

	def __hash__(self) -> int:
		return hash(self.id)

	def for_json(self) -> object:
		return _hex_for_json(self.id)

	@classmethod
	def json_to(cls: Type[_S], datum: object) -> _S:
		return cls(id=_json_to_hex(datum))


@unique
class Status(Enum):  # FIXME derive from Choice
	__slots__ = ('code', 'success', 'message', '_value_')
	code:    int
	success: bool
	message: str

	def __new__(cls: Type[_R], code, success, message) -> _R:
		self = object.__new__(cls)
		self._value_ = code  # pylint: disable=protected-access
		self.code    = code
		self.success = success
		self.message = message
		return self

	# FIXME __init__

	def __repr__(self) -> str:
		return '{}({!r})'.format(type(self).__qualname__, self._value_)

	def __str__(self) -> str:
		return self.message

	def __bool__(self) -> bool:
		return self.success

	def for_json(self) -> object:
		return for_json(self.code)

	@classmethod
	def json_to(cls: Type[_R], datum: object) -> _R:
		try:
			return cls(json_to(int)(datum))  # type: ignore  # pylint: disable=no-value-for-parameter
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


class Message(Value):
	__slots__ = ()

	@property
	@abstractmethod
	def type(self) -> int:
		raise NotImplementedError  # pragma: no cover

	def chunks(self) -> Sequence[bytes]:
		size = Packet.MAXLEN  # FIXME Don't mention Packet explicitly?
		json = dumps(self.for_json()).encode('ascii')
		return [json[i:i+size] for i in range(0, len(json), size)]

	def topackets(self, session: Session, number: int) -> Iterable[Packet]:
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
	def fromchunks(cls: Type[_M], chunks: Iterable[bytes]) -> _M:
		chunks = list(chunks)
		if not chunks:
			raise DVRIPDecodeError('no data in DVRIP packet')
		chunks[-1] = chunks[-1].rstrip(b'\x00\\')
		return cls.json_to(load(_ChunkReader(chunks)))  # type: ignore # FIXME

	@classmethod
	def frompackets(cls: Type[_M], packets: Iterable[Packet]) -> _M:
		packets = list(packets)
		return cls.fromchunks(p.payload for p in packets if p.payload)


Filter = Generator[Union['NotImplemented', None, _T], Optional[Packet], None]


def controlfilter(cls: Type[_M], number: int) -> Filter[_M]:
	count = 0
	limit = 0
	packets: List[Optional[Packet]] = []

	packet = yield None  # prime the pump
	while True:
		assert packet is not None

		if packet.type != cls.type:
			packet = yield NotImplemented; continue
		if packet.number & ~1 != number & ~1:
			packet = yield NotImplemented; continue
		if not limit:
			limit   = max(packet.fragments, 1)
			packets = [None] * limit
		if max(packet.fragments, 1) != limit:
			raise DVRIPDecodeError('conflicting fragment counts')
		if packet.fragment >= limit:
			raise DVRIPDecodeError('invalid fragment number')
		if packets[packet.fragment] is not None:
			raise DVRIPDecodeError('overlapping fragments')

		assert count < limit
		packets[packet.fragment] = packet
		count += 1
		if count < limit:
			yield None
			packet = yield None
			continue
		else:
			assert all(p is not None for p in packets)
			yield cls.frompackets(cast(List[Packet], packets))
			return


def streamfilter(type: int) -> Filter[Union[bytes, bytearray, memoryview]]:  # pylint: disable=redefined-builtin
	packet = yield None  # prime the pump
	while True:
		assert packet is not None
		if packet.type != type:
			packet = yield NotImplemented
			continue
		yield packet.payload if packet.payload else None
		if packet.end: return
		packet = yield None


class Request(Generic[_M], Message):
	reply: ClassVar[Type[_M]]
	data:  ClassVar[int]

	@classmethod
	def replies(cls, number: int) -> Filter[_M]:
		return controlfilter(cls.reply, number)

	@classmethod
	def stream(cls) -> Filter[Union[bytes, bytearray, memoryview]]:
		return streamfilter(cls.data)
