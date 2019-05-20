from datetime import datetime
from typing import Optional
from .message import Choice, Request, Message, Session, Status, datetimetype
from .typing import Object, fixedmember, member


class DoPlaybackReply(Object, Message):
	type = 1421

	status:  member[Status]  = member('Ret')
	command: fixedmember     = fixedmember('Name', 'OPPlayBack')
	session: member[Session] = member('SessionID')


class PlaybackAction(Choice):
	CLAIM         = 'Claim'
	START         = 'Start'
	PAUSE         = 'Pause'
	FAST          = 'Fast'
	SLOW          = 'Slow'
	STOP          = 'Stop'
	DOWNLOADSTART = 'DownloadStart'
	DOWNLOADSTOP  = 'DownloadStop'

class PlaybackParams(Object):
	# TODO there are more
	name:      member[str] = member('FileName')
	transport: fixedmember = fixedmember('TransMode', 'TCP')  # TODO

class Playback(Object):
	action: member[PlaybackAction] = member('Action')
	params: member[PlaybackParams] = member('Parameter')
	start:  member[Optional[datetime]] = member('StartTime', datetimetype)
	end:    member[Optional[datetime]] = member('EndTime', datetimetype)

class DoPlayback(Object, Request):
	type  = 1420
	reply = DoPlaybackReply

	command:  fixedmember      = fixedmember('Name', 'OPPlayBack')
	session:  member[Session]  = member('SessionID')
	playback: member[Playback] = member('OPPlayBack')


class PlaybackClaimReply(DoPlaybackReply):
	type = 1425


class PlaybackClaim(DoPlayback):
	type  = 1424
	reply = PlaybackClaimReply
	data  = 1426
