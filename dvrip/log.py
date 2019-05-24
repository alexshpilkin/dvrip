from datetime import datetime
from enum import Enum
from typing import List, Optional, Type, TypeVar
from .errors import DVRIPDecodeError
from .message import Choice, Message, Request, Session, Status, datetimetype
from .typing import Object, Value, fixedmember, for_json, json_to, member

__all__ = ('ConnectionEntry', 'RecordTrigger', 'RecordEntry', 'EntryType',
           'Entry', 'GetLogReply', 'LogQuery', 'GetLog')

_C = TypeVar('_C', bound='ConnectionEntry')
_E = TypeVar('_E', bound='Entry')
_R = TypeVar('_R', bound='RecordEntry')
_T = TypeVar('_T', bound='EntryType')

_json_to_str = json_to(str)


class ConnectionEntry(Value):
	__slots__ = ('user', 'service', 'host')

	def __init__(self, *,
	             user: str,
	             service: str,
	             host: Optional[str] = None
	            ) -> None:
		self.user    = user
		self.service = service
		self.host    = host

	def __str__(self) -> str:
		return ('user {} service {}'.format(self.user, self.service) +
		        (' host {}'.format(self.host)
		         if self.host is not None
		         else ''))

	def __repr__(self) -> str:
		return ('{}(user={!r}, service={!r}, host={!r})'
		        .format(type(self).__qualname__,
		                self.user,
		                self.service,
		                self.host))

	def __eq__(self, other: object):
		if not isinstance(other, ConnectionEntry):
			return NotImplemented
		return (self.user == other.user and
		        self.service == other.service and
		        self.host == other.host)

	def for_json(self) -> object:
		return for_json('{},{}'
		                .format(self.user,
		                        '{}:{}'.format(self.service, self.host)
		                        if self.host is not None
		                        else self.service))

	@classmethod
	def json_to(cls: Type[_C], datum: object) -> _C:
		data = _json_to_str(datum).split(',')
		if len(data) < 2:
			raise DVRIPDecodeError('not a valid connection entry')
		# TODO len > 2 (e.g. "admin,DVRIP-Web:192.168.58.32,203")?
		user = data[0]
		service = data[1]
		host: Optional[str]
		if ':' in service:
			service, host = service.split(':', 1)
		else:
			host = None
		return cls(user=user, service=service, host=host)


class RecordTrigger(Choice):  # FIXME sync with info.TriggerInfo
	OBSCURE    = 'BlindDetect'
	DISCONNECT = 'LossDetect'
	MOTION     = 'MotionDetect'


class RecordEntry(Value):
	__slots__ = ('channel', 'trigger')

	def __init__(self, *, channel: int, trigger: RecordTrigger) -> None:
		self.channel = channel
		self.trigger = trigger

	def __str__(self) -> str:
		return ('channel {} trigger {}'
		        .format(self.channel, self.trigger.name.lower()))

	def __repr__(self) -> str:
		return ('{}(channel={!r}, trigger={!r})'
		        .format(type(self).__qualname__,
		                self.channel,
		                self.trigger))

	def __eq__(self, other: object):
		if not isinstance(other, RecordEntry):
			return NotImplemented
		return (self.channel == other.channel and
		        self.trigger == other.trigger)

	def for_json(self) -> object:
		return for_json('{},{}'.format(self.trigger.value,
		                               self.channel))

	@classmethod
	def json_to(cls: Type[_R], datum: object) -> _R:
		data = _json_to_str(datum).split(',')
		if len(data) != 2:
			raise DVRIPDecodeError('not a valid record entry')
		trigger = RecordTrigger.json_to(data[0])
		try:
			channel = int(data[1])
		except ValueError:
			raise DVRIPDecodeError('not a valid record entry')
		return cls(channel=channel, trigger=trigger)


class EntryType(Enum):  # FIXME derive from Choice
	__slots__ = ('data', 'json_to_data', '_value_')

	def __new__(cls: Type[_T], value: str, data: Type) -> _T:  # pylint:disable=unused-argument
		self = object.__new__(cls)
		self._value_ = value  # pylint: disable=protected-access
		return self

	def __init__(self, value: str, data: Type) -> None:  # pylint: disable=unused-argument
		self.data = data
		self.json_to_data = json_to(data)

	def __repr__(self) -> str:
		return '{}.{}'.format(type(self).__qualname__, self.name)

	def for_json(self) -> object:
		return for_json(self.value)

	@classmethod
	def json_to(cls: Type[_T], datum: object) -> _T:
		try:
			return cls(json_to(str)(datum))  # type: ignore  # pylint: disable=no-value-for-parameter
		except ValueError:
			raise DVRIPDecodeError('not a known entry type')

	REBOOT   = ('Reboot', str)  # TODO
	SHUTDOWN = ('ShutDown', str)  # TODO
	LOGIN    = ('LogIn', ConnectionEntry)
	LOGOUT   = ('LogOut', ConnectionEntry)
	START    = ('EventStart', RecordEntry)
	END      = ('EventStop', RecordEntry)
	SETTIME  = ('SetTime', str)  # TODO
	_SAVESTATE  = ('SaveSystemState', str)  # FIXME
	_SAVECONFIG = ('SaveConfig', str)  # FIXME


class Entry(Object):
	__slots__ = ('data',)

	number: member[int]                = member('Position')
	time:   member[Optional[datetime]] = member('Time', datetimetype)
	type:   member[EntryType]          = member('Type')  # TODO
	_user:  fixedmember                = fixedmember('User', 'System')

	def __init__(self, *, data=None, **kwargs):
		super().__init__(**kwargs)
		self.data = data

	def __repr__(self) -> str:
		r = super().__repr__()
		return r[:-1] + ', data={!r})'.format(self.data)  # FIXME hack

	def __eq__(self, other):  # FIXME type
		b = super().__eq__(other)
		return ((b and self.data == other.data)
		        if b is not NotImplemented
		        else NotImplemented)

	@staticmethod
	def _end_(value, datum):
		pop = value._popper_(datum)
		value.data = value.type.json_to_data(pop('Data'))
		return value

	def for_json(self):
		datum = super().for_json()
		push = self._pusher_(datum)
		push('Data', for_json(self.data))
		return datum


class GetLogReply(Object, Message):
	type = 1443

	status:  member[Status]  = member('Ret')
	session: member[Session] = member('SessionID')
	command: fixedmember     = fixedmember('Name', 'OPLogQuery')
	entries: member[Optional[List[Entry]]] = member('OPLogQuery')


class LogQuery(Object):
	start:    member[Optional[datetime]] = member('BeginTime', datetimetype)
	end:      member[Optional[datetime]] = member('EndTime', datetimetype)
	offset:   member[int]                = member('LogPosition')
	_type:     fixedmember                = fixedmember('Type', 'LogAll')  # TODO


class GetLog(Object, Request):
	type = 1442
	reply = GetLogReply

	session:  member[Session]  = member('SessionID')
	command:  fixedmember      = fixedmember('Name', 'OPLogQuery')
	logquery: member[LogQuery] = member('OPLogQuery')
