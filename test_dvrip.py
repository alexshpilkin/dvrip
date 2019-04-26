from io     import BytesIO
from pytest import raises

from dvrip import *

def test_md5crypt_empty():
	assert md5crypt(b'') == b'tlJwpbo6'

def test_md5crypt_tluafed():
	assert md5crypt(b'tluafed') == b'OxhlwSG8'

def test_checkbool_invalid():
	with raises(DVRIPError, match='not a boolean in test'):
		checkbool(None, 'test')

def test_checkint_invalid():
	with raises(DVRIPError, match='not an integer in test'):
		checkint(None, 'test')

def test_checkstr_invalid():
	with raises(DVRIPError, match='not a string in test'):
		checkstr(None, 'test')

def test_checkdict_invalid():
	with raises(DVRIPError, match='not a dictionary in test'):
		checkdict(None, 'test')

def test_checkempty_invalid():
	with raises(DVRIPError, match='extra keys in test'):
		checkempty({'spam': 'sausages'}, 'test')

def test_popkey_invalid():
	with raises(DVRIPError, match='test missing'):
		popkey({'spam': 'sausages'}, 'ham', 'test')

def test_mirrorproperty():
	class Foo:
		y = mirrorproperty('x')
	foo = Foo()
	foo.y = 'hello'
	assert foo.x == 'hello'
	del foo.y
	assert getattr(foo, 'x', None) is None
	foo.x = 'goodbye'
	assert foo.y == 'goodbye'

def test_ChunkReader():
	r = ChunkReader([b'hel', b'lo'])
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
	with raises(DVRIPError, match='invalid DVRIP magic'):
		Packet.decode(bytes.fromhex('fe010000cdab0000fade0000'
		                            '123456780500000068656c6c6f'))
	with raises(DVRIPError, match='unknown DVRIP version'):
		Packet.decode(bytes.fromhex('ff020000cdab0000fade0000'
		                            '123456780500000068656c6c6f'))
	with raises(DVRIPError, match='DVRIP packet too long'):
		Packet.decode(bytes.fromhex('ff010000cdab0000fade0000'
		                            '123456780140000068656c6c6f'))

def test_Status_bool():
	assert Status(100)
	assert not Status(101)

def test_Status_for_json():
	assert Status(100).for_json() == 100
	assert Status(101).for_json() == 101

def test_Status_json_to():
	assert Status.json_to(100) == Status(100)
	with raises(DVRIPError, match="'SPAM' is not a valid status code"):
		Status.json_to('SPAM')

def test_Status_repr():
	assert repr(Status.OK) == 'Status(100)'
	assert repr(Status.ERROR) == 'Status(101)'

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
	with raises(DVRIPError, match="'SPAM' is not a valid session ID"):
		Session.json_to('SPAM')
	with raises(DVRIPError, match="'0xSPAM' is not a valid session ID"):
		Session.json_to('0xSPAM')
	with raises(DVRIPError, match="'0x59AE' is not a valid session ID"):
		Session.json_to('0x59AE')

class MockSequence(object):
	def __init__(self, session, number):
		self.session = session
		self.number  = number

	def packet(self, *args, **named):
		packet = Packet(self.session.id, self.number, *args, **named)
		return packet

class MockConnection(object):
	def __init__(self, session=Session(0), number=0):
		self.session = session
		self.number  = number

	def sequence(self):
		s = MockSequence(self.session, self.number)
		self.number += 1
		return s

def test_ClientLogin_topackets():
	p, = tuple(ClientLogin('admin', '').topackets(MockConnection()))
	assert (p.encode() == b'\xFF\x01\x00\x00\x00\x00\x00\x00\x00\x00'
	                      b'\x00\x00\x00\x00\xe8\x03\x5F\x00\x00\x00'
	                      b'{"LoginType": "DVRIP-Web", '
	                      b'"UserName": "admin", '
	                      b'"PassWord": "tlJwpbo6", '
	                      b'"EncryptType": "MD5"}'
	                      b'\x0A\x00')

def test_ClientLogin_topackets_chunked():
	p, q = tuple(ClientLogin('a'*16384, '').topackets(MockConnection()))
	assert (p.encode() == b'\xFF\x01\x00\x00\x00\x00\x00\x00\x00\x00'
	                      b'\x00\x00\x02\x00\xe8\x03\x00\x40\x00\x00'
	                      b'{"LoginType": "DVRIP-Web", '
	                      b'"UserName": "' + b'a' * (16384 - 40))
	assert (q.encode() == b'\xFF\x01\x00\x00\x00\x00\x00\x00\x00\x00'
	                      b'\x00\x00\x02\x01\xe8\x03\x5A\x00\x00\x00' +
	                      b'a' * 40 + b'", '
	                      b'"PassWord": "tlJwpbo6", '
	                      b'"EncryptType": "MD5"}'
	                      b'\x0A\x00')

def test_ClientLoginReply_frompackets():
	chunks = [b'\xFF\x01\x00\x00\x3F\x00\x00\x00\x00\x00',
	          b'\x00\x00\x00\x00\xe9\x03\x96\x00\x00\x00'
	          b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	          b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	          b'"ExtraChannel" : 0, "Ret" : 100, '
	          b'"SessionID" : "0x0000003F" }\x0A\x00']
	n, m = ClientLoginReply.frompackets([Packet.load(ChunkReader(chunks))])
	assert n == 0
	assert (m.timeout == 21 and m.channels == 4 and m.aes == False and
	        m.views == 0 and m.status == Status(100) and
	        m.session == Session(0x3F))

def test_ClientLoginReply_fromchunks_empty():
	with raises(DVRIPError, match='no data in DVRIP packet'):
		ClientLoginReply.fromchunks([])

def test_ControlFilter_accept():
	chunks = [b'\xFF\x01\x00\x00\x3F\x00\x00\x00\x00\x00',
	          b'\x00\x00\x00\x00\xe9\x03\x96\x00\x00\x00'
	          b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	          b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	          b'"ExtraChannel" : 0, "Ret" : 100, '
	          b'"SessionID" : "0x0000003F" }\x0A\x00']
	replies = ClientLogin.replies()
	(n, m), = replies.accept(Packet.load(ChunkReader(chunks)))
	assert n == 0
	assert (m.timeout == 21 and m.channels == 4 and m.aes == False and
	        m.views == 0 and m.status == Status(100) and
	        m.session == Session(0x3F))

def test_ControlFilter_accept_chunked():
	p = Packet(0x3F, 0, 1001,
	           b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	           b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	           fragments=2, fragment=0)
	q = Packet(0x3F, 0, 1001,
	           b'"ExtraChannel" : 0, "Ret" : 100, '
	           b'"SessionID" : "0x0000003F" }\x0A\x00',
	           fragments=2, fragment=1)

	replies = ClientLogin.replies()
	() = replies.accept(p)
	(n, m), = replies.accept(q)
	assert n == 0
	assert (m.timeout == 21 and m.channels == 4 and m.aes == False and
	        m.views == 0 and m.status == Status(100) and
	        m.session == Session(0x3F))

def test_ControlFilter_accept_wrong_type():
	p = Packet(0x3F, 0, 1002,
	           b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	           b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	           fragments=2, fragment=0)

	replies = ClientLogin.replies()
	assert replies.accept(p) is None

def test_ControlFilter_accept_wrong_number():
	p = Packet(0x3F, 0, 1001,
	           b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	           b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	           fragments=2, fragment=0)
	q = Packet(0x3F, 57, 1001,
	           b'"ExtraChannel" : 0, "Ret" : 100, '
	           b'"SessionID" : "0x0000003F" }\x0A\x00',
	           fragments=2, fragment=1)

	replies = ClientLogin.replies()
	() = replies.accept(p)
	assert replies.accept(q) is None

def test_ControlFilter_accept_invalid_fragments():
	p = Packet(0x3F, 0, 1001,
	           b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	           b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	           fragments=2, fragment=0)
	q = Packet(0x3F, 0, 1001,
	           b'"ExtraChannel" : 0, "Ret" : 100, '
	           b'"SessionID" : "0x0000003F" }\x0A\x00',
	           fragments=3, fragment=1)

	replies = ClientLogin.replies()
	() = replies.accept(p)
	with raises(DVRIPError, match='conflicting fragment counts'):
		replies.accept(q)

def test_ControlFilter_accept_invalid_overrun():
	p = Packet(0x3F, 0, 1001,
	           b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	           b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	           fragments=2, fragment=4)

	replies = ClientLogin.replies()
	with raises(DVRIPError, match='invalid fragment number'):
		replies.accept(p)

def test_ControlFilter_accept_invalid_overlap():
	p = Packet(0x3F, 0, 1001,
	           b'{ "AliveInterval" : 21, "ChannelNum" : 4, '
	           b'"DataUseAES" : false, "DeviceType " : "HVR", ',
	           fragments=2, fragment=0)
	q = Packet(0x3F, 0, 1001,
	           b'"ExtraChannel" : 0, "Ret" : 100, '
	           b'"SessionID" : "0x0000003F" }\x0A\x00',
	           fragments=2, fragment=0)

	replies = ClientLogin.replies()
	() = replies.accept(p)
	with raises(DVRIPError, match='overlapping fragments'):
		replies.accept(q)

def test_ClientLogout_topackets():
	p, = (ClientLogout('admin', Session(0x5F))
	     .topackets(MockConnection(session=Session(0x5F))))
	assert p.encode() == (b'\xFF\x01\x00\x00\x5F\x00\x00\x00\x00\x00'
	                      b'\x00\x00\x00\x00\xEA\x03\x2E\x00\x00\x00'
	                      b'{"Name": "admin", "SessionID": "0x0000005F"}'
	                      b'\x0A\x00')

def test_ClientLogoutReply_accept():
	data = (b'\xFF\x01\x00\x00\x5A\x00\x00\x00\x00\x00'
	        b'\x00\x00\x00\x00\xeb\x03\x3A\x00\x00\x00'
	        b'{ "Name" : "", "Ret" : 100, '
	        b'"SessionID" : "0x00000059" }\x0A\x00')
	replies = ClientLogout.replies()
	(n, m), = replies.accept(Packet.decode(data))
	assert n == 0
	assert (m.username == "" and m.status == Status(100) and
	        m.session == Session(0x59))
