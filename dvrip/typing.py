from collections import OrderedDict
from sys         import intern
from .errors     import DVRIPDecodeError


def _isunder(name):
	return len(name) >= 2 and name[0] == name[-1] == '_'


def _isdescriptor(name):
	return (hasattr(name, '__get__') or hasattr(name, '__set__') or
	        hasattr(name, '__delete__'))


def _for_json(obj):
	return obj.for_json()


_SENTINEL = object()

class member(object):
	__slots__ = ('key', 'json_to', 'for_json', 'default', '__name__')

	def __init__(self, key, json_to, for_json=_for_json, default=_SENTINEL):
		self.key      = key
		self.json_to  = json_to
		self.for_json = for_json
		if default is not _SENTINEL:
			self.default = default
		self.__name__ = None

	def __set_name__(self, _type, name):
		self.__name__ = name

	def __get__(self, obj, type):  # pylint: disable=redefined-builtin
		if obj is None:
			return self
		return getattr(obj._values_, self.__name__)  # pylint: disable=protected-access

	def __set__(self, obj, value):
		return setattr(obj._values_, self.__name__, value)  # pylint: disable=protected-access


def _obj(obj):
	if not isinstance(obj, dict):
		raise DVRIPDecodeError('not an object')
	return dict(obj)


def _pop(obj, key):
	assert isinstance(obj, dict)
	try:
		return obj.pop(key)
	except KeyError:
		raise DVRIPDecodeError('no member {!r}'.format(key))


def _nil(obj):
	assert isinstance(obj, dict)
	if not obj:
		return
	key, _ = obj.popitem()
	raise DVRIPDecodeError('extra member {!r}'.format(key))


class ObjectMeta(type):
	def __new__(cls, name, bases, clsdict, **kwargs):
		names = OrderedDict()
		for mname, value in clsdict.items():
			if (_isunder(mname) or not _isdescriptor(value) or
			    not hasattr(value, 'key')):
				continue
			names[intern(mname)] = value
		for mname in names.keys():
			del clsdict[mname]
		clsdict['_names_'] = tuple(names)

		slots = set(clsdict.get('__slots__', ()))
		slots.add('_values_')
		clsdict['slots'] = tuple(slots)

		self = super().__new__(cls, name, bases, clsdict, **kwargs)
		for mname, member in names.items():  # pylint: disable=redefined-outer-name
			member.__set_name__(self, mname)
			setattr(self, mname, member)  # for members()

		members = self.members()
		for mname, member in members.items():
			setattr(self, mname, member)
		self._members_ = tuple(members)  # pylint: disable=protected-access

		return self

	def __init__(self, name, bases, clsdict):  # pylint: disable=too-many-locals
		# pylint: disable=exec-used
		super().__init__(name, bases, clsdict)

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


	def members(self):
		members = OrderedDict()
		for type in reversed(self.__mro__):  # pylint: disable=redefined-builtin
			members.update((mname, getattr(type, mname))
			               for mname in getattr(type, '_names_', ()))
		return members


class Object(metaclass=ObjectMeta):
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

	def for_json(self):
		return self._for_json_()

	@classmethod
	def json_to(cls, obj):
		return cls._json_to_(obj)
