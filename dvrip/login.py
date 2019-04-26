from hashlib  import md5
from string   import ascii_lowercase, ascii_uppercase, digits
from .control import ControlMessage, ControlFilter, Status, Session
from .utils   import (checkbool as _checkbool, checkdict as _checkdict,
                      checkempty as _checkempty, init as _init,
                      popint as _popint, popkey as _popkey, popstr as _popstr,
                      pun as _pun)

__all__ = ('md5crypt', 'ClientLogin', 'ClientLoginReply', 'ClientLogout',
           'ClientLogoutReply')


_MD5MAGIC = (digits + ascii_uppercase + ascii_lowercase).encode('ascii')

def md5crypt(password):
	mdfive = md5(bytes(password)).digest()
	return bytes(_MD5MAGIC[(a+b) % len(_MD5MAGIC)]
	             for a, b in zip(mdfive[0::2], mdfive[1::2]))[:8]


class ClientLogin(ControlMessage):
	type = 1000

	__slots__ = ('username', 'password', 'service')

	def __init__(self, username, password, service='DVRIP-Web'):  # pylint: disable=unused-argument
		_init(ClientLogin, self)

	@classmethod
	def replies(cls):
		return ControlFilter(ClientLoginReply)

	def for_json(self):
		return {
			'LoginType':   self.service,
			'UserName':    self.username,
			'PassWord':    md5crypt(self.password.encode('utf-8'))
			                       .decode('ascii'),
			'EncryptType': 'MD5'
		}


class ClientLoginReply(ControlMessage):
	type = 1001

	__slots__ = ('status', 'session', 'timeout', 'channels', 'views',
	             'chassis', 'aes')

	def __init__(self, status, session, timeout,  # pylint: disable=unused-argument,too-many-arguments
	             channels, views, chassis, aes):  # pylint: disable=unused-argument,too-many-arguments
		_init(ClientLoginReply, self)

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
		aes      = _checkbool(json.pop('DataUseAES', False), 'AES flag')
		_checkempty(json, 'client login reply')

		return cls(**_pun(ClientLoginReply.__slots__))


class ClientLogout(ControlMessage):
	type = 1002

	# FIXME 'username' unused?
	__slots__ = ('username', 'session')

	def __init__(self, username, session):  # pylint: disable=unused-argument
		_init(ClientLogout, self)

	@classmethod
	def replies(cls):
		return ControlFilter(ClientLogoutReply)

	def for_json(self):
		return {
			'Name':      self.username,
			'SessionID': self.session.for_json()
		}


class ClientLogoutReply(ControlMessage):
	type = 1003

	# FIXME 'username' unused?
	__slots__ = ('status', 'username', 'session')

	def __init__(self, status, username, session):  # pylint: disable=unused-argument
		_init(ClientLogoutReply, self)

	@classmethod
	def json_to(cls, json):
		# pylint: disable=unused-variable

		_checkdict(json, 'client logout reply')
		status   = Status.json_to(_popint(json, 'Ret', 'status code'))
		username = _popstr(json, 'Name',      'username')
		session  = Session.json_to(_popstr(json, 'SessionID', 'session ID'))
		_checkempty(json, 'client logout reply')

		return cls(**_pun(ClientLogoutReply.__slots__))
