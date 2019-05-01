from datetime import datetime
from typing import Optional
from .message import ControlMessage, ControlRequest, Status, Session, \
                     datetimetype
from .typing import Object, fixedmember, member


class GetTimeReply(Object, ControlMessage):
	# pylint: disable=line-too-long
	type = 1453

	status:  member[Status]  = member('Ret')
	command: fixedmember     = fixedmember('Name', 'OPTimeQuery')
	session: member[Session] = member('SessionID')
	time:    member[Optional[datetime]] = member('OPTimeQuery', datetimetype)


class GetTime(Object, ControlRequest):
	type = 1452
	reply = GetTimeReply

	command: fixedmember     = fixedmember('Name', 'OPTimeQuery')
	session: member[Session] = member('SessionID')
