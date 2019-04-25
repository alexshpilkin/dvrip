from hashlib import md5
from string  import ascii_lowercase, ascii_uppercase, digits
from struct  import Struct
from sys     import intern


MD5MAGIC = (digits + ascii_uppercase + ascii_lowercase).encode('ascii')
def md5crypt(password):
	mdfive = md5(bytes(password)).digest()
	return bytes(MD5MAGIC[(a+b) % len(MD5MAGIC)]
	             for a, b in zip(mdfive[0::2], mdfive[1::2]))[:8]


class mirrorproperty:
	__slots__ = ('attr',)
	def __init__(self, attr):
		self.attr = attr
	def __get__(self, obj, type=None):
		return getattr(obj, self.attr)
	def __set__(self, obj, value):
		return setattr(obj, self.attr, value)
	def __delete__(self, obj):
		return delattr(obj, self.attr)


class Packet(object):
	MAGIC    = 0xFF
	VERSION  = 0x01
	__STRUCT = Struct('<BBxxIIBBHI')

	__slots__ = ('session', 'number', '_fragment0', '_fragment1', 'type',
	             'payload')
	def __init__(self, session=None, number=None, type=None, payload=None,
	             *, fragments=None, channel=None, fragment=None, end=None):
		super().__init__()

		assert (fragments is None and fragment is None or
		        channel   is None and end      is None)
		_fragment0 = fragments if fragments is not None else channel
		_fragment1 = fragment  if fragment  is not None else end

		self.session    = session
		self.number     = number
		self._fragment0 = _fragment0
		self._fragment1 = _fragment1
		self.type       = type
		self.payload    = payload

	fragments = mirrorproperty('_fragment0')
	channel   = mirrorproperty('_fragment0')
	fragment  = mirrorproperty('_fragment1')
	end       = mirrorproperty('_fragment1')

	@property
	def length(self):
		return len(self.payload)

	@property
	def size(self):
		return self.__STRUCT.size + self.length

	def pack_into(self, buffer, offset=0):
		assert (self.session is not None and
		        self.number is not None and
		        self._fragment0 is not None and
		        self._fragment1 is not None and
		        self.type is not None)
		# FIXME Only for control packets
		#assert self.fragments != 1
		#assert (self.fragment < self.fragments or
		#        self.fragment == self.fragments == 0)

		struct  = self.__STRUCT
		payload = self.payload
		buffer  = memoryview(buffer)[offset:]
		struct.pack_into(buffer, offset, self.MAGIC, self.VERSION,
		                 self.session, self.number, self._fragment0,
		                 self._fragment1, self.type, self.length)
		buffer = buffer[struct.size:]
		buffer[:len(payload)] = payload

	def pack(self):
		buf = bytearray(self.size)
		self.pack_into(buf)
		return buf

