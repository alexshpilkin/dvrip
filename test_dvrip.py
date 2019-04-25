from dvrip import *
from io    import BytesIO

def test_md5crypt_empty():
	assert md5crypt(b'') == b'tlJwpbo6'

def test_md5crypt_tluafed():
	assert md5crypt(b'tluafed') == b'OxhlwSG8'

def test_AbstractPacket_pack():
	p = AbstractPacket(0xdefa, 0xabcd)
	assert p.pack().hex() == 'ff010000cdab0000fade0000'
	assert p.size == len(p.pack())

def test_AbstractPacket_copy():
	p = AbstractPacket(0xdefa, 0xabcd)
	q = AbstractPacket(other=p)
	assert p.pack() == q.pack()

def test_ControlPacket_encode():
	p = ControlPacket(b'hello', 0x7856, 0x34, 0x12, 0xdefa, 0xabcd)
	assert p.pack().hex() == ('ff010000cdab0000fade0000'
	                          '123456780500000068656c6c6f')
	assert p.size == len(p.pack())

def test_ControlPacket_copy():
	p = ControlPacket(b'hello', 0x7856, 0x34, 0x12, 0xdefa, 0xabcd)
	q = ControlPacket(other=p)
	assert p.pack() == q.pack()
