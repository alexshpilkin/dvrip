from hashlib import md5
from inspect import currentframe
from io      import BytesIO, RawIOBase
from json    import dumps, load
from string  import ascii_lowercase, ascii_uppercase, digits, hexdigits
from struct  import Struct
from sys     import intern


def init(type, obj=None):
	frame = currentframe().f_back
	for attr in type.__slots__:
		setattr(obj, attr, frame.f_locals[attr])

def pun(attrs):
	frame = currentframe().f_back
	return {attr: frame.f_locals[attr] for attr in attrs}

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

MD5MAGIC = (digits + ascii_uppercase + ascii_lowercase).encode('ascii')
def md5crypt(password):
	mdfive = md5(bytes(password)).digest()
	return bytes(MD5MAGIC[(a+b) % len(MD5MAGIC)]
	             for a, b in zip(mdfive[0::2], mdfive[1::2]))[:8]

SESSION = '0x{:08X}'


class mirrorproperty:
	__slots__ = ('attr',)
	def __init__(self, attr):
		init(mirrorproperty, self)
	def __get__(self, obj, type=None):
		return getattr(obj, self.attr)
	def __set__(self, obj, value):
		return setattr(obj, self.attr, value)
	def __delete__(self, obj):
		return delattr(obj, self.attr)

class ChunkReader(RawIOBase):
	def __init__(self, chunks):
		self.chunks = list(chunks)
		self.chunks.reverse()
	def readable(self):
		return True
	def readinto(self, buffer):
		if not self.chunks:
			return 0
		chunk = self.chunks[-1]
		assert chunk
		buffer[:len(chunk)] = chunk[:len(buffer)]
		if len(chunk) > len(buffer):
			self.chunks[-1] = chunk[len(buffer):]
		else:
			self.chunks.pop()
		return len(chunk)


class DVRIPError(OSError):
	pass

def checkbool(json, description):
	if not isinstance(json, bool):
		raise DVRIPError('not a boolean in {}'.format(description))
	return json

def checkint(json, description):
	if not isinstance(json, int):
		raise DVRIPError('not an integer in {}'.format(description))
	return json

def checkstr(json, description):
	if not isinstance(json, str):
		raise DVRIPError('not a string in {}'.format(description))
	return json

def checkdict(json, description):
	if not isinstance(json, dict):
		raise DVRIPError('not a dictionary in {}'.format(description))
	return json

def checkempty(json, description):
	assert isinstance(json, dict)
	if json:
		raise DVRIPError('extra keys in {}'.format(description))

def popkey(json, key, description):
	assert isinstance(json, dict)
	value = json.pop(key, Ellipsis)
	if value is Ellipsis:
		raise DVRIPError('{} missing'.format(description))
	return value

def popint(json, key, description):
	return checkint(popkey(json, key, description), description)

def popstr(json, key, description):
	return checkstr(popkey(json, key, description), description)

def pophex(json, key, description):
	value = popstr(json, key, description)
	if value[:2] != '0x' or not all(c in hexdigits for c in value[2:]):
		raise DVRIPError('invalid hex string in {}'.format(description))
	return int(value[2:], 16)


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

		init(Packet, self)

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
		_write(fp, struct.pack(self.MAGIC, self.VERSION, self.session,
		                       self.number, self._fragment0,
		                       self._fragment1, self.type,
		                       len(payload)))
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


class ControlMessage(object):
	__slots__ = ()

	def topackets(self, session):
		chunks   = self.chunks()
		length   = len(chunks)
		sequence = session.sequence()
		if length == 1:
			chunk = next(iter(chunks))
			yield sequence.packet(self.type, chunk, fragments=0,
			                      fragment=0)
		else:
			for i, chunk in enumerate(chunks):
				yield sequence.packet(self.type, chunk,
				                      fragments=length,
				                      fragment=i)

	def chunks(self):
		size = Packet.MAXLEN
		json = dumps(self.for_json()).encode('ascii') + b'\x0A\x00'
		return [json[i:i+size] for i in range(0, len(json), size)]

	@classmethod
	def frompackets(cls, packets):
		packets = list(packets)
		return (packets[0].number,
		        cls.fromchunks(p.payload for p in packets if p.payload))

	@classmethod
	def fromchunks(cls, chunks):
		chunks = list(chunks)
		if not chunks:
			raise DVRIPError('no data in DVRIP packet')
		chunks[-1] = chunks[-1].rstrip(b'\x00\\')
		return cls.json_to(load(ChunkReader(chunks), encoding='latin-1'))


class ControlAcceptor(object):
	__slots__ = ('cls', 'number', 'count', 'limit', 'packets')

	def __init__(self, cls):
		number  = None
		count   = 0
		limit   = 0
		packets = None
		init(ControlAcceptor, self)

	def accept(self, packet):
		# FIXME No idea if this interpretation of sequence
		# numbers is correct.

		if packet.type != self.cls.type:
			return None
		if self.number is None:
			self.number  = packet.number
			self.limit   = max(packet.fragments, 1)
			self.packets = [None] * self.limit
		if packet.number != self.number:
			return None
		if max(packet.fragments, 1) != self.limit:
			raise DVRIPError('conflicting fragment counts')
		if packet.fragment >= self.limit:
			raise DVRIPError('invalid fragment number')
		if self.packets[packet.fragment] is not None:
			raise DVRIPError('overlapping fragments')

		assert self.count < self.limit
		self.packets[packet.fragment] = packet
		self.count += 1
		if self.count == self.limit:
			return (self.cls.frompackets(self.packets),)
		else:
			return ()


class ClientLogin(ControlMessage):
	type = 1000

	__slots__ = ('username', 'password', 'service')
	def __init__(self, username, password, service='DVRIP-Web'):
		init(ClientLogin, self)

	@classmethod
	def acceptor(self):
		return ControlAcceptor(ClientLoginReply)

	def for_json(self):
		return {'LoginType':   self.service,
		        'UserName':    self.username,
		        'PassWord':    md5crypt(self.password.encode('utf-8'))
		                               .decode('ascii'),
		        'EncryptType': 'MD5'}


class ClientLoginReply(ControlMessage):
	type = 1001

	__slots__ = ('result', 'session', 'timeout', 'channels', 'views',
	             'chassis', 'aes')

	def __init__(self, result, session, timeout, channels, views, chassis,
	             aes):
		init(ClientLoginReply, self)

	@classmethod
	def json_to(cls, json):
		checkdict(json, 'client login reply')
		result   = popint(json, 'Ret',           'result code')
		session  = pophex(json, 'SessionID',     'session number')
		timeout  = popint(json, 'AliveInterval', 'timeout value')
		channels = popint(json, 'ChannelNum',    'channel count')
		views    = popint(json, 'ExtraChannel',  'view count')
		chassis  = popstr(json, 'DeviceType ',   'chassis type')
		aes      = checkbool(json.pop('DataUseAES', False), 'AES flag')
		checkempty(json, 'client login reply')

		return cls(**pun(ClientLoginReply.__slots__))


class ClientLogout(ControlMessage):
	type = 1002

	# FIXME 'username' unused?
	__slots__ = ('username', 'session')

	def __init__(self, username, session):
		init(ClientLogout, self)

	@classmethod
	def acceptor(self):
		return ControlAcceptor(ClientLogoutReply)

	def for_json(self):
		return {'Name':      self.username,
		        'SessionID': SESSION.format(self.session)}


class ClientLogoutReply(ControlMessage):
	type = 1003

	# FIXME 'username' unused?
	__slots__ = ('result', 'username', 'session')

	def __init__(self, result, username, session):
		init(ClientLogoutReply, self)

	@classmethod
	def json_to(cls, json):
		checkdict(json, 'client logout reply')
		result   = popint(json, 'Ret',       'result code')
		username = popstr(json, 'Name',      'username')
		session  = pophex(json, 'SessionID', 'session number')
		checkempty(json, 'client logout reply')

		return cls(**pun(ClientLogoutReply.__slots__))
