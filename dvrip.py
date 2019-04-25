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

	def pack_into(self, buffer, offset=0):
		assert self.session is not None and self.number is not None

		struct = self.__STRUCT
		struct.pack_into(buffer, offset, self.MAGIC, self.VERSION,
		                 self.session, self.number)
		return memoryview(buffer)[offset+struct.size:]

	def pack(self):
		buf = bytearray(self.size)
		self.pack_into(buf)
		return buf


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

	def pack_into(self, buffer, offset=0):
		assert (self.fragment is not None and
		        self.fragments is not None and
		        self.type is not None)
		assert self.fragments != 1
		assert (self.fragment < self.fragments or
		        self.fragment == self.fragments == 0)

		buffer = super().pack_into(buffer, offset)
		struct = self.__STRUCT
		struct.pack_into(buffer, 0, self.fragments, self.fragment,
		                 self.type, self.length)
		return buffer[struct.size:]


class ControlPacket(AbstractControlPacket):
	__slots__ = ('payload',)
	def __init__(self, payload=None, *args, other=None, **named):
		super().__init__(*args, other=other, **named)

		if isinstance(other, ControlPacket):
			assert payload is None
			payload = other.payload
		self.payload = payload

	@property
	def length(self):
		return len(self.payload)

	def pack_into(self, buffer, offset=0):
		buffer  = super().pack_into(buffer, offset)
		payload = self.payload
		buffer[:len(payload)] = payload
		return buffer[len(payload):]
