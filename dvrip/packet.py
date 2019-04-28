from io      import BytesIO
from struct  import Struct
from .errors import DVRIPDecodeError

__all__ = ('Packet',)


class _mirrorproperty:
	def __init__(self, attr):
		self.attr = attr
	def __get__(self, obj, type=None):  # pylint: disable=redefined-builtin
		return getattr(obj, self.attr)
	def __set__(self, obj, value):
		return setattr(obj, self.attr, value)
	def __delete__(self, obj):
		return delattr(obj, self.attr)


def _read(file, length):
	data = bytearray(length)
	buf  = memoryview(data)
	while buf:
		buf = buf[file.readinto(buf):]
	return data


def _write(file, data):
	buf = memoryview(data)
	while buf:
		buf = buf[file.write(buf):]


class Packet(object):
	MAGIC    = 0xFF
	VERSION  = 0x01
	MAXLEN   = 16384
	__STRUCT = Struct('<BBxxIIBBHI')

	__slots__ = ('session', 'number', '_fragment0', '_fragment1', 'type',
	             'payload')

	def __init__(self, session=None, number=None, type=None, payload=None,  # pylint: disable=redefined-builtin
	             *, fragments=None, channel=None, fragment=None, end=None):
		super().__init__()

		assert (fragments is None and fragment is None or
		        channel   is None and end      is None)
		_fragment0 = fragments if fragments is not None else channel
		_fragment1 = fragment  if fragment  is not None else end

		self.session   = session
		self.number     = number
		self._fragment0 = _fragment0
		self._fragment1 = _fragment1
		self.type       = type
		self.payload    = payload

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

	def dump(self, file):
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
		_write(file, struct.pack(self.MAGIC, self.VERSION,
		                         self.session, self.number,
		                         self._fragment0, self._fragment1,
		                         self.type, len(payload)))
		_write(file, payload)

	def encode(self):
		buf = BytesIO()
		self.dump(buf)
		return buf.getvalue()

	@classmethod
	def load(cls, file):
		struct = cls.__STRUCT
		header = struct.unpack(_read(file, struct.size))
		(magic, version, session, number,
		 _fragment0, _fragment1, type, length) = header  # pylint: disable=redefined-builtin
		if magic != cls.MAGIC:
			raise DVRIPDecodeError('invalid DVRIP magic')
		if version != cls.VERSION:
			raise DVRIPDecodeError('unknown DVRIP version')
		if length > cls.MAXLEN:
			raise DVRIPDecodeError('DVRIP packet too long')
		payload = _read(file, length)
		return cls(session=session, number=number,
		           fragments=_fragment0, fragment=_fragment1,
		           type=type, payload=payload)

	@classmethod
	def decode(cls, buffer):
		buf = BytesIO(buffer)
		packet = cls.load(buf)
		assert buf.tell() == len(buffer)
		return packet
