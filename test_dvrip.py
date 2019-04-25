from dvrip import *
from io    import BytesIO

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
	assert p.pack().hex() == ('ff010000cdab0000fade0000'
	                          '123456780500000068656c6c6f')
	assert p.size == len(p.pack())
