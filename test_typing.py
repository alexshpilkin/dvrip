from enum       import IntEnum
from hypothesis import given
from hypothesis.strategies \
                import binary, integers, sampled_from, text
from pytest     import raises  # type: ignore
from string     import hexdigits
from typing     import Callable, Type, TypeVar, no_type_check

from dvrip.errors import DVRIPDecodeError
from dvrip.typing import EnumValue, Member, Object, Value, _for_json, \
                         _json_to_int, _json_to_str, member, optionalmember


def test_forjson():
	with raises(TypeError, match='not a JSON value'):
		_for_json(Ellipsis)

D = TypeVar('D', bound='DuckValue')

class SubclassValue(Value):
	pass

class DuckValue(object):
	def for_json(self) -> object:
		pass

	@staticmethod
	def json_to(cls: Type[D], datum: object) -> D:
		pass

class DuckNoValue(DuckValue):
	json_to = None

def test_Value():
	assert hasattr(Value, 'for_json')
	assert hasattr(Value, 'json_to')

def test_Value_subclasshook():
	assert not issubclass(int, Value)
	assert issubclass(SubclassValue, Value)
	assert not issubclass(Value, SubclassValue)
	assert issubclass(DuckValue, Value)
	assert not issubclass(DuckNoValue, Value)

class SubclassEnumValue(EnumValue, IntEnum):
	ZERO = 0
	ONE  = 1

def test_EnumValue():
	assert issubclass(SubclassEnumValue, IntEnum)
	assert issubclass(SubclassEnumValue, Value)
	assert SubclassEnumValue.ZERO == 0 and SubclassEnumValue.ONE == 1

@given(integers())
def test_int_forjson(i):
	assert _for_json(i) == i

@given(integers())
def test_int_jsonto(i):
	assert _json_to_int(i) == i
	with raises(DVRIPDecodeError, match='not an integer'):
		# False and True are tricky, because issubclass(bool, int)
		_json_to_int(False)

@given(integers())
def test_int_forjson_jsonto(i):
	assert _json_to_int(_for_json(i)) == i

@given(integers())
def test_int_jsonto_forjson(i):
	assert _for_json(_json_to_int(i)) == i

@given(text())
def test_str_forjson(s):
	assert _for_json(s) == s

@given(text())
def test_str_jsonto(s):
	assert _json_to_str(s) == s
	with raises(DVRIPDecodeError, match='not a string'):
		_json_to_str(57)

@given(text())
def test_str_forjson_jsonto(s):
	assert _json_to_str(_for_json(s)) == s

@given(text())
def test_str_jsonto_forjson(s):
	assert _for_json(_json_to_str(s)) == s

class SubclassMember(Member):
	pass

class DuckMember(object):
	def __set_name__(self, _type: Type['Object'], _name: str) -> None:
		pass
	def push(self, push: Callable[[str, object], None], value: set) -> None:
		pass
	def pop(self, pop: Callable[[str], object]) -> set:
		pass

class DuckNoMember(DuckMember):
	__set_name__ = None

def test_Member():
	assert hasattr(Member, '__set_name__')

def test_Member_subclasshook():
	assert not issubclass(int, Member)
	assert issubclass(SubclassMember, Member)
	assert not issubclass(Member, SubclassMember)
	assert issubclass(DuckMember, Member)
	assert not issubclass(DuckNoMember, Member)

def fromhex(value):
	if not isinstance(value, str) or not all(c in hexdigits for c in value):
		raise DVRIPDecodeError('not a hex string')
	return bytes.fromhex(value)

def tohex(value):
	return memoryview(value).hex()

def hextext():
	return (text(sampled_from('0123456789abcdef'))
	            .filter(lambda s: len(s) % 2 == 0))

class Example(Object):
	mint: member[int] = member('Int', _json_to_int, default=2)
	mhex: member[str] = member('Hex', fromhex, tohex, default=b'\x57')

class BigExample(Example):
	# a descriptor but not a field
	@property
	def room(self):
		return 101
	# note the single quote
	nini: member[int] = member("Int'")
	nhex: member[str] = member("Hex'", fromhex, tohex, default=b'\x42')

class NestedExample(Object):
	mint = member('Int', _json_to_int)  # type: ignore
	mobj: member[Example] = member('Obj')

class ConflictExample(Object):
	mint: member[int] = member('Conflict')
	nint: member[int] = member('Conflict')

def test_Object():
	assert issubclass(Object, Value)

@no_type_check
def test_Member_nojsonto():
	with raises(TypeError, match='no type or conversion specified'):
		class FailingExample(Example):
			bad = member('Bad')
	with raises(TypeError, match='no type or conversion specified'):
		class FailingExample(Example):
			bad: 3 = member('Bad')
	with raises(TypeError, match='no type or conversion specified'):
		class FailingExample(Example):
			bad: member[type(Ellipsis)] = member('Bad')

@given(integers(), binary())
def test_Object_get(i, b):
	mobj = Example(i, b)
	assert mobj.mint == i and mobj.mhex == b

@given(integers(), binary(), integers(), binary())
def test_Object_set(i, b, j, c):
	mobj = Example(i, b)
	assert mobj.mint == i and mobj.mhex == b
	mobj.mint = j
	assert mobj.mint == j and mobj.mhex == b
	mobj.mhex = c
	assert mobj.mint == j and mobj.mhex == c

@given(integers(), binary(), integers())
def test_Object_defaults(i, b, j):
	assert Example().mint == 2 and Example().mhex == b'\x57'
	assert Example(i).mhex == b'\x57'
	assert Example(mhex=b).mint == 2
	assert BigExample(i, b, j).nhex == b'\x42'
	with raises(TypeError):
		BigExample(mint=i, nini=j)

@given(integers(), binary())
def test_Object_repr(i, b):
	assert (repr(Example(i, b)) ==
	        'Example(mint={!r}, mhex={!r})'.format(i, b))

@given(integers(), binary(), integers(), binary())
def test_Object_eq(i, b, j, c):
	assert ((Example(i, b) == Example(j, c)) ==
	         (i == j and b == c))
	assert Example(i, b) != Ellipsis

@given(integers(), binary(), integers())
def test_Object_forjson(i, b, j):
	assert Example(i, b).for_json() == {'Int': i, 'Hex': b.hex()}
	with raises(TypeError, match='already set'):
		ConflictExample(i, j).for_json()

@given(integers(), hextext())
def test_Object_jsonto(i, h):
	assert (Example.json_to({'Int': i, 'Hex': h}) ==
	        Example(i, bytes.fromhex(h)))
	with raises(DVRIPDecodeError, match='not an object'):
		Example.json_to([])
	with raises(DVRIPDecodeError, match='no member'):
		Example.json_to({})
	with raises(DVRIPDecodeError, match='no member'):
		Example.json_to({'Int': i})
	with raises(DVRIPDecodeError, match='no member'):
		Example.json_to({'Hex': h})
	with raises(DVRIPDecodeError, match='extra member'):
		Example.json_to({'Int': i, 'Hex': h, 'Extra': Ellipsis})

@given(integers(), integers(), binary())
def test_Object_forjson_jsonto(i, j, b):
	mobj = Example(j, b)
	assert Example.json_to(mobj.for_json()) == mobj
	nst = NestedExample(i, mobj)
	assert NestedExample.json_to(nst.for_json()) == nst

@given(integers(), integers(), hextext())
def test_Object_jsonto_forjson(i, j, h):
	obj = {'Int': j, 'Hex': h}
	assert Example.json_to(obj).for_json() == obj
	nst = {'Int': i, 'Obj': obj}
	assert NestedExample.json_to(nst).for_json() == nst

class OptionalExample(Object):
	mint: member[int] = member('Int1')
	nint: optionalmember[int] = optionalmember('Int2')
	kint: member[int] = member('Int3')

@given(integers(), integers(), integers())
def test_optionalmember_forjson(i, j, k):
	value = OptionalExample(mint=i, nint=j, kint=k)
	assert value.for_json() == {'Int1': i, 'Int2': j, 'Int3': k}
	value = OptionalExample(mint=i, nint=NotImplemented, kint=k)
	assert value.for_json() == {'Int1': i, 'Int3': k}

@given(integers(), integers(), integers())
def test_optionalmember_jsonto(i, j, k):
	datum = {'Int1': i, 'Int2': j, 'Int3': k}
	assert (OptionalExample.json_to(datum) ==
	        OptionalExample(mint=i, nint=j, kint=k))
	datum = {'Int1': i, 'Int3': k}
	assert (OptionalExample.json_to(datum) ==
	        OptionalExample(mint=i, nint=NotImplemented, kint=k))
