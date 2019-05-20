from datetime import datetime
from typing import List, Optional
from .message import Choice, Message, Request, Session, Status, datetimetype
from .typing import Object, fixedmember, member

__all__ = ('LogEntry', 'GetLogReply', 'LogQuery', 'GetLog')


class LogType(Choice):
	REBOOT   = 'Reboot'
	SHUTDOWN = 'ShutDown'
	LOGIN    = 'LogIn'
	LOGOUT   = 'LogOut'
	START    = 'EventStart'
	END      = 'EventStop'
	_SAVESTATE  = 'SaveSystemState' # FIXME
	_SAVECONFIG = 'SaveConfig' # FIXME


class LogEntry(Object):
	_data:  member[str]                = member('Data')  # TODO
	number: member[int]                = member('Position')
	time:   member[Optional[datetime]] = member('Time', datetimetype)
	type:   member[LogType]            = member('Type')  # TODO
	user:   member[str]                = member('User')


class GetLogReply(Object, Message):
	type = 1443

	status:  member[Status]  = member('Ret')
	session: member[Session] = member('SessionID')
	command: fixedmember     = fixedmember('Name', 'OPLogQuery')
	entries: member[Optional[List[LogEntry]]] = member('OPLogQuery')


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
