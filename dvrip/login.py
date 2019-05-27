from enum     import Enum, unique
from hashlib  import md5 as MD5
from string   import ascii_lowercase, ascii_uppercase, digits
from typing   import Callable, Type, TypeVar
from .message import Message, Request, Session, Status
from .errors  import DVRIPDecodeError
from .typing  import Object, fixedmember, for_json, json_to, member, \
                     optionalmember

_H = TypeVar('_H', bound='Hash')


_XMMD5MAGIC = (digits + ascii_uppercase + ascii_lowercase)

def xmmd5(password: str) -> str:
	md5 = MD5(password.encode('utf-8')).digest()
	return ''.join(_XMMD5MAGIC[(a+b) % len(_XMMD5MAGIC)]
	               for a, b in zip(md5[0::2], md5[1::2]))[:8]


@unique
class Hash(Enum):
	__slots__ = ('id', 'func')

	def __new__(cls, id: str, _func: Callable[[str], str]) -> 'Hash':  # pylint: disable=redefined-builtin
		self = object.__new__(cls)
		self._value_ = id  # pylint: disable=protected-access
		return self

	def __init__(self, id: str, func: Callable[[str], str]) -> None:  # pylint: disable=redefined-builtin
		self.id   = id
		self.func = func

	def __repr__(self) -> str:
		return '{}.{}'.format(type(self).__qualname__, self.name)

	def __str__(self) -> str:
		return self.id

	def for_json(self) -> object:
		return for_json(self.id)

	@classmethod
	def json_to(cls: Type[_H], datum: object) -> _H:
		try:
			return cls(json_to(str)(datum))  # type: ignore  # pylint: disable=no-value-for-parameter
		except ValueError:
			raise DVRIPDecodeError('not a known hash function')

	XMMD5 = ('MD5', xmmd5)


class ClientLoginReply(Object, Message):
	type = 1001

	status:    member[Status]       = member('Ret')
	session:   member[Session]      = member('SessionID')
	keepalive: member[int]          = member('AliveInterval')
	channels:  member[int]          = member('ChannelNum')
	views:     member[int]          = member('ExtraChannel')
	chassis:   member[str]          = member('DeviceType ')
	encrypt:   optionalmember[bool] = optionalmember('DataUseAES')


class ClientLogin(Object, Request[ClientLoginReply]):
	type  = 1000
	reply = ClientLoginReply

	username: member[str]  = member('UserName')
	passhash: member[str]  = member('PassWord')
	hash:     member[Hash] = member('EncryptType')
	service:  member[str]  = member('LoginType')


class ClientLogoutReply(Object, Message):
	type = 1003

	status:  member[Status]  = member('Ret')
	command: fixedmember     = fixedmember('Name', '')
	session: member[Session] = member('SessionID')


class ClientLogout(Object, Request[ClientLogoutReply]):
	type  = 1002
	reply = ClientLogoutReply

	command: fixedmember     = fixedmember('Name', '')
	session: member[Session] = member('SessionID')


class KeepAliveReply(Object, Message):
	type = 1007

	status:  member[Status]  = member('Ret')
	session: member[Session] = member('SessionID')
	command: fixedmember     = fixedmember('Name', 'KeepAlive')


class KeepAlive(Object, Request):
	type  = 1006
	reply = KeepAliveReply

	session: member[Session] = member('SessionID')
	command: fixedmember     = fixedmember('Name', 'KeepAlive')
