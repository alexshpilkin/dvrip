from enum     import Enum, unique
from hashlib  import md5 as MD5
from string   import ascii_lowercase, ascii_uppercase, digits
from .message import ControlMessage, ControlFilter, Status, Session
from .errors  import DVRIPDecodeError
from .typing  import Object, for_json, json_to, member, optionalmember

__all__ = ('xmmd5', 'Hash', 'ClientLogin', 'ClientLoginReply', 'ClientLogout',
           'ClientLogoutReply')


_XMMD5MAGIC = (digits + ascii_uppercase + ascii_lowercase)

def xmmd5(password):
	md5 = MD5(password.encode('utf-8')).digest()
	return ''.join(_XMMD5MAGIC[(a+b) % len(_XMMD5MAGIC)]
	               for a, b in zip(md5[0::2], md5[1::2]))[:8]


@unique
class Hash(Enum):
	__slots__ = ('id', 'func')

	def __new__(cls, id, func):  # pylint: disable=redefined-builtin
		self = object.__new__(cls)
		self._value_ = id  # pylint: disable=protected-access
		self.id      = id
		self.func    = func
		return self

	def __repr__(self):
		return '{}.{}'.format(type(self).__qualname__, self._name_)  # pylint: disable=no-member

	def __str__(self):
		return self.id

	def for_json(self):
		return for_json(self.id)

	@classmethod
	def json_to(cls, datum):
		try:
			return cls(json_to(str)(datum))  # pylint: disable=no-value-for-parameter
		except ValueError:
			raise DVRIPDecodeError('not a known hash function')

	XMMD5 = ('MD5', xmmd5)


class ClientLogin(Object, ControlMessage):
	type = 1000

	username: member[str]  = member('UserName')
	passhash: member[str]  = member('PassWord')
	hash:     member[Hash] = member('EncryptType')
	service:  member[str]  = member('LoginType')

	@classmethod
	def replies(cls, number):
		return ControlFilter(ClientLoginReply, number)


class ClientLoginReply(Object, ControlMessage):
	type = 1001

	status:   member[Status]       = member('Ret')
	session:  member[Session]      = member('SessionID')
	timeout:  member[int]          = member('AliveInterval')
	channels: member[int]          = member('ChannelNum')
	views:    member[int]          = member('ExtraChannel')
	chassis:  member[str]          = member('DeviceType ')
	encrypt:  optionalmember[bool] = optionalmember('DataUseAES')


class ClientLogout(Object, ControlMessage):
	type = 1002

	# FIXME 'username' unused?
	username: member[str]     = member('Name')
	session:  member[Session] = member('SessionID')

	@classmethod
	def replies(cls, number):
		return ControlFilter(ClientLogoutReply, number)


class ClientLogoutReply(Object, ControlMessage):
	type = 1003

	status:   member[Status]  = member('Ret')
	username: member[str]     = member('Name')
	session:  member[Session] = member('SessionID')
