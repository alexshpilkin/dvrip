from datetime import datetime
from typing import Optional
from .message import Choice, ControlRequest, ControlMessage, Session, Status, \
                     datetimetype
from .typing import Object, fixedmember, member


class DoPlaybackReply(Object, ControlMessage):
	type = 1421

	status:  member[Status]  = member('Ret')
	command: fixedmember     = fixedmember('Name', 'OPPlayBack')
	session: member[Session] = member('SessionID')

class Action(Choice):
	CLAIM          = 'Claim'
	_STREAMSTART   = 'Start'  # TODO
	_STREAMSTOP    = 'Stop'   # TODO
	DOWNLOADSTART = 'DownloadStart'
	DOWNLOADSTOP  = 'DownloadStop'

class Params(Object):
	# TODO there are more
	name:      member[str] = member('FileName')
	transport: fixedmember = fixedmember('TransMode', 'TCP')  # TODO

class Playback(Object):
	action: member[Action] = member('Action')
	params: member[Params] = member('Parameter')
	start:  member[Optional[datetime]] = member('StartTime', datetimetype)
	end:    member[Optional[datetime]] = member('EndTime', datetimetype)

class DoPlayback(Object, ControlRequest):
	type  = 1420
	reply = DoPlaybackReply

	command:  fixedmember      = fixedmember('Name', 'OPPlayBack')
	session:  member[Session]  = member('SessionID')
	playback: member[Playback] = member('OPPlayBack')


class ClaimReply(DoPlaybackReply):
	type = 1425

class Claim(DoPlayback):
	type = 1424
	data = 1426
	reply = ClaimReply
