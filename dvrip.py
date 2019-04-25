from hashlib import md5
from string  import ascii_lowercase, ascii_uppercase, digits
from struct  import Struct
from sys     import intern


MD5MAGIC = (digits + ascii_uppercase + ascii_lowercase).encode('ascii')
def md5crypt(password):
	mdfive = md5(bytes(password)).digest()
	return bytes(MD5MAGIC[(a+b) % len(MD5MAGIC)]
	             for a, b in zip(mdfive[0::2], mdfive[1::2]))[:8]


class AbstractPacket(object):
	MAGIC    = 0xFF
	VERSION  = 0x01
	__STRUCT = Struct('<BBxxII')

	__slots__ = ('session', 'number')
	def __init__(self, number=None, session=None, *, other=None):
		super().__init__()

		if isinstance(other, AbstractPacket):
			assert number is None and session is None
			number  = other.number
			session = other.session
		self.session = session
		self.number  = number

	@property
	def size(self):
		return self.__STRUCT.size

	def encodeto(self, buffer, offset=0):
		struct = self.__STRUCT
		struct.pack_into(buffer, offset, self.MAGIC, self.VERSION,
		                 self.session, self.number)
		return memoryview(buffer)[offset+struct.size:]

	def encode(self):
		buf = bytearray(self.size)
		self.encodeto(buf)
		return buf

	def chunks(self):
		return (self.encode(),)

	def dump(self, fp):
		for chunk in self.chunks():
			chunk = memoryview(chunk)
			while chunk:
				chunk = chunk[fp.write(chunk):]


class AbstractControlPacket(AbstractPacket):
	__STRUCT = Struct('<BBHI')

	__slots__ = ('fragments', 'fragment', 'type', 'length')
	def __init__(self, type=None, fragment=None, fragments=None,
	             *args, other=None, **named):
		super().__init__(*args, other=other, **named)

		if isinstance(other, AbstractControlPacket):
			assert (type is None and fragment is None and
			        fragments is None)
			type      = other.type
			fragment  = other.fragment
			fragments = other.fragments
		self.fragments = fragments
		self.fragment  = fragment
		self.type      = type

	@property
	def size(self):
		return super().size + self.__STRUCT.size + self.length

	def encodeto(self, buffer, offset=0):
		buffer = super().encodeto(buffer, offset)
		struct = self.__STRUCT
		struct.pack_into(buffer, 0, self.fragments, self.fragment,
		                 self.type, self.length)
		return buffer[struct.size:]


class UnknownControlPacket(AbstractControlPacket):
	__slots__ = ('data',)
	def __init__(self, data=None, *args, other=None, **named):
		super().__init__(*args, other=other, **named)

		if isinstance(other, UnknownControlPacket):
			assert data is None
			data = other.data
		self.data = data

	@property
	def length(self):
		return len(self.data)

	def encodeto(self, buffer, offset=0):
		buffer = super().encodeto(buffer, offset)
		data   = self.data
		buffer[:len(data)] = data
		return buffer[len(data):]
