from abc import ABCMeta, abstractmethod
from collections import OrderedDict
from collections.abc import Mapping, Sequence
from enum import Enum, EnumMeta
from sys import intern
from typing import Any, Callable, Dict, Generic, List, MutableMapping, \
                   Optional, Tuple, TYPE_CHECKING, Type, TypeVar, Union, \
                   get_type_hints
from typing_extensions import Protocol, runtime
from typing_inspect import is_generic_type, get_origin, get_args  # type: ignore
from .errors import DVRIPDecodeError

__all__ = ('Value', 'for_json', 'json_to', 'jsontype', 'EnumValueMeta',
           'EnumValue', 'Member', 'member', 'optionalmember', 'absentmember',
           'ObjectMeta', 'Object')

T = TypeVar('T')
V = TypeVar('V', bound='Union[bool, int, str, list, Dict[str, Any], Value]')
O = TypeVar('O', bound='Object')


if TYPE_CHECKING:  # pragma: no cover
	@runtime
	class Value(Protocol):
		# pylint: disable=no-self-use,unused-argument

		def for_json(self) -> object:
			...

		@classmethod
		def json_to(cls: Type[V], datum: object) -> V:
			...

else:
	class Value(metaclass=ABCMeta):
		__slots__ = ()

		@abstractmethod
		def for_json(self) -> object:
			raise NotImplementedError  # pragma: no cover

		@classmethod
		@abstractmethod
		def json_to(cls: Type[V], datum: object) -> V:
			raise NotImplementedError  # pragma: no cover

		@classmethod
		def __subclasshook__(cls, other: Type) -> bool:
			if cls is not Value:
				return NotImplemented
			for method in ('for_json', 'json_to'):
				for base in other.__mro__:
					if method not in base.__dict__:
						continue
					if base.__dict__[method] is None:
						return NotImplemented
					break
				else:
					return NotImplemented
			return True


def for_json(obj: V.__bound__) -> object:  # pylint: disable=no-member
	try:
		return obj.for_json()
	except AttributeError:
		if isinstance(obj, (bool, int, str)):
			return obj
		if isinstance(obj, Sequence):
			return list(obj)
		if isinstance(obj, Mapping):
			return dict(obj)
		raise TypeError('not a JSON value')


def json_to(type: Type[V]) -> Callable[[object], V]:  # pylint: disable=redefined-builtin
	try:
		return type.json_to  # type: ignore
	except AttributeError:
		if is_generic_type(type):  # needs to come before 'issubclass'
			if get_origin(type) == list:
				return _json_to_list(get_args(type)[0])  # type: ignore
			if get_origin(type) == dict:
				return _json_to_dict(get_args(type)[1])  # type: ignore
		if issubclass(type, bool):  # needs to come before 'int'
			return _json_to_bool  # type: ignore
		if issubclass(type, int):
			return _json_to_int  # type: ignore
		if issubclass(type, str):
			return _json_to_str  # type: ignore
		if issubclass(type, list):
			raise TypeError('no element type specified for list')
		if issubclass(type, dict):
			raise TypeError('no value type specified for dict')
	raise TypeError('not a JSON value type')


def _json_to_bool(datum: object) -> bool:
	if not isinstance(datum, bool):
		raise DVRIPDecodeError('not a boolean')
	return bool(datum)


def _json_to_int(datum: object) -> int:
	if not isinstance(datum, int) or isinstance(datum, bool):
		raise DVRIPDecodeError('not an integer')
	return int(datum)


def _json_to_str(datum: object) -> str:
	if not isinstance(datum, str):
		raise DVRIPDecodeError('not a string')
	return str(datum)


def _json_to_list(arg: Type[V]) -> Callable[[object], List[V]]:
	_json_to = json_to(arg)
	def _json_tolist(datum: object) -> List[V]:
		if not isinstance(datum, list):
			raise DVRIPDecodeError('not an array')
		return [_json_to(item) for item in datum]
	return _json_tolist


def _json_to_dict(arg: Type[V]) -> Callable[[object], Dict[str, V]]:
	_json_to = json_to(arg)
	def _json_todict(datum: object) -> Dict[str, V]:
		if not isinstance(datum, dict):
			raise DVRIPDecodeError('not an object')
		return {_json_to_str(key): _json_to(value)
		        for key, value in datum.items()}
	return _json_todict


def jsontype(type):  # pylint: disable=redefined-builtin
	return (json_to(type), for_json)


class EnumValueMeta(EnumMeta, ABCMeta):
	pass


class EnumValue(Value, Enum, metaclass=EnumValueMeta):  # pylint: disable=abstract-method
	pass


if TYPE_CHECKING:  # pragma: no cover
	@runtime
	class Member(Generic[T], Protocol):
		# pylint: disable=no-self-use,unused-argument
		name: str

		def __set_name__(self, type: 'ObjectMeta', name: str) -> None:  # pylint: disable=redefined-builtin
			self.name = name

		def push(self,
		         push: Callable[[str, object], None],
		         value: T
		        ) -> None:
			...

		def pop(self, pop: Callable[[str], object]) -> T:
			...

else:
	class Member(Generic[T], metaclass=ABCMeta):
		__slots__ = ('name',)

		def __init__(self):
			self.name: str  # pragma: no cover

		def __set_name__(self, _type: 'ObjectMeta', name: str) -> None:
			self.name = name

		@abstractmethod
		def push(self,
			 push: Callable[[str, object], None],
			 value: T
			) -> None:
			pass

		@abstractmethod
		def pop(self, pop: Callable[[str], object]) -> T:
			raise NotImplementedError  # pragma: no cover

		@classmethod
		def __subclasshook__(cls, other: Type) -> bool:
			if cls is not Member:
				return NotImplemented
			for method in ('__set_name__', 'push', 'pop'):
				for base in other.__mro__:
					if method not in base.__dict__:
						continue
					if base.__dict__[method] is None:
						return NotImplemented
					break
				else:
					return NotImplemented
			return True


def _compose(*args: Callable[[Any], Any]) -> Callable[[Any], Any]:
	# pylint: disable=exec-used
	res = 'x'
	env = {}
	for i, fun in enumerate(reversed(args)):
		res = 'f{}({})'.format(i, res)
		env['f{}'.format(i)] = fun
	exec('def composition(x):\n'
	     '\treturn {}'.format(res),
	     env)
	return env['composition']


class absentmember(Member[Union['NotImplemented', T]]):  # see python/mypy#4791
	default = NotImplemented
	key     = NotImplemented

	def __get__(self, obj: 'Object', _type: type) -> Union['member[T]', T]:
		if obj is None:
			return self
		return getattr(obj._values_, self.name)  # pylint: disable=protected-access

	def __set__(self, obj: 'Object', value: T) -> None:
		return setattr(obj._values_, self.name, value)  # pylint: disable=protected-access

	def push(self, push, value):
		if value is not NotImplemented:
			raise ValueError('value provided for absent member {!r}'
			                 .format(self.name))

	def pop(self, pop):
		return NotImplemented


class member(Member[T]):
	__slots__ = ('key', 'pipe', 'default', 'json_to', 'for_json')

	def __init__(self,
	             key:    str,
	             conv:   Optional[Tuple[Callable[[Any], T],
	                                    Callable[[T], Any]]]
	                     = None,
	             *args:  Tuple[Callable[[Any], Any],
	                           Callable[[Any], Any]],
	            ) -> None:
		self.key   = key
		if conv is not None:
			self.pipe = (conv, *args)
		else:
			self.pipe = ()
		self.json_to:  Callable[[object], T]
		self.for_json: Callable[[T], object]

	def __set_name__(self, cls: 'ObjectMeta', name: str) -> None:
		super().__set_name__(cls, name)
		if not self.pipe:
			ann = get_type_hints(cls).get(name, None)
			if (not is_generic_type(ann) and
			    get_origin(ann) is not type(self) and
			    len(get_args(ann)) != 1):
				raise TypeError('no type or conversions '
				                'specified for member {!r}'
				                .format(name))
			self.pipe = (jsontype(get_args(ann)[0]),)

		self.json_to  = _compose(*(p[0] for p in self.pipe))
		self.for_json = _compose(*(p[1] for p in reversed(self.pipe)))

	def __get__(self, obj: 'Object', _type: type) -> Union['member[T]', T]:
		if obj is None:
			return self
		return getattr(obj._values_, self.name)  # pylint: disable=protected-access

	def __set__(self, obj: 'Object', value: T) -> None:
		return setattr(obj._values_, self.name, value)  # pylint: disable=protected-access

	def push(self, push, value):
		super().push(push, value)
		push(self.key, self.for_json(value))

	def pop(self, pop):
		return self.json_to(pop(self.key))


class optionalmember(member[Union['NotImplemented', T]]):
	default = NotImplemented

	def push(self, push, value):
		if value is NotImplemented:
			return
		super().push(push, value)

	def pop(self, pop):
		try:
			datum = pop(self.key)
		except DVRIPDecodeError:
			return NotImplemented
		return self.json_to(datum)


def _isunder(name: str) -> bool:
	return len(name) >= 2 and name[0] == name[-1] == '_'


class ObjectMeta(ABCMeta):
	_begin_:  Callable[['ObjectMeta', object], dict]
	_pusher_: Callable[['ObjectMeta', dict], Callable[[str, object], None]]
	_popper_: Callable[['ObjectMeta', dict], Callable[[str], object]]
	_end_:    Callable[['ObjectMeta', dict], None]

	def __new__(cls, name, bases, namespace, **kwargs) -> 'ObjectMeta':
		names: MutableMapping[str, Member] = OrderedDict()
		for mname, value in namespace.items():
			if (_isunder(mname) or
			    not isinstance(value, Member) or
			    not hasattr(value, 'key')):
				# Pytest-cov mistakenly thinks this branch is
				# not taken.  Place a print statement here to
				# verify.
				continue  # pragma: no cover
			names[intern(mname)] = value
		for mname in names.keys():
			del namespace[mname]
		namespace['_names_'] = tuple(names)

		slots = set(namespace.get('__slots__', ()))
		slots.add('_values_')
		namespace['slots'] = tuple(slots)

		self = super().__new__(cls, name, bases, namespace, **kwargs)  # type: ignore
		assert isinstance(self, ObjectMeta)
		for mname, member in names.items():  # pylint: disable=redefined-outer-name
			member.__set_name__(self, mname)
			setattr(self, mname, member)  # for members()

		members = self.members()
		for mname, member in members.items():
			setattr(self, mname, member)
		self._members_ = tuple(members)  # pylint: disable=protected-access

		return self

	def __init__(self, name, bases, namespace) -> None:  # pylint: disable=too-many-locals
		# pylint: disable=exec-used
		super().__init__(name, bases, namespace)

		self._names_:     Tuple[str, ...]
		self._members_:   Tuple[str, ...]
		self._container_: Type

		initspec = []
		initbody = []
		initvals = {}
		forbody  = []
		forvals  = {'_pusher_': self._pusher_}
		tobody   = []
		tovals   = {'_begin_':  self._begin_,
		            '_popper_': self._popper_,
		            '_end_':    self._end_}

		for mname in reversed(self._members_):
			member = getattr(self, mname)  # pylint: disable=redefined-outer-name

			initspec.append('{0}={0}'.format(mname)
			                if hasattr(member, 'default')
			                else mname)
			initbody.append('\t_self_.{0} = {0}'.format(mname))
			initvals[mname] = getattr(member, 'default', None)

			mvalue = '_member_{}_'.format(mname)
			forbody.append('\t{mvalue}.push(_pusher_(_datum_), '
			                               '_self_.{mname})'
			               .format(mname=mname, mvalue=mvalue))
			forvals[mvalue] = member
			tobody.append('\t{mname}={mvalue}.pop(_popper_(_datum_)),'
			              .format(mname=mname, mvalue=mvalue))
			tovals[mvalue] = member

		if initspec:
			initspec.append('*')
		initspec.append('_self_')
		exec('def __init__({}):\n'
		     '{}\n'
		     '\treturn\n'
		     .format(', '.join(reversed(initspec)),
		             '\n'.join(reversed(initbody))),
		     initvals)
		self._container_ = type('{}._container_'.format(name),
		                        (object,),
		                        {'__slots__': self._members_,
		                         '__init__':  initvals['__init__']})

		exec('def _for_json_(_self_):\n'
		     '\t_datum_ = {{}}\n'
		     '{}\n'
		     '\treturn _datum_\n'
		     .format('\n'.join(reversed(forbody))),
		     forvals)
		self._for_json_ = forvals['_for_json_']

		exec('@classmethod\n'
		     'def _json_to_(_cls_, _datum_):\n'
		     '\t_datum_ = _begin_(_datum_)\n'
		     '\t_self_ = _cls_(\n'
		     '{}\n'
		     '\t)\n'
		     '\t_end_(_datum_)\n'
		     '\treturn _self_\n'
		     .format('\n'.join(reversed(tobody))),
		     tovals)
		self._json_to_ = tovals['_json_to_']

	def members(self) -> MutableMapping[str, Any]:
		members: MutableMapping[str, Any] = OrderedDict()
		for type in reversed(self.__mro__):  # pylint: disable=redefined-builtin
			members.update((mname, getattr(type, mname))
			               for mname in getattr(type, '_names_', ()))
		return members


class Object(Value, metaclass=ObjectMeta):
	_for_json_: Callable[['Object'], object]
	# FIXME _to_json_

	def __init__(self, *args, **kwargs):
		self._values_ = type(self)._container_(*args, **kwargs)

	def __repr__(self):
		args = ('{}={!r}'.format(name, getattr(self, name))
		        for name in self._members_)
		return '{}({})'.format(type(self).__qualname__, ', '.join(args))

	def __eq__(self, other):
		if (not isinstance(other, Object) or
		    self._members_ != other._members_):  # pylint: disable=protected-access
			return NotImplemented
		return all(getattr(self, member) == getattr(other, member)
		           for member in self._members_)

	def for_json(self) -> object:
		return self._for_json_()

	@classmethod
	def json_to(cls: Type[O], datum: object) -> O:
		return cls._json_to_(datum)  # type: ignore

	@staticmethod
	def _begin_(datum: object) -> dict:
		if not isinstance(datum, dict):
			raise DVRIPDecodeError('not an object')
		return dict(datum)

	@staticmethod
	def _pusher_(datum: dict) -> Callable[[str, object], None]:
		def push(key: str, value: object) -> None:
			if key in datum:
				raise TypeError('member {!r} already '
				                'set'.format(key))
			datum[key] = value
		return push

	@staticmethod
	def _popper_(datum: dict) -> Callable[[str], object]:
		def pop(key: str) -> object:
			try:
				return datum.pop(key)
			except KeyError:
				raise DVRIPDecodeError('no member {!r}'
				                       .format(key))
		return pop

	@staticmethod
	def _end_(datum: dict) -> None:
		if not datum:
			return
		key, _ = datum.popitem()
		raise DVRIPDecodeError('extra member {!r}'.format(key))
