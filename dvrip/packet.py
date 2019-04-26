from io      import BytesIO
from struct  import Struct
from .errors import DVRIPError
from .utils  import init as _init

__all__ = ('Packet',)


class _mirrorproperty:
	__slots__ = ('attr',)
	def __init__(self, attr):
		_init(_mirrorproperty, self)
	def __get__(self, obj, type=None):
		return getattr(obj, self.attr)
	def __set__(self, obj, value):
		return setattr(obj, self.attr, value)
	def __delete__(self, obj):
		return delattr(obj, self.attr)


def _read(fp, length):
	data = bytearray(length)
	buf  = memoryview(data)
	while buf:
		buf = buf[fp.readinto(buf):]
	return data


def _write(fp, data):
	buf = memoryview(data)
	while buf:
		buf = buf[fp.write(buf):]


class Packet(object):
	MAGIC    = 0xFF
	VERSION  = 0x01
	MAXLEN   = 16384
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

		_init(Packet, self)

	fragments = _mirrorproperty('_fragment0')
	channel   = _mirrorproperty('_fragment0')
	fragment  = _mirrorproperty('_fragment1')
	end       = _mirrorproperty('_fragment1')

	@property
	def length(self):
		return len(self.payload)

	@property
	def size(self):
		return self.__STRUCT.size + self.length

	def dump(self, fp):
		assert (self.session is not None and
		        self.number is not None and
		        self._fragment0 is not None and
		        self._fragment1 is not None and
		        self.type is not None)
		# FIXME Only for control packets
		#assert self.fragments != 1
		#assert (self.fragment < self.fragments or
		#        self.fragment == self.fragments == 0)
		assert len(self.payload) <= self.MAXLEN

		struct  = self.__STRUCT
		payload = self.payload
		_write(fp, struct.pack(self.MAGIC, self.VERSION,
		                       self.session, self.number,
		                       self._fragment0, self._fragment1,
		                       self.type, len(payload)))
		_write(fp, payload)

	def encode(self):
		buf = BytesIO()
		self.dump(buf)
		return buf.getvalue()

	@classmethod
	def load(cls, fp):
		struct = cls.__STRUCT
		(magic, version, session, number, _fragment0, _fragment1,
		 type, length) = \
		 	struct.unpack(_read(fp, struct.size))
		if magic != cls.MAGIC:
			raise DVRIPError('invalid DVRIP magic')
		if version != cls.VERSION:
			raise DVRIPError('unknown DVRIP version')
		if length > cls.MAXLEN:
			raise DVRIPError('DVRIP packet too long')
		payload = _read(fp, length)
		return cls(session=session, number=number,
		           fragments=_fragment0, fragment=_fragment1,
		           type=type, payload=payload)

	@classmethod
	def decode(cls, buffer):
		buf = BytesIO(buffer)
		packet = cls.load(buf)
		assert buf.tell() == len(buffer)
		return packet
