from io     import BytesIO
from pytest import raises

from dvrip import *

def test_md5crypt_empty():
	assert md5crypt(b'') == b'tlJwpbo6'

def test_md5crypt_tluafed():
	assert md5crypt(b'tluafed') == b'OxhlwSG8'

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

class MockSequence(object):
	def __init__(self, session, number):
		self.session = session
		self.number  = number

	def packet(self, *args, **named):
		packet = Packet(self.session, self.number, *args, **named)
		return packet

class MockSession(object):
	def __init__(self, session=0, number=0):
		self.session = session
		self.number  = number

	def sequence(self):
		s = MockSequence(self.session, self.number)
		self.number += 1
		return s

def test_ClientLogin_topackets():
	p, = tuple(ClientLogin('admin', '').topackets(MockSession()))
	assert (p.encode() == b'\xFF\x01\x00\x00\x00\x00\x00\x00\x00\x00'
	                      b'\x00\x00\x00\x00\xe8\x03\x5F\x00\x00\x00'
	                      b'{"LoginType": "DVRIP-Web", '
	                      b'"UserName": "admin", '
	                      b'"PassWord": "tlJwpbo6", '
	                      b'"EncryptType": "MD5"}'
	                      b'\x0A\x00')

def test_ClientLogin_topackets_chunked():
	p, q = tuple(ClientLogin('a'*16384, '').topackets(MockSession()))
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
