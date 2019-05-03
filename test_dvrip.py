from datetime import datetime
from hypothesis import given
from hypothesis.strategies import booleans, integers, none, one_of, \
                                  sampled_from, text
from io import BytesIO, RawIOBase
from mock import Mock
from pytest import fixture, raises
from socket import socket as Socket

# pylint: disable=wildcard-import,unused-wildcard-import
from dvrip import DVRIP_PORT
from dvrip.discover import _json_to_ip,  _json_to_mask, _ip_for_json, \
                           _mask_for_json
from dvrip.errors import *
from dvrip.info import *
from dvrip.info import _json_to_version, _version_for_json, _versiontype
from dvrip.io import *
from dvrip.login import *
from dvrip.message import *
from dvrip.message import _ChunkReader, _datetime_for_json, EPOCH, \
                          _json_to_datetime
from dvrip.packet import *
from dvrip.packet import _mirrorproperty
from dvrip.typing import *


def test_xmmd5_empty():
	assert xmmd5('') == 'tlJwpbo6'

def test_xmmd5_tluafed():
	assert xmmd5('tluafed') == 'OxhlwSG8'

def test_mirrorproperty():
	class Test:  # pylint: disable=too-few-public-methods
		y = _mirrorproperty('x')
	test = Test()
	test.y = 'hello'
	assert test.x == 'hello'
	del test.y
	assert getattr(test, 'x', None) is None
	test.x = 'goodbye'
	assert test.y == 'goodbye'

def test_datetime_for_json():
	assert (_datetime_for_json(datetime(2019, 4, 30, 15, 0, 0)) ==
	        '2019-04-30 15:00:00')
	assert (_datetime_for_json(datetime(2000, 1, 1, 0, 0, 0)) ==
	        '2000-00-00 00:00:00')
	assert (_datetime_for_json(None) == '0000-00-00 00:00:00')
	with raises(ValueError, match='datetime not after the epoch'):
		_datetime_for_json(datetime(1999, 1, 1, 0, 0, 0))

def test_json_to_datetime():
	assert (_json_to_datetime('2019-04-30 15:00:00') ==
	        datetime(2019, 4, 30, 15, 0, 0))
	assert (_json_to_datetime('2000-00-00 00:00:00') ==
	        datetime(2000, 1, 1, 0, 0, 0) ==
	        EPOCH)
	assert (_json_to_datetime('0000-00-00 00:00:00') == None)
	with raises(DVRIPDecodeError, match='not a datetime string'):
		_json_to_datetime('SPAM')
	with raises(DVRIPDecodeError, match='datetime not after the epoch'):
		_json_to_datetime('1999-01-01 00:00:00')

def test_ChunkReader():
	r = _ChunkReader([b'hel', b'lo'])
	assert r.readable()
	assert r.readall() == b'hello'

def test_Packet_encode():
	p = Packet(0xabcd, 0xdefa, 0x7856, b'hello',
	           fragments=0x12, fragment=0x34)
	assert p.encode().hex() == ('ff010000cdab0000fade0000'
	                            '123456780500000068656c6c6f')
	assert p.size == len(p.encode())

def test_Packet_decode():
	data = bytes.fromhex('ff010000cdab0000fade0000'
	                     '123456780500000068656c6c6f')
	assert Packet.decode(data).encode() == data

def test_Packet_decode_invalid():
	with raises(DVRIPDecodeError, match='invalid DVRIP magic'):
		Packet.decode(bytes.fromhex('fe010000cdab0000fade0000'
		                            '123456780500000068656c6c6f'))
	with raises(DVRIPDecodeError, match='unknown DVRIP version'):
		Packet.decode(bytes.fromhex('ff020000cdab0000fade0000'
		                            '123456780500000068656c6c6f'))
	with raises(DVRIPDecodeError, match='DVRIP packet too long'):
		Packet.decode(bytes.fromhex('ff010000cdab0000fade0000'
		                            '12345678ffffffff68656c6c6f'))

def test_Status_repr():
	assert repr(Status.OK) == 'Status(100)'
	assert repr(Status.ERROR) == 'Status(101)'

def test_Status_str():
	assert str(Status.OK) == 'OK'
	assert str(Status.ERROR) == 'Unknown error'

def test_Status_bool():
	# pylint: disable=no-value-for-parameter
	assert Status(100)
	assert not Status(101)

def test_Status_for_json():
	# pylint: disable=no-value-for-parameter
	assert Status(100).for_json() == 100
	assert Status(101).for_json() == 101

def test_Status_json_to():
	# pylint: disable=no-value-for-parameter
	assert Status.json_to(100) == Status(100)
	with raises(DVRIPDecodeError, match="not a known status code"):
		Status.json_to('SPAM')

@given(integers(min_value=0, max_value=0xFFFFFFFF))
def test_Session_repr(s):
	assert repr(Session(s)) == 'Session(0x{:08X})'.format(s)

@given(integers(min_value=0, max_value=0xFFFFFFFF),
       integers(min_value=0, max_value=0xFFFFFFFF))
def test_Session_eq(s, t):
	assert (Session(s) == Session(t)) == (s == t)
	assert Session(s) != False

@given(integers(min_value=0, max_value=0xFFFFFFFF))
def test_Session_hash(s):
	assert hash(Session(s)) == hash(s)

@given(integers(min_value=0, max_value=0xFFFFFFFF))
def test_Session_forjson(s):
	assert Session(s).for_json() == '0x{:08X}'.format(s)

def test_Session_jsonto():
	assert Session.json_to('0x00000057') == Session(0x57)
	with raises(DVRIPDecodeError, match="not a session ID"):
		Session.json_to('SPAM')
	with raises(DVRIPDecodeError, match="not a session ID"):
		Session.json_to('0xSPAM')

class PseudoSocket(RawIOBase):
	def __init__(self, rfile, wfile):
		self.rfile = rfile
		self.wfile = wfile

	def readable(self):
		return True

	def readinto(self, *args, **named):
		return self.rfile.readinto(*args, **named)

	def writable(self):
		return True

	def write(self, *args, **named):
		return self.wfile.write(*args, **named)

def test_Hash_repr():
	assert repr(Hash.XMMD5) == 'Hash.XMMD5'

def test_Hash_str():
	assert str(Hash.XMMD5) == 'MD5'

def test_Hash_forjson():
	assert Hash.XMMD5.for_json() == 'MD5'

def test_Hash_jsonto():
	assert Hash.json_to('MD5') == Hash.XMMD5
	with raises(DVRIPDecodeError, match='not a known hash function'):
		Hash.json_to('SPAM')

@fixture
def clitosrv():
	return BytesIO()

@fixture
def srvtocli():
	return BytesIO()

@fixture
def clifile(clitosrv, srvtocli):
	return PseudoSocket(srvtocli, clitosrv)

@fixture
def srvfile(clitosrv, srvtocli):
	return PseudoSocket(clitosrv, srvtocli)

@fixture
def clisock(clifile):
	return Mock(Socket, makefile=Mock(return_value=clifile))

@fixture
def srvsock(srvfile):
	return Mock(Socket, makefile=Mock(return_value=srvfile))

@fixture
def cliconn(clisock):
	return DVRIPClient(clisock)

@fixture
def srvconn(srvsock):
	return DVRIPServer(srvsock)

@fixture
def session():
	return Session(0x57)

@fixture
def clinoconn(cliconn, session):
	cliconn.session = session
	return cliconn

@fixture
def srvnoconn(srvconn, session):
	srvconn.session = session
	return srvconn

def test_ClientLogin_topackets(session):
	p, = tuple(ClientLogin(username='admin',
	                       passhash='tlJwpbo6',
	                       hash=Hash.XMMD5,
	                       service='DVRIP-Web')
	                      .topackets(session, 0))
	assert (p.encode() == b'\xFF\x01\x00\x00\x57\x00\x00\x00\x00\x00'
	                      b'\x00\x00\x00\x00\xE8\x03\x5D\x00\x00\x00'
	                      b'{"UserName": "admin", '
	                      b'"PassWord": "tlJwpbo6", '
	                      b'"EncryptType": "MD5", '
	                      b'"LoginType": "DVRIP-Web"}')

def test_ClientLogin_topackets_chunked(session):
	p, q = tuple(ClientLogin(username='a'*32768,
	                         passhash='tlJwpbo6',
	                         hash=Hash.XMMD5,
	                         service='DVRIP-Web')
	                        .topackets(session, 0))
	assert (p.encode() == b'\xFF\x01\x00\x00\x57\x00\x00\x00\x00\x00'
	                      b'\x00\x00\x02\x00\xE8\x03\x00\x80\x00\x00'
	                      b'{"UserName": "' + b'a' * (32768 - 14))
	assert (q.encode() == b'\xFF\x01\x00\x00\x57\x00\x00\x00\x00\x00'
	                      b'\x00\x00\x02\x01\xE8\x03\x58\x00\x00\x00' +
	                      b'a' * 14 + b'", '
	                      b'"PassWord": "tlJwpbo6", '
	                      b'"EncryptType": "MD5", '
	                      b'"LoginType": "DVRIP-Web"}')

def test_ClientLogin_frompackets_invalid():
	packet = p = Packet(0x57, 0, 1000,
	                    b'{"UserName": "admin", "PassWord": "tlJwpbo6", '
	                    b'"EncryptType": "SPAM", "LoginType": "DVRIP-Web"}'
	                    b'\x0A\x00',
	                    fragments=0, fragment=0)
	with raises(DVRIPDecodeError,
	            match='not a known hash function'):
		ClientLogin.frompackets([packet])

def test_ClientLoginReply_frompackets():
	chunks = [b'\xFF\x01\x00\x00\x57\x00\x00\x00\x00\x00',
	          b'\x00\x00\x00\x00\xE9\x03\x96\x00\x00\x00'
	          b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	          b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	          b'"ExtraChannel" : 0, "Ret" : 100, '
	          b'"SessionID" : "0x00000057" }\x0A\x00']
	m = ClientLoginReply.frompackets([Packet.load(_ChunkReader(chunks))])
	assert (m.timeout == 21 and m.channels == 4 and m.encrypt is False and
	        m.views == 0 and m.status == Status(100) and  # pylint: disable=no-value-for-parameter
	        m.session == Session(0x57))

def test_ClientLoginReply_fromchunks_empty():
	with raises(DVRIPDecodeError, match='no data in DVRIP packet'):
		ClientLoginReply.fromchunks([])

def test_controlfilter_send():
	chunks = [b'\xFF\x01\x00\x00\x57\x00\x00\x00\x00\x00',
	          b'\x00\x00\x00\x00\xe9\x03\x96\x00\x00\x00'
	          b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	          b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	          b'"ExtraChannel" : 0, "Ret" : 100, '
	          b'"SessionID" : "0x00000057" }\x0A\x00']
	replies = ClientLogin.replies(0)
	assert replies.send(None) is None
	m = replies.send(Packet.load(_ChunkReader(chunks)))
	assert (m.timeout == 21 and m.channels == 4 and m.encrypt is False and
	        m.views == 0 and m.status == Status(100) and  # pylint: disable=no-value-for-parameter
	        m.session == Session(0x57))
	with raises(StopIteration):
		replies.send(None)

def test_controlfilter_send_chunked():
	p = Packet(0x57, 0, 1001,
	           b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	           b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	           fragments=2, fragment=0)
	q = Packet(0x57, 0, 1001,
	           b'"ExtraChannel" : 0, "Ret" : 100, '
	           b'"SessionID" : "0x00000057" }\x0A\x00',
	           fragments=2, fragment=1)

	replies = ClientLogin.replies(0)
	assert replies.send(None) is None
	assert replies.send(p) is None
	assert replies.send(None) is None
	m = replies.send(q)
	assert (m.timeout == 21 and m.channels == 4 and m.encrypt is False and
	        m.views == 0 and m.status == Status(100) and  # pylint: disable=no-value-for-parameter
	        m.session == Session(0x57))
	with raises(StopIteration):
		replies.send(None)

def test_controlfilter_send_wrong_type():
	p = Packet(0x57, 0, 1002,
	           b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	           b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	           fragments=2, fragment=0)

	replies = ClientLogin.replies(0)
	assert replies.send(None) is None
	assert replies.send(p) is NotImplemented

def test_controlfilter_send_wrong_number():
	p = Packet(0x3F, 0, 1001,
	           b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	           b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	           fragments=2, fragment=0)
	q = Packet(0x3F, 57, 1001,
	           b'"ExtraChannel" : 0, "Ret" : 100, '
	           b'"SessionID" : "0x00000057" }\x0A\x00',
	           fragments=2, fragment=1)

	replies = ClientLogin.replies(0)
	assert replies.send(None) is None
	assert replies.send(p) is None
	assert replies.send(None) is None
	assert replies.send(q) is NotImplemented

def test_controlfilter_send_invalid_fragments():
	p = Packet(0x3F, 0, 1001,
	           b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	           b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	           fragments=2, fragment=0)
	q = Packet(0x3F, 0, 1001,
	           b'"ExtraChannel" : 0, "Ret" : 100, '
	           b'"SessionID" : "0x00000057" }\x0A\x00',
	           fragments=3, fragment=1)

	replies = ClientLogin.replies(0)
	assert replies.send(None) is None
	assert replies.send(p) is None
	assert replies.send(None) is None
	with raises(DVRIPDecodeError, match='conflicting fragment counts'):
		replies.send(q)

def test_controlfilter_send_invalid_overrun():
	p = Packet(0x3F, 0, 1001,
	           b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	           b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	           fragments=2, fragment=4)

	replies = ClientLogin.replies(0)
	assert replies.send(None) is None
	with raises(DVRIPDecodeError, match='invalid fragment number'):
		replies.send(p)

def test_controlfilter_send_invalid_overlap():
	p = Packet(0x3F, 0, 1001,
	           b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	           b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	           fragments=2, fragment=0)
	q = Packet(0x3F, 0, 1001,
	           b'"ExtraChannel" : 0, "Ret" : 100, '
	           b'"SessionID" : "0x00000057" }\x0A\x00',
	           fragments=2, fragment=0)

	replies = ClientLogin.replies(0)
	assert replies.send(None) is None
	assert replies.send(p) is None
	assert replies.send(None) is None
	with raises(DVRIPDecodeError, match='overlapping fragments'):
		replies.send(q)

def test_streamfilter_send(session):
	p = Packet(session.id, 0, 1426, b'hello', channel=0, end=0)
	r = Packet(session.id, 2, 1425, b'world', channel=0, end=0)
	q = Packet(session.id, 1, 1426, b'',      channel=0, end=0)
	s = Packet(session.id, 2, 1426, b'world', channel=0, end=1)

	f = streamfilter(1426)  # pylint: disable=
	assert f.send(None) is None  # prime
	assert f.send(p) == b'hello'
	assert f.send(None) is None  # re-prime
	assert f.send(q) is None
	assert f.send(None) is None
	assert f.send(r) is NotImplemented
	assert f.send(s) == b'world'
	with raises(StopIteration):
		f.send(None)  # re-prime

class ExampleRequest(ControlRequest):
	type  = 57
	reply = None  # FIXME
	data  = 42

	def for_json(self):
		return 'example'

	@classmethod
	def json_to(cls):
		return cls()

def test_ControlMessage_stream(session):
	p = Packet(session.id, 0, 42, b'hello', channel=0, end=1)
	r = ExampleRequest()
	f = r.stream()
	assert f.send(None) is None  # prime
	assert f.send(p) == b'hello'
	with raises(StopIteration):
		f.send(None)  # re-prime

def test_ClientLogout_topackets(session):
	p, = (ClientLogout(session=session).topackets(session, 0))
	assert p.encode() == (b'\xFF\x01\x00\x00\x57\x00\x00\x00\x00\x00'
	                      b'\x00\x00\x00\x00\xEA\x03\x27\x00\x00\x00'
	                      b'{"Name": "", "SessionID": "0x00000057"}')

def test_ClientLogoutReply_replies():
	data = (b'\xFF\x01\x00\x00\x57\x00\x00\x00\x00\x00'
	        b'\x00\x00\x00\x00\xeb\x03\x3A\x00\x00\x00'
	        b'{ "Name" : "", "Ret" : 100, '
	        b'"SessionID" : "0x00000057" }'
	        b'\x0A\x00')
	replies = ClientLogout.replies(0)
	assert replies.send(None) is None
	m = replies.send(Packet.decode(data))
	assert m.status == Status(100) and m.session == Session(0x57)
	with raises(StopIteration):
		replies.send(None)

def test_Client_logout(capsys, session, clinoconn, clitosrv, srvtocli):
	p, = (ClientLogoutReply(status=Status.OK,
	                        session=session)
	                       .topackets(session, 2))
	p.dump(srvtocli)
	srvtocli.seek(0)

	clinoconn.logout()
	clitosrv.seek(0); m = ClientLogout.frompackets([Packet.load(clitosrv)])
	assert m == ClientLogout(session=session)

def test_Client_logout_stray(capsys, session, clinoconn, clitosrv, srvtocli):
	p, = (ClientLogoutReply(status=Status.OK,
	                        session=session)
	                       .topackets(session, 57))
	p.dump(srvtocli)
	srvtocli.seek(0)

	with raises(DVRIPDecodeError, match='stray packet'):
		clinoconn.logout()

def test_Client_login(session, cliconn, clitosrv, srvtocli):
	p, = (ClientLoginReply(status=Status.OK,
	                       session=session,
	                       timeout=21,
	                       channels=4,
	                       views=0,
	                       chassis='HVR',
	                       encrypt=False)
	                      .topackets(session, 2))
	p.dump(srvtocli); srvtocli.seek(0)

	cliconn.connect(('example.com', DVRIP_PORT), 'admin', '')
	clitosrv.seek(0); m = ClientLogin.frompackets([Packet.load(clitosrv)])
	assert (m.username == 'admin' and m.passhash == xmmd5('') and
	        m.hash == Hash.XMMD5 and m.service == 'DVRIP-Web')

def test_Client_login_invalid(session, cliconn, clitosrv, srvtocli):
	p, = (ClientLoginReply(status=Status.ERROR,
	                       session=session,
	                       timeout=21,
	                       channels=4,
	                       views=0,
	                       chassis='HVR',
	                       encrypt=False)
	                      .topackets(session, 2))
	p.dump(srvtocli); srvtocli.seek(0)

	with raises(DVRIPRequestError, match='Unknown error'):
		try:
			cliconn.connect(('example.com', DVRIP_PORT),
			                'admin', '')
		except DVRIPRequestError as e:
			assert e.code == Status.ERROR.code
			raise

@given(text())
def test_version_jsonto(s):
	assert _json_to_version('Unknown') is None
	assert s == 'Unknown' or _json_to_version(s) == s

@given(one_of(none(), text()))
def test_version_forjson(s):
	assert _version_for_json(None) == 'Unknown'
	assert s is None or _version_for_json(s) == s
	with raises(ValueError, match='argument must not be'):
		_version_for_json('Unknown')

def test_version():
	assert _versiontype == (_json_to_version, _version_for_json)

@given(sampled_from(list(Info.__members__.values())))
def test_Info_repr(cmd):
	assert repr(cmd) == 'Info.{}'.format(cmd.name)

@given(sampled_from(list(Info.__members__.values())))
def test_Info_str(cmd):
	assert str(cmd) == cmd.value

@given(sampled_from(list(Info.__members__.values())))
def test_Info_forjson(cmd):
	assert cmd.for_json() == cmd.value

@given(sampled_from(list(Info.__members__.values())))
def test_info_jsonto(cmd):
	assert Info.json_to(cmd.value) == cmd
	with raises(DVRIPDecodeError, match='not a known'):
		Info.json_to('SPAM')

octets = lambda: integers(min_value=0, max_value=255)

@given(octets(), octets(), octets(), octets())
def test_ip_forjson(a, b, c, d):
	assert (_ip_for_json('{}.{}.{}.{}'.format(a, b, c, d)) ==
	        '0x{3:02X}{2:02X}{1:02X}{0:02X}'.format(a, b, c, d))

@given(octets(), octets(), octets(), octets())
def test_ip_jsonto(a, b, c, d):
	assert (_json_to_ip('0x{3:02X}{2:02X}{1:02X}{0:02X}'
	                    .format(a, b, c, d)) ==
	        '{}.{}.{}.{}'.format(a, b, c, d))

@given(octets(), octets(), octets(), octets())
def test_ip_forjson_jsonto(a, b, c, d):
	value = '{}.{}.{}.{}'.format(a, b, c, d)
	assert _json_to_ip(_ip_for_json(value)) == value

@given(octets(), octets(), octets(), octets())
def test_ip_jsonto_forjson(a, b, c, d):
	value = '0x{3:02X}{2:02X}{1:02X}{0:02X}'.format(a, b, c, d)
	assert _ip_for_json(_json_to_ip(value)) == value

def test_mask_forjson():
	assert _mask_for_json(24) == '0x00FFFFFF'
	assert _mask_for_json(20) == '0x000FFFFF'
	assert _mask_for_json(16) == '0x0000FFFF'
	assert _mask_for_json(8)  == '0x000000FF'

def test_mask_jsonto():
	assert _json_to_mask('0x00FFFFFF') == 24
	assert _json_to_mask('0x000FFFFF') == 20
	assert _json_to_mask('0x0000FFFF') == 16
	assert _json_to_mask('0x000000FF') == 8
