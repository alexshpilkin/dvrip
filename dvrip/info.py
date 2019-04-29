from enum     import Enum, unique
from .errors  import DVRIPDecodeError
from .message import ControlMessage, ControlRequest, Session, Status, hextype
from .typing  import Object, absentmember, for_json, json_to, member, \
                     optionalmember

__all__ = ('Info', 'SystemInfo', 'GetInfoReply', 'GetInfo')


_json_to_str = json_to(str)

def _json_to_version(datum):
	datum = _json_to_str(datum)
	return None if datum == 'Unknown' else datum

def _version_for_json(value):
	if value == 'Unknown':
		raise ValueError("argument must not be 'Unknown'")
	return for_json('Unknown' if value is None else value)

_versiontype = (_json_to_version, _version_for_json)


@unique
class Info(Enum):
	def __repr__(self):
		return '{}.{}'.format(type(self).__qualname__, self.name)

	def __str__(self):
		return self.value

	def for_json(self):
		return for_json(self.value)

	@classmethod
	def json_to(cls, datum):
		try:
			return cls(json_to(str)(datum))
		except ValueError:
			raise DVRIPDecodeError('not a known info category')

	SYSTEM = 'SystemInfo'
	_STORAGE = 'StorageInfo' # TODO
	_STATUS  = 'WorkState' # TODO

class SystemInfo(Object):
	# pylint: disable=line-too-long
	triggerin:   member[int] = member('AlarmInChannel')
	triggerout:  member[int] = member('AlarmOutChannel')
	build:       member[str] = member('BuildTime')
	cryptover:   member[str] = member('EncryptVersion', _versiontype)
	hardwarever: member[str] = member('HardWareVersion', _versiontype)
	serial:      member[str] = member('SerialNo')
	softwarever: member[str] = member('SoftWareVersion', _versiontype)
	commin:      member[int] = member('TalkInChannel')
	commout:     member[int] = member('TalkOutChannel')
	videoin:     member[int] = member('VideoInChannel')
	videoout:    member[int] = member('VideoOutChannel')
	views:       member[int] = member('ExtraChannel')
	audioin:     member[int] = member('AudioInChannel')
	uptime:      member[int] = member('DeviceRunTime', hextype)  # minutes
	_digitalin:  optionalmember[int] = optionalmember('DigChannel')  # FIXME unclear
	_updatatime: optionalmember[str] = optionalmember('UpdataTime')  # FIXME unclear
	hardware:    optionalmember[str] = optionalmember('HardWare')
	_combine:    optionalmember[int] = optionalmember('CombineSwitch')  # FIXME unclear
	_updatatype: optionalmember[int] = optionalmember('UpdataType', hextype)  # FIXME unclear
	chassis:     absentmember[str] = absentmember()  # from _logininfo


class GetInfoReply(Object, ControlMessage):
	type = 1021

	status:   member[Status]     = member('Ret')
	category: member[Info]       = member('Name')
	session:  member[Session]    = member('SessionID')
	system:   member[SystemInfo] = optionalmember('SystemInfo')


class GetInfo(Object, ControlRequest):
	type  = 1020
	reply = GetInfoReply

	category: member[Info]    = member('Name')
	session:  member[Session] = member('SessionID')
