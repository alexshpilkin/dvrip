from hypothesis import given
from hypothesis.strategies \
                import booleans, integers, sampled_from, text
from io         import BytesIO, RawIOBase
from mock       import Mock
from pytest     import fixture, raises
from socket     import socket as Socket

# pylint: disable=wildcard-import,unused-wildcard-import
from dvrip         import *
from dvrip.message import _ChunkReader
from dvrip.packet  import _mirrorproperty
from dvrip.utils   import checkbool, checkdict, checkempty, checkint, \
                          checkstr, popkey


def test_md5crypt_empty():
	assert md5crypt(b'') == b'tlJwpbo6'

def test_md5crypt_tluafed():
	assert md5crypt(b'tluafed') == b'OxhlwSG8'

def test_checkbool_invalid():
	with raises(DVRIPDecodeError, match='not a boolean in test'):
		checkbool(None, 'test')

def test_checkint_invalid():
	with raises(DVRIPDecodeError, match='not an integer in test'):
		checkint(None, 'test')

def test_checkstr_invalid():
	with raises(DVRIPDecodeError, match='not a string in test'):
		checkstr(None, 'test')

def test_checkdict_invalid():
	with raises(DVRIPDecodeError, match='not a dictionary in test'):
		checkdict(None, 'test')

def test_checkempty_invalid():
	with raises(DVRIPDecodeError, match='extra keys in test'):
		checkempty({'spam': 'sausages'}, 'test')

def test_popkey_invalid():
	with raises(DVRIPDecodeError, match='test missing'):
		popkey({'spam': 'sausages'}, 'ham', 'test')

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
	with raises(DVRIPDecodeError, match="'SPAM' is not a valid status code"):
		Status.json_to('SPAM')

def test_Session_repr():
	assert repr(Session(0x42)) == 'Session(0x00000042)'
	assert repr(Session(0x57)) == 'Session(0x00000057)'

def test_Session_hash():
	assert hash(Session(0x42)) == hash(0x42)
	assert hash(Session(0x57)) == hash(0x57)

def test_Session_for_json():
	assert Session(0x42).for_json() == '0x00000042'
	assert Session(0x57).for_json() == '0x00000057'

def test_Session_json_to():
	assert Session.json_to('0x00000057') == Session(0x57)
	with raises(DVRIPDecodeError, match="'SPAM' is not a valid session ID"):
		Session.json_to('SPAM')
	with raises(DVRIPDecodeError, match="'0xSPAM' is not a valid session ID"):
		Session.json_to('0xSPAM')
	with raises(DVRIPDecodeError, match="'0x59AE' is not a valid session ID"):
		Session.json_to('0x59AE')

@fixture
def rfile():
	return BytesIO()

@fixture
def wfile():
	return BytesIO()

class SFile(RawIOBase):
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

@fixture
def sfile(rfile, wfile):
	return SFile(rfile, wfile)

@fixture
def sock(sfile):
	return Mock(Socket, makefile=Mock(return_value=sfile))

@fixture
def conn(sock):
	return Connection(sock)

@fixture
def noconn(conn):
	conn.session = Session(0x57)
	return conn

def test_ClientLogin_repr():
	assert (repr(ClientLogin('admin', passhash='def', service='abc')) ==
	        "ClientLogin('admin', passhash='def', service='abc')")

def test_ClientLogin_eq():
	assert ClientLogin('admin', '') == ClientLogin('admin', '')
	assert ClientLogin('admin', '') != ClientLogin('spam', '')
	assert ClientLogin('admin', '') != ClientLogin('admin', 'spam')
	assert ClientLogin('admin', '') != Ellipsis
 
def test_ClientLogin_topackets(noconn):
	p, = tuple(ClientLogin('admin', '').topackets(noconn))
	assert (p.encode() == b'\xFF\x01\x00\x00\x57\x00\x00\x00\x00\x00'
	                      b'\x00\x00\x00\x00\xE8\x03\x5F\x00\x00\x00'
	                      b'{"UserName": "admin", '
	                      b'"PassWord": "tlJwpbo6", '
	                      b'"EncryptType": "MD5", '
	                      b'"LoginType": "DVRIP-Web"}'
	                      b'\x0A\x00')

def test_ClientLogin_topackets_chunked(noconn):
	p, q = tuple(ClientLogin('a'*16384, '').topackets(noconn))
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
	            match="'SPAM' is not a valid hash function"):
		ClientLogin.frompackets([packet])

@given(text(), text())
def test_ClientLogin_forjson_jsonto(username, password):
	m = ClientLogin(username, password)
	assert ClientLogin.json_to(m.for_json()) == m

@given(text(), text())
def test_ClientLogin_forjson_jsonto_forjson(username, password):
	m = ClientLogin(username, password)
	assert ClientLogin.json_to(m.for_json()).for_json() == m.for_json()

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

@given(sampled_from(Status), integers(min_value=0, max_value=0xFFFFFFFF),
       integers(), integers(), integers(), text(), booleans())
def test_ClientLoginReply_forjson_jsonto(status, id, timeout, channels, views,
                                         chassis, encrypt):
	m = ClientLoginReply(status, Session(id), timeout, channels, views,
	                     chassis, encrypt)
	assert ClientLoginReply.json_to(m.for_json()) == m

@given(sampled_from(Status), integers(min_value=0, max_value=0xFFFFFFFF),
       integers(), integers(), integers(), text(), booleans())
def test_ClientLoginReply_forjson_jsonto_fromjson(status, id, timeout,
                                                  channels, views, chassis,
                                                  encrypt):
	m = ClientLoginReply(status, Session(id), timeout, channels, views,
	                     chassis, encrypt)
	assert ClientLoginReply.json_to(m.for_json()).for_json() == m.for_json()

def test_ControlFilter_accept():
	chunks = [b'\xFF\x01\x00\x00\x57\x00\x00\x00\x00\x00',
	          b'\x00\x00\x00\x00\xe9\x03\x96\x00\x00\x00'
	          b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	          b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	          b'"ExtraChannel" : 0, "Ret" : 100, '
	          b'"SessionID" : "0x00000057" }\x0A\x00']
	replies = ClientLogin.replies(0)
	m, = replies.accept(Packet.load(_ChunkReader(chunks)))
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
	m, = replies.accept(q)
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

def test_ClientLogout_topackets(noconn):
	p, = ClientLogout('admin', noconn.session).topackets(noconn)
	assert p.encode() == (b'\xFF\x01\x00\x00\x57\x00\x00\x00\x00\x00'
	                      b'\x00\x00\x00\x00\xEA\x03\x2E\x00\x00\x00'
	                      b'{"Name": "admin", "SessionID": "0x00000057"}'
	                      b'\x0A\x00')

@given(text(), integers(min_value=0, max_value=0xFFFFFFFF))
def test_ClientLogout_forjson_jsonto(username, id):
	m = ClientLogout(username, Session(id))
	assert ClientLogout.json_to(m.for_json()) == m

@given(text(), integers(min_value=0, max_value=0xFFFFFFFF))
def test_ClientLogout_forjson_jsonto_forjson(username, id):
	m = ClientLogout(username, Session(id))
	assert ClientLogout.json_to(m.for_json()).for_json() == m.for_json()

def test_ClientLogoutReply_accept():
	data = (b'\xFF\x01\x00\x00\x57\x00\x00\x00\x00\x00'
	        b'\x00\x00\x00\x00\xeb\x03\x3A\x00\x00\x00'
	        b'{ "Name" : "", "Ret" : 100, '
	        b'"SessionID" : "0x00000057" }\x0A\x00')
	replies = ClientLogout.replies(0)
	m, = replies.accept(Packet.decode(data))
	assert (m.username == "" and m.status == Status(100) and  # pylint: disable=no-value-for-parameter
	        m.session == Session(0x57))

@given(sampled_from(Status), text(),
       integers(min_value=0, max_value=0xFFFFFFFF))
def test_ClientLogoutReply_forjson_jsonto(status, username, id):
	m = ClientLogoutReply(status, username, Session(id))
	assert ClientLogoutReply.json_to(m.for_json()) == m

@given(sampled_from(Status), text(),
       integers(min_value=0, max_value=0xFFFFFFFF))
def test_ClientLogoutReply_forjson_jsonto_forjson(status, username, id):
	m = ClientLogoutReply(status, username, Session(id))
	assert (ClientLogoutReply.json_to(m.for_json()).for_json() ==
	        m.for_json())

def test_Connection_logout(noconn, rfile, wfile, capsys):
	session = noconn.session

	noconn.number = 2
	p, = (ClientLogoutReply(Status.OK, 'admin', session)
	     .topackets(noconn))
	p.dump(rfile)
	noconn.number = 0
	p, = (ClientLogoutReply(Status.OK, 'admin', session)
	     .topackets(noconn))
	p.dump(rfile)
	noconn.number = 0
	noconn.username = 'admin'

	rfile.seek(0); noconn.logout(); wfile.seek(0)
	m = ClientLogout.frompackets([Packet.load(wfile)])
	assert m == ClientLogout('admin', session)
	out1, out2 = capsys.readouterr().out.split('\n')
	assert out1.startswith('unrecognized packet: ') and out2 == ''

def test_Connection_login(conn, rfile, wfile):
	session, conn.session = conn.session, Session(0x57)
	p, = (ClientLoginReply(Status.OK, Session(0x57),
	                       21, 4, 0, 'HVR', False)
	     .topackets(conn))
	p.dump(rfile); conn.number -= 1
	conn.session = session

	rfile.seek(0)
	conn.connect(('example.com', conn.PORT),
	             'admin', passhash='abc', service='def')
	wfile.seek(0)
	m = ClientLogin.frompackets([Packet.load(wfile)])

def test_Connection_login_invalid(conn, rfile, wfile):
	session, conn.session = conn.session, Session(0x57)
	p, = (ClientLoginReply(Status.ERROR, Session(0x57),
	                       21, 4, 0, 'HVR', False)
	     .topackets(conn))
	p.dump(rfile); conn.number -= 1
	conn.session = session

	rfile.seek(0)
	with raises(DVRIPRequestError, match='Unknown error'):
		try:
			conn.connect(('example.com', conn.PORT),
			             'admin', passhash='abc', service='def')
		except DVRIPRequestError as e:
			assert e.code == Status.ERROR.code
			raise
