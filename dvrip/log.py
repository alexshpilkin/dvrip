from datetime import datetime
from typing import List, Optional, Type, TypeVar
from .errors import DVRIPDecodeError
from .message import Choice, Message, Request, Session, Status, datetimetype
from .typing import Object, Value, fixedmember, for_json, json_to, member

__all__ = ('ConnectionEntry', 'EntryType', 'Entry', 'GetLogReply', 'LogQuery',
           'GetLog')

_C = TypeVar('_C', bound='ConnectionEntry')
_E = TypeVar('_E', bound='Entry')


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
		datum = _json_to_str(datum)
		if ',' not in datum:
			raise DVRIPDecodeError('not a valid connection entry')
		user, service = datum.split(',', 1)
		host: Optional[str]
		if ':' in service:
			service, host = service.split(':', 1)
		else:
			host = None
		return cls(user=user, service=service, host=host)


class EntryType(Choice):
	REBOOT   = 'Reboot'
	SHUTDOWN = 'ShutDown'
	LOGIN    = 'LogIn'
	LOGOUT   = 'LogOut'
	START    = 'EventStart'
	END      = 'EventStop'
	SETTIME  = 'SetTime'
	_SAVESTATE  = 'SaveSystemState' # FIXME
	_SAVECONFIG = 'SaveConfig' # FIXME


class Entry(Object):
	#__slots__ = ('data',)

	number: member[int]                = member('Position')
	time:   member[Optional[datetime]] = member('Time', datetimetype)
	type:   member[EntryType]          = member('Type')  # TODO
	_user:  fixedmember                = fixedmember('User', 'System')
	_data:  member[str]                = member('Data')


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
