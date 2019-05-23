from enum import unique
from datetime import datetime
from typing import Optional
from .message import Choice, Message, Request, Status, Session, datetimetype
from .typing import Object, fixedmember, member, optionalmember


@unique
class Operation(Choice):
	UNKNOWN  = ''
	MACHINE  = 'OPMachine'
	LOG      = 'OPLogManager'
	RESET    = 'OPDefaultConfig'
	SETTIME  = 'OPTimeSetting'


@unique
class Machine(Choice):
	REBOOT = 'Reboot'


class MachineOperation(Object):
	action: member[Machine] = member('Action')


@unique
class Log(Choice):
	CLEAR = 'RemoveAll'


class LogOperation(Object):
	action: member[Log] = member('Action')


class ResetOperation(Object):
	accounts:  member[bool] = member('Account')
	triggers:  member[bool] = member('Alarm')
	ptz:       member[bool] = member('CommPtz')
	encoding:  member[bool] = member('Encode')
	general:   member[bool] = member('General')
	network:   member[bool] = member('NetCommon')
	_server:   member[bool] = member('NetServer')  # FIXME
	_preview:  member[bool] = member('Preview')  # FIXME
	recording: member[bool] = member('Record')


class DoOperationReply(Object, Message):
	# pylint: disable=line-too-long
	type = 1451

	status:  member[Status]   = member('Ret')
	command: member[Operation]= member('Name')
	session: member[Session]  = member('SessionID')


class DoOperation(Object, Request):
	# pylint: disable=line-too-long
	type = 1450
	reply = DoOperationReply

	command: member[Operation] = member('Name')
	session: member[Session]   = member('SessionID')
	machine: optionalmember[MachineOperation]   = optionalmember('OPMachine')
	log:     optionalmember[MachineOperation]   = optionalmember('OPLogManager')
	reset:   optionalmember[ResetOperation]     = optionalmember('OPDefaultConfig')
	settime: optionalmember[Optional[datetime]] = optionalmember('OPTimeSetting', datetimetype)


class GetTimeReply(Object, Message):
	# pylint: disable=line-too-long
	type = 1453

	status:  member[Status]  = member('Ret')
	command: fixedmember     = fixedmember('Name', 'OPTimeQuery')
	session: member[Session] = member('SessionID')
	gettime: member[Optional[datetime]] = member('OPTimeQuery', datetimetype)


class GetTime(Object, Request):
	type = 1452
	reply = GetTimeReply

	command: fixedmember     = fixedmember('Name', 'OPTimeQuery')
	session: member[Session] = member('SessionID')
