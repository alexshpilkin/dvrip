from .message import Message, Session, Status, hextype
from .typing import Object, fixedmember, member


_json_to_hex, _hex_for_json = hextype

def _ip_for_json(value: str) -> object:
	a, b, c, d = (int(x) for x in value.split('.'))
	return _hex_for_json((d << 24) | (c << 16) | (b << 8) | a)

def _json_to_ip(datum: object) -> str:
	datum = _json_to_hex(datum)
	d = (datum >> 24) & 0xFF
	c = (datum >> 16) & 0xFF
	b = (datum >>  8) & 0xFF
	a = (datum      ) & 0xFF
	return '{}.{}.{}.{}'.format(a, b, c, d)

_iptype = (_json_to_ip, _ip_for_json)


def _mask_for_json(value: int) -> object:
	value = (0xFFFFFFFF >> (32 - value)) & 0xFFFFFFFF  # little endian!
	return _hex_for_json(value)

def _json_to_mask(datum: object) -> int:
	datum = _json_to_hex(datum)
	value = 0
	while datum:
		datum >>= 1
		value += 1
	return value

_masktype = (_json_to_mask, _mask_for_json)


class Host(Object):
	_type:      fixedmember = fixedmember('DeviceType', 1)  # TODO
	serial:    member[str] = member('SN')
	mac:       member[str] = member('MAC')
	router:    member[str] = member('GateWay', _iptype)
	host:      member[str] = member('HostIP', _iptype)
	mask:      member[int] = member('Submask', _masktype)  # FIXME
	name:      member[str] = member('HostName')
	tcpport:   member[int] = member('TCPPort')
	udpport:   member[int] = member('UDPPort')
	httpport:  member[int] = member('HttpPort')
	httpsport: member[int] = member('SSLPort')
	channels:  member[int] = member('ChannelNum')
	_maxconn:   member[int] = member('TCPMaxConn')
	_transport: fixedmember = fixedmember('MonMode', 'TCP')  # TODO
	_maxbps:    member[int] = member('MaxBps')
	_plan:      fixedmember = fixedmember('TransferPlan', 'AutoAdapt')  # TODO
	_hs:        fixedmember = fixedmember('UseHSDownLoad', False)  # TODO
	_state:     member[int] = member('NetConnectState')  # TODO
	_others:    member[str] = member('OtherFunction')  # TODO

class DiscoverReply(Object, Message):
	type = 1531

	status:  member[Status]  = member('Ret')
	session: member[Session] = member('SessionID')
	host:    member[Host]    = member('NetWork.NetCommon')
