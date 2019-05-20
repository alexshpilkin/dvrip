from .message import Choice, Request, Message, Session, Status
from .typing import Object, fixedmember, member


class DoMonitorReply(Object, Message):
	type = 1411

	status:  member[Status]  = member('Ret')
	session: member[Session] = member('SessionID')
	command: fixedmember     = fixedmember('Name', 'OPMonitor')


class MonitorAction(Choice):
	CLAIM = 'Claim'
	START = 'Start'
	STOP  = 'Stop'

class Stream(Choice):
	HD = 'Main'
	SD = 'Extra'

class MonitorParams(Object):
	# TODO there are more
	channel:   member[int]    = member('Channel')
	stream:    member[Stream] = member('StreamType')
	transport: fixedmember    = fixedmember('TransMode', 'TCP')  # TODO

class Monitor(Object):
	action: member[MonitorAction] = member('Action')
	params: member[MonitorParams] = member('Parameter')


class DoMonitor(Object, Request):
	type  = 1410
	reply = DoMonitorReply

	session: member[Session] = member('SessionID')
	command: fixedmember     = fixedmember('Name', 'OPMonitor')
	monitor: member[Monitor] = member('OPMonitor')


class MonitorClaimReply(DoMonitorReply):
	type = 1414


class MonitorClaim(DoMonitor):
	type  = 1413
	reply = MonitorClaimReply
	data  = 1412
