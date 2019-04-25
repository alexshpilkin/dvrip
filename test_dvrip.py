from dvrip import *
from io    import BytesIO

def test_md5crypt_empty():
	assert md5crypt(b'') == b'tlJwpbo6'

def test_md5crypt_tluafed():
	assert md5crypt(b'tluafed') == b'OxhlwSG8'

def test_AbstractPacket_encode():
	p = AbstractPacket(0xdefa, 0xabcd)
	assert p.encode().hex() == 'ff010000cdab0000fade0000'
	assert p.size == len(p.encode())

def test_AbstractPacket_dump():
	b = BytesIO()
	p = AbstractPacket(0xdefa, 0xabcd)
	p.dump(b)
	assert p.encode() == b.getvalue()

def test_UnknownControlPacket_encode():
	p = UnknownControlPacket(b'hello', 0x7856, 0x34, 0x12, 0xdefa, 0xabcd)
	assert p.encode().hex() == ('ff010000cdab0000fade0000'
	                            '123456780500000068656c6c6f')
	assert p.size == len(p.encode())

def test_UnknownControlPacket_dump():
	b = BytesIO()
	p = UnknownControlPacket(b'hello', 0x7856, 0x34, 0x12, 0xdefa, 0xabcd)
	p.dump(b)
	assert p.encode() == b.getvalue()
