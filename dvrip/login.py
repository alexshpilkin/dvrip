from hashlib  import md5
from string   import ascii_lowercase, ascii_uppercase, digits
from .message import ControlMessage, ControlFilter, Status, Session
from .errors  import DVRIPDecodeError
from .typing  import String, Object, member
from .utils   import (checkbool as _checkbool, checkdict as _checkdict,
                      checkempty as _checkempty, eq as _eq, init as _init,
                      popint as _popint, popkey as _popkey, popstr as _popstr,
                      pun as _pun, repr as _repr)

__all__ = ('md5crypt', 'ClientLogin', 'ClientLoginReply', 'ClientLogout',
           'ClientLogoutReply')


_MD5MAGIC = (digits + ascii_uppercase + ascii_lowercase).encode('ascii')

def md5crypt(password):
	mdfive = md5(bytes(password)).digest()
	return bytes(_MD5MAGIC[(a+b) % len(_MD5MAGIC)]
	             for a, b in zip(mdfive[0::2], mdfive[1::2]))[:8]


class ClientLogin(ControlMessage):
	type = 1000

	__slots__ = ('username', 'passhash', 'service')

	def __init__(self, username, password=None, service='DVRIP-Web',  # pylint: disable=unused-argument
	             passhash=None):                                      # pylint: disable=unused-argument
		assert password is not None or passhash is not None
		if passhash is None:
			passhash = (md5crypt(password.encode('utf-8'))
			           .decode('ascii'))
		_init(ClientLogin, self)

	__repr__ = _repr

	def __eq__(self, other):
		return _eq(ClientLogin, self, other)

	@classmethod
	def replies(cls, number):
		return ControlFilter(ClientLoginReply, number)

	def for_json(self):
		return {
			'UserName':    self.username,
			'PassWord':    self.passhash,
			'EncryptType': 'MD5',
			'LoginType':   self.service,
		}

	@classmethod
	def json_to(cls, json):
		# pylint: disable=unused-variable

		_checkdict(json, 'client login request')
		username = _popstr(json, 'UserName',    'username')
		passhash = _popstr(json, 'PassWord',    'password')
		service  = _popstr(json, 'LoginType',   'service')
		hashfunc = _popstr(json, 'EncryptType', 'hash function')
		_checkempty(json, 'client login request')

		if hashfunc != 'MD5':
			raise DVRIPDecodeError('{!r} is not a valid hash '
			                       'function'.format(hashfunc))
		return cls(**_pun(ClientLogin.__slots__))


class ClientLoginReply(ControlMessage):
	type = 1001

	__slots__ = ('status', 'session', 'timeout', 'channels', 'views',
	             'chassis', 'encrypt')

	def __init__(self, status, session, timeout,      # pylint: disable=unused-argument,too-many-arguments
	             channels, views, chassis, encrypt):  # pylint: disable=unused-argument,too-many-arguments
		_init(ClientLoginReply, self)

	__repr__ = _repr

	def __eq__(self, other):
		return _eq(ClientLoginReply, self, other)

	def for_json(self):
		return {
			'Ret':           self.status.for_json(),
			'SessionID':     self.session.for_json(),
			'AliveInterval': self.timeout,
			'ChannelNum':    self.channels,
			'ExtraChannel':  self.views,
			'DeviceType ':   self.chassis,
			'DataUseAES':    self.encrypt,
		}

	@classmethod
	def json_to(cls, json):
		# pylint: disable=unused-variable

		_checkdict(json, 'client login reply')
		status   = Status.json_to(_popint(json, 'Ret', 'status code'))
		session  = Session.json_to(_popkey(json, 'SessionID', 'session ID'))
		timeout  = _popint(json, 'AliveInterval', 'timeout value')
		channels = _popint(json, 'ChannelNum',    'channel count')
		views    = _popint(json, 'ExtraChannel',  'view count')
		chassis  = _popstr(json, 'DeviceType ',   'chassis type')
		encrypt  = _checkbool(json.pop('DataUseAES', False), 'encryption flag')
		_checkempty(json, 'client login reply')

		return cls(**_pun(ClientLoginReply.__slots__))


class ClientLogout(Object, ControlMessage):
	type = 1002

	# FIXME 'username' unused?
	username: member[String]  = member('Name')
	session:  member[Session] = member('SessionID')

	@classmethod
	def replies(cls, number):
		return ControlFilter(ClientLogoutReply, number)


class ClientLogoutReply(Object, ControlMessage):
	type = 1003

	status:   member[Status]  = member('Ret')
	username: member[String]  = member('Name')
	session:  member[Session] = member('SessionID')
