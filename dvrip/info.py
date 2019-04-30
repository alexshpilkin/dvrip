from datetime import datetime
from enum     import Enum, unique
from typing   import List, Optional
from .errors  import DVRIPDecodeError
from .message import ControlMessage, ControlRequest, Session, Status, \
                     datetimetype, hextype
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

	SYSTEM   = 'SystemInfo'
	STORAGE  = 'StorageInfo'
	ACTIVITY = 'WorkState'


class SystemInfo(Object):
	# pylint: disable=line-too-long
	triggerin:   member[int] = member('AlarmInChannel')
	triggerout:  member[int] = member('AlarmOutChannel')
	build:       member[Optional[datetime]] = member('BuildTime', datetimetype)
	eeprom:      member[str] = member('EncryptVersion', _versiontype)
	hardware:    member[str] = member('HardWareVersion', _versiontype)
	serial:      member[str] = member('SerialNo')
	software:    member[str] = member('SoftWareVersion', _versiontype)
	commin:      member[int] = member('TalkInChannel')
	commout:     member[int] = member('TalkOutChannel')
	videoin:     member[int] = member('VideoInChannel')
	videoout:    member[int] = member('VideoOutChannel')
	views:       member[int] = member('ExtraChannel')
	audioin:     member[int] = member('AudioInChannel')
	uptime:      member[int] = member('DeviceRunTime', hextype)  # minutes

	_digitalin:  optionalmember[int] = optionalmember('DigChannel')  # FIXME unclear
	_updatatime: optionalmember[str] = optionalmember('UpdataTime')  # FIXME unclear
	board:       optionalmember[str] = optionalmember('HardWare')
	_combine:    optionalmember[int] = optionalmember('CombineSwitch')  # FIXME unclear
	_updatatype: optionalmember[int] = optionalmember('UpdataType', hextype)  # FIXME unclear

	chassis:     absentmember[str] = absentmember()  # from _logininfo


class PartitionInfo(Object):
	# pylint: disable=line-too-long
	_number:       member[int]  = member('LogicSerialNo')  # FIXME unclear
	_driver:       member[int]  = member('DirverType')  # FIXME unclear
	current:       member[bool] = member('IsCurrent')
	_status:       member[int]  = member('Status')  # FIXME unclear
	size:          member[int]  = member('TotalSpace', hextype)   # 2**20 bytes
	free:          member[int]  = member('RemainSpace', hextype)  # 2**20 bytes
	viewedstart:   member[Optional[datetime]] = member('OldStartTime', datetimetype)  # FIXME unclear (et seqq)
	viewedend:     member[Optional[datetime]] = member('OldEndTime', datetimetype)
	unviewedstart: member[Optional[datetime]] = member('NewStartTime', datetimetype)
	unviewedend:   member[Optional[datetime]] = member('NewEndTime', datetimetype)

class DiskInfo(Object):
	number:   member[int]                 = member('PlysicalNo')
	parts:    member[int]                 = member('PartNumber')
	partinfo: member[List[PartitionInfo]] = member('Partition')

StorageInfo = List[DiskInfo]


class TriggerInfo(Object):
	in_:        member[int] = member('AlarmIn')
	out:        member[int] = member('AlarmOut')
	obscure:    member[int] = member('VideoBlind')
	disconnect: member[int] = member('VideoLoss')
	motion:     member[int] = member('VideoMotion')

class ChannelInfo(Object):
	bitrate:   member[int]  = member('Bitrate') # 2**10 bits/second
	recording: member[bool] = member('Record')

class ActivityInfo(Object):
	triggers: member[TriggerInfo]       = member('AlarmState')
	channels: member[List[ChannelInfo]] = member('ChannelState')


class GetInfoReply(Object, ControlMessage):
	type = 1021

	status:   member[Status]  = member('Ret')
	category: member[Info]    = member('Name')
	session:  member[Session] = member('SessionID')
	system:   optionalmember[SystemInfo]   = optionalmember('SystemInfo')
	storage:  optionalmember[StorageInfo]  = optionalmember('StorageInfo')
	activity: optionalmember[ActivityInfo] = optionalmember('WorkState')

	# FIXME mutual exclusion?


class GetInfo(Object, ControlRequest):
	type  = 1020
	reply = GetInfoReply

	category: member[Info]    = member('Name')
	session:  member[Session] = member('SessionID')
