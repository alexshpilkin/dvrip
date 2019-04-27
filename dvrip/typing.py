from abc         import ABCMeta, abstractmethod
from collections import OrderedDict
from sys         import intern
from typing      import Any, Callable, Generic, MutableMapping, Tuple
from typing      import Type, TypeVar, Union
from .errors     import DVRIPDecodeError

T = TypeVar('T')
V = TypeVar('V', bound='Value')
I = TypeVar('I', bound='Integer')
O = TypeVar('O', bound='Object')


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


class Integer(Value, int):
	def __repr__(self) -> str:
		return 'Integer({})'.format(self)

	def __str__(self) -> str:
		return str(int(self))

	def for_json(self) -> int:
		return int(self)

	@classmethod
	def json_to(cls: Type[I], datum: object) -> I:
		if not isinstance(datum, int) or isinstance(datum, bool):
			raise DVRIPDecodeError('not an integer')
		return cls(datum)


def _isunder(name: str) -> bool:
	return len(name) >= 2 and name[0] == name[-1] == '_'


def _for_json(obj) -> object:
	return obj.for_json()


class Member(metaclass=ABCMeta):
	__slots__ = ('__name__',)
	__name__: str

	@abstractmethod
	def __set_name__(self, _type: Type['Object'], name: str) -> None:
		self.__name__ = name

	@classmethod
	def __subclasshook__(cls, other: Type) -> bool:
		if cls is not Member:
			return NotImplemented
		for method in ('__set_name__',):
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

class member(Member, Generic[T]):
	__slots__ = ('key', 'json_to', 'for_json', 'default')

	def __init__(self,
	             key:      str,
	             json_to:  Callable[[object], T],
	             for_json: Callable[[T], object] = _for_json,
	             default = _SENTINEL
	            ) -> None:
		self.key      = key
		self.json_to  = json_to
		self.for_json = for_json
		if default is not _SENTINEL:
			self.default: str = default

	def __set_name__(self, type: Type['Object'], name: str) -> None:  # pylint: disable=redefined-builtin, useless-super-delegation
		super().__set_name__(type, name)

	def __get__(self, obj: 'Object', _type: type) -> Union['member[T]', T]:
		if obj is None:
			return self
		return getattr(obj._values_, self.__name__)  # pylint: disable=protected-access

	def __set__(self, obj: 'Object', value: T) -> None:
		return setattr(obj._values_, self.__name__, value)  # pylint: disable=protected-access


def _obj(obj: object) -> dict:
	if not isinstance(obj, dict):
		raise DVRIPDecodeError('not an object')
	return dict(obj)


def _pop(obj: dict, key: str) -> object:
	assert isinstance(obj, dict)
	try:
		return obj.pop(key)
	except KeyError:
		raise DVRIPDecodeError('no member {!r}'.format(key))


def _nil(obj: dict) -> None:
	assert isinstance(obj, dict)
	if not obj:
		return
	key, _ = obj.popitem()
	raise DVRIPDecodeError('extra member {!r}'.format(key))


class ObjectMeta(ABCMeta):
	def __new__(cls, name, bases, namespace, **kwargs) -> 'ObjectMeta':
		names: MutableMapping[str, Any] = OrderedDict()
		for mname, value in namespace.items():
			if (_isunder(mname) or
			    not hasattr(value, '__set_name__') or
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
		forvals  = {}
		tobody   = []
		tovals   = {'_obj_': _obj, '_pop_': _pop, '_nil_': _nil}
		defaults = True

		for mname in reversed(self._members_):
			member = getattr(self, mname)  # pylint: disable=redefined-outer-name

			if not hasattr(member, 'default'):
				defaults = False
			initspec.append('{0}={0}'.format(mname)
			                if defaults else mname)
			initbody.append('\t_self_.{0} = {0}'.format(mname))
			initvals[mname] = getattr(member, 'default', None)

			key  = '_key_{}_'.format(mname)
			func = '_func_{}_'.format(mname)
			forbody.append('\t_datum_[{}] = {}(_self_.{})'
			               .format(key, func, mname))
			forvals[func] = member.for_json
			forvals[key]  = member.key
			tobody.append('\t\t{}={}(_pop_(_datum_, {})),'
			              .format(mname, func, key))
			tovals[func] = member.json_to
			tovals[key]  = member.key

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
		     '\t_datum_ = _obj_(_datum_)\n'
		     '\t_self_ = _cls_(\n'
		     '{}\n'
		     '\t)\n'
		     '\t_nil_(_datum_)\n'
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
