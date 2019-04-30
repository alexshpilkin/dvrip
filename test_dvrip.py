from datetime import datetime
from hypothesis import given
from hypothesis.strategies import booleans, integers, none, one_of, \
                                  sampled_from, text
from io import BytesIO, RawIOBase
from mock import Mock
from pytest import fixture, raises
from socket import socket as Socket

# pylint: disable=wildcard-import,unused-wildcard-import
from dvrip         import *
from dvrip.info    import _json_to_version, _version_for_json, _versiontype
from dvrip.message import _ChunkReader, _datetime_for_json, EPOCH, \
                          _json_to_datetime
from dvrip.packet  import _mirrorproperty


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
		                            '123456780140000068656c6c6f'))

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
	return Client(clisock)

@fixture
def srvconn(srvsock):
	return Server(srvsock)

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
	                      b'\x00\x00\x00\x00\xE8\x03\x5F\x00\x00\x00'
	                      b'{"UserName": "admin", '
	                      b'"PassWord": "tlJwpbo6", '
	                      b'"EncryptType": "MD5", '
	                      b'"LoginType": "DVRIP-Web"}'
	                      b'\x0A\x00')

def test_ClientLogin_topackets_chunked(session):
	p, q = tuple(ClientLogin(username='a'*16384,
	                         passhash='tlJwpbo6',
	                         hash=Hash.XMMD5,
	                         service='DVRIP-Web')
	                        .topackets(session, 0))
	assert (p.encode() == b'\xFF\x01\x00\x00\x57\x00\x00\x00\x00\x00'
	                      b'\x00\x00\x02\x00\xE8\x03\x00\x40\x00\x00'
	                      b'{"UserName": "' + b'a' * (16384 - 14))
	assert (q.encode() == b'\xFF\x01\x00\x00\x57\x00\x00\x00\x00\x00'
	                      b'\x00\x00\x02\x01\xE8\x03\x5A\x00\x00\x00' +
	                      b'a' * 14 + b'", '
	                      b'"PassWord": "tlJwpbo6", '
	                      b'"EncryptType": "MD5", '
	                      b'"LoginType": "DVRIP-Web"}\x0A\x00')

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
	          b'\x00\x00\x00\x00\xe9\x03\x96\x00\x00\x00'
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

def test_ControlFilter_accept():
	chunks = [b'\xFF\x01\x00\x00\x57\x00\x00\x00\x00\x00',
	          b'\x00\x00\x00\x00\xe9\x03\x96\x00\x00\x00'
	          b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	          b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	          b'"ExtraChannel" : 0, "Ret" : 100, '
	          b'"SessionID" : "0x00000057" }\x0A\x00']
	replies = ClientLogin.replies(0)
	(n, m), = replies.accept(Packet.load(_ChunkReader(chunks)))
	assert n == 0
	assert (m.timeout == 21 and m.channels == 4 and m.encrypt is False and
	        m.views == 0 and m.status == Status(100) and  # pylint: disable=no-value-for-parameter
	        m.session == Session(0x57))

def test_ControlFilter_accept_chunked():
	p = Packet(0x57, 0, 1001,
	           b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	           b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	           fragments=2, fragment=0)
	q = Packet(0x57, 0, 1001,
	           b'"ExtraChannel" : 0, "Ret" : 100, '
	           b'"SessionID" : "0x00000057" }\x0A\x00',
	           fragments=2, fragment=1)

	replies = ClientLogin.replies(0)
	() = replies.accept(p)
	(n, m), = replies.accept(q)
	assert n == 0
	assert (m.timeout == 21 and m.channels == 4 and m.encrypt is False and
	        m.views == 0 and m.status == Status(100) and  # pylint: disable=no-value-for-parameter
	        m.session == Session(0x57))

def test_ControlFilter_accept_wrong_type():
	p = Packet(0x57, 0, 1002,
	           b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	           b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	           fragments=2, fragment=0)

	replies = ClientLogin.replies(0)
	assert replies.accept(p) is None

def test_ControlFilter_accept_wrong_number():
	p = Packet(0x3F, 0, 1001,
	           b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	           b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	           fragments=2, fragment=0)
	q = Packet(0x3F, 57, 1001,
	           b'"ExtraChannel" : 0, "Ret" : 100, '
	           b'"SessionID" : "0x00000057" }\x0A\x00',
	           fragments=2, fragment=1)

	replies = ClientLogin.replies(0)
	() = replies.accept(p)
	assert replies.accept(q) is None

def test_ControlFilter_accept_invalid_fragments():
	p = Packet(0x3F, 0, 1001,
	           b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	           b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	           fragments=2, fragment=0)
	q = Packet(0x3F, 0, 1001,
	           b'"ExtraChannel" : 0, "Ret" : 100, '
	           b'"SessionID" : "0x00000057" }\x0A\x00',
	           fragments=3, fragment=1)

	replies = ClientLogin.replies(0)
	() = replies.accept(p)
	with raises(DVRIPDecodeError, match='conflicting fragment counts'):
		replies.accept(q)

def test_ControlFilter_accept_invalid_overrun():
	p = Packet(0x3F, 0, 1001,
	           b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	           b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	           fragments=2, fragment=4)

	replies = ClientLogin.replies(0)
	with raises(DVRIPDecodeError, match='invalid fragment number'):
		replies.accept(p)

def test_ControlFilter_accept_invalid_overlap():
	p = Packet(0x3F, 0, 1001,
	           b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	           b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	           fragments=2, fragment=0)
	q = Packet(0x3F, 0, 1001,
	           b'"ExtraChannel" : 0, "Ret" : 100, '
	           b'"SessionID" : "0x00000057" }\x0A\x00',
	           fragments=2, fragment=0)

	replies = ClientLogin.replies(0)
	() = replies.accept(p)
	with raises(DVRIPDecodeError, match='overlapping fragments'):
		replies.accept(q)

def test_ClientLogout_topackets(session):
	p, = (ClientLogout(username='admin', session=session)
	                  .topackets(session, 0))
	assert p.encode() == (b'\xFF\x01\x00\x00\x57\x00\x00\x00\x00\x00'
	                      b'\x00\x00\x00\x00\xEA\x03\x2E\x00\x00\x00'
	                      b'{"Name": "admin", "SessionID": "0x00000057"}'
	                      b'\x0A\x00')

def test_ClientLogoutReply_accept():
	data = (b'\xFF\x01\x00\x00\x57\x00\x00\x00\x00\x00'
	        b'\x00\x00\x00\x00\xeb\x03\x3A\x00\x00\x00'
	        b'{ "Name" : "", "Ret" : 100, '
	        b'"SessionID" : "0x00000057" }\x0A\x00')
	replies = ClientLogout.replies(0)
	(n, m), = replies.accept(Packet.decode(data))
	assert n == 0
	assert (m.username == "" and m.status == Status(100) and  # pylint: disable=no-value-for-parameter
	        m.session == Session(0x57))

def test_Client_logout(capsys, session, clinoconn, clitosrv, srvtocli):
	p, = (ClientLogoutReply(status=Status.OK,
	                        username='admin',
	                        session=session)
	                       .topackets(session, 2))
	p.dump(srvtocli)
	p, = (ClientLogoutReply(status=Status.OK,
	                        username='admin',
	                        session=session)
	                       .topackets(session, 1))
	p.dump(srvtocli)
	srvtocli.seek(0)

	clinoconn.username = 'admin'
	clinoconn.logout()
	clitosrv.seek(0); m = ClientLogout.frompackets([Packet.load(clitosrv)])
	assert m == ClientLogout(username='admin', session=session)
	out1, out2 = capsys.readouterr().out.split('\n')
	assert out1.startswith('unrecognized packet: ') and out2 == ''

def test_Client_login(session, cliconn, clitosrv, srvtocli):
	p, = (ClientLoginReply(status=Status.OK,
	                       session=session,
	                       timeout=21,
	                       channels=4,
	                       views=0,
	                       chassis='HVR',
	                       encrypt=False)
	                      .topackets(session, 1))
	p.dump(srvtocli); srvtocli.seek(0)

	cliconn.connect(('example.com', cliconn.PORT), 'admin', '')
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
	                      .topackets(session, 1))
	p.dump(srvtocli); srvtocli.seek(0)

	with raises(DVRIPRequestError, match='Unknown error'):
		try:
			cliconn.connect(('example.com', cliconn.PORT),
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
def test_Info_repr(cat):
	assert repr(cat) == 'Info.{}'.format(cat.name)

@given(sampled_from(list(Info.__members__.values())))
def test_Info_str(cat):
	assert str(cat) == cat.value

@given(sampled_from(list(Info.__members__.values())))
def test_Info_forjson(cat):
	assert cat.for_json() == cat.value

@given(sampled_from(list(Info.__members__.values())))
def test_info_jsonto(cat):
	assert Info.json_to(cat.value) == cat
	with raises(DVRIPDecodeError, match='not a known info category'):
		Info.json_to('SPAM')
