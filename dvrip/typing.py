from abc         import ABCMeta, abstractmethod
from collections import OrderedDict
from enum        import Enum, EnumMeta
from sys         import intern
from typing      import Any, Callable, Generic, MutableMapping, Optional, \
                        Tuple, TYPE_CHECKING, Type, TypeVar, Union, \
                        get_type_hints
from typing_extensions import Protocol, runtime
from typing_inspect import is_generic_type, get_origin, get_args  # type: ignore
from .errors     import DVRIPDecodeError

V = TypeVar('V', bound='Union[bool, int, str, Value]')
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


def for_json(obj: V.__bound__) -> object:
	try:
		return obj.for_json()
	except AttributeError:
		if isinstance(obj, (bool, int, str)):
			return obj
		raise TypeError('not a JSON value')


def json_to(type):  # pylint: disable=redefined-builtin
	if issubclass(type, Value):
		return type.json_to
	if issubclass(type, bool):  # needs to come before 'int'
		return _json_to_bool
	if issubclass(type, int):
		return _json_to_int
	if issubclass(type, str):
		return _json_to_str
	return None


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


class EnumValueMeta(EnumMeta, ABCMeta):
	pass


class EnumValue(Value, Enum, metaclass=EnumValueMeta):  # pylint: disable=abstract-method
	pass


if TYPE_CHECKING:  # pragma: no cover
	@runtime
	class Member(Generic[V], Protocol):
		# pylint: disable=no-self-use,unused-argument
		name: str

		def __set_name__(self, _type: 'ObjectMeta', name: str) -> None:
			self.name = name

		def push(self,
		         push: Callable[[str, object], None],
		         value: V
		        ) -> None:
			...

		def pop(self, pop: Callable[[str], object]) -> V:
			...

else:
	class Member(Generic[V], metaclass=ABCMeta):
		__slots__ = ('name',)
		name: str

		def __set_name__(self, _type: 'ObjectMeta', name: str) -> None:
			self.name = name

		@abstractmethod
		def push(self,
			 push: Callable[[str, object], None],
			 value: V
			) -> None:
			pass

		@abstractmethod
		def pop(self, pop: Callable[[str], object]) -> V:
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


_SENTINEL = object()

class member(Member[V]):
	__slots__ = ('key', 'json_to', 'for_json', 'default')

	def __init__(self,
	             key:      str,
	             json_to:  Optional[Callable[[object], V]] = None,  # pylint: disable=redefined-outer-name
	             for_json: Callable[[V], object] = for_json,        # pylint: disable=redefined-outer-name
	             default = _SENTINEL
	            ) -> None:
		self.key      = key
		self.json_to  = json_to
		self.for_json = for_json
		if default is not _SENTINEL:
			self.default: str = default

	def __set_name__(self, cls: 'ObjectMeta', name: str) -> None:
		super().__set_name__(cls, name)
		if self.json_to is None:
			ann = get_type_hints(cls).get(name, None)
			if (is_generic_type(ann) and
			    get_origin(ann) == type(self)):
				arg, = get_args(ann)
				self.json_to = json_to(arg)
		if self.json_to is None:
			raise TypeError('no type or conversion '
			                'specified for member {!r}'
			                .format(name))

	def __get__(self, obj: 'Object', _type: type) -> Union['member[V]', V]:
		if obj is None:
			return self
		return getattr(obj._values_, self.name)  # pylint: disable=protected-access

	def __set__(self, obj: 'Object', value: V) -> None:
		return setattr(obj._values_, self.name, value)  # pylint: disable=protected-access

	def push(self, push, value):
		super().push(push, value)
		push(self.key, self.for_json(value))

	def pop(self, pop):
		return self.json_to(pop(self.key))


class optionalmember(member[V]):
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
		defaults = True

		for mname in reversed(self._members_):
			member = getattr(self, mname)  # pylint: disable=redefined-outer-name

			if not hasattr(member, 'default'):
				defaults = False
			initspec.append('{0}={0}'.format(mname)
			                if defaults else mname)
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
