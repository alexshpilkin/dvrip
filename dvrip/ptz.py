from .message import Choice, Message, Request, Session, Status
from .typing import Object, fixedmember, member


class DoPTZReply(Object, Message):
	type = 1401

	status:  member[Status]  = member('Ret')
	session: member[Session] = member('SessionID')
	command: fixedmember     = fixedmember('Name', '')


class PTZButton(Choice):
	MENU      = 'Menu'
	RIGHT     = 'DirectionRight'
	RIGHTUP   = 'DirectionRightUp'
	UP        = 'DirectionUp'
	LEFTUP    = 'DirectionLeftUp'
	LEFT      = 'DirectionLeft'
	LEFTDOWN  = 'DirectionLeftDown'
	DOWN      = 'DirectionDown'
	RIGHTDOWN = 'DirectionRightDown'
	IN        = 'ZoomTile' # FIXME
	OUT       = 'ZoomWide'
	NEAR      = 'FocusNear'
	FAR       = 'FocusFar'
	OPEN      = 'IrisLarge'
	CLOSE     = 'IrisSmall'
	STILL     = 'AutoPanOff'
	PAN       = 'AutoPanOn'
	_GOTOPRESET  = 'GotoPreset'  # TODO
	_SETPRESET   = 'SetPreset'  # TODO
	_CLEARPRESET = 'ClearPreset'  # TODO
	_STARTTOUR   = 'StartTour'  # TODO
	_ENDTOUR     = 'EndTour'  # TODO


class PTZParams(Object):
	# pylint: disable=line-too-long
	_aux:     fixedmember = fixedmember('AUX', {'Number': 0, 'Status': 'On'})  # TODO
	channel: member[int] = member('Channel')
	_menu:    fixedmember = fixedmember('MenuOpts', 'Enter')  # TODO
	_point:   fixedmember = fixedmember('POINT', {'bottom': 0, 'left': 0, 'right': 0, 'top': 0})  # TODO
	_pattern: fixedmember = fixedmember('Pattern', 'SetBegin')  # TODO
	_preset:  fixedmember = fixedmember('Preset', 65535)  # TODO
	_step:    fixedmember = fixedmember('Step', 5)  # TODO
	_tour:    fixedmember = fixedmember('Tour', 0)  # TODO


class PTZ(Object):
	button: member[PTZButton] = member('Command')
	params: member[PTZParams] = member('Parameter')


class DoPTZ(Object, Request):
	type  = 1400
	reply = DoPTZReply

	session: member[Session] = member('SessionID')
	command: fixedmember     = fixedmember('Name', 'OPPTZControl')
	ptz:     member[PTZ]     = member('OPPTZControl')
