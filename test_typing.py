from enum import IntEnum
from hypothesis import given
from hypothesis.strategies import binary, booleans, dictionaries, integers, \
                                  lists, sampled_from, text
from pytest import raises  # type: ignore
from string import hexdigits
from typing import Callable, Dict, List, SupportsBytes, Type, TypeVar, \
                   no_type_check

from dvrip.errors import DVRIPDecodeError
from dvrip.typing import EnumValue, Member, Object, Value, absentmember, \
                         _compose, for_json, json_to, jsontype, member, \
                         optionalmember


def test_forjson():
	with raises(TypeError, match='not a JSON value'):
		for_json(NotImplementedError())

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

@given(booleans())
def test_bool_forjson(b):
	assert for_json(b) == b

@given(booleans())
def test_bool_jsonto(b):
	assert json_to(bool)(b) == b
	with raises(DVRIPDecodeError, match='not a boolean'):
		json_to(bool)(1)

@given(booleans())
def test_bool_forjson_jsonto(b):
	assert json_to(bool)(for_json(b)) == b

@given(booleans())
def test_bool_jsonto_forjson(b):
	assert for_json(json_to(bool)(b)) == b

@given(integers())
def test_int_forjson(i):
	assert for_json(i) == i

@given(integers())
def test_int_jsonto(i):
	assert json_to(int)(i) == i
	with raises(DVRIPDecodeError, match='not an integer'):
		# False and True are tricky, because issubclass(bool, int)
		json_to(int)(False)

@given(integers())
def test_int_forjson_jsonto(i):
	assert json_to(int)(for_json(i)) == i

@given(integers())
def test_int_jsonto_forjson(i):
	assert for_json(json_to(int)(i)) == i

@given(text())
def test_str_forjson(s):
	assert for_json(s) == s

@given(text())
def test_str_jsonto(s):
	assert json_to(str)(s) == s
	with raises(DVRIPDecodeError, match='not a string'):
		json_to(str)(57)

@given(text())
def test_str_forjson_jsonto(s):
	assert json_to(str)(for_json(s)) == s

@given(text())
def test_str_jsonto_forjson(s):
	assert for_json(json_to(str)(s)) == s

@given(lists(integers()))
def test_list_forjson(l):
	assert for_json(l) == l

@given(lists(integers()))
def test_list_jsonto(l):
	assert json_to(List[int])(l) == l
	with raises(DVRIPDecodeError, match='not an array'):
		json_to(List[int])({})
	with raises(DVRIPDecodeError, match='not an integer'):
		json_to(List[int])([False])
	with raises(TypeError, match='no element type specified'):
		json_to(list)(l)

@given(lists(integers()))
def test_list_forjson_jsonto(l):
	assert json_to(List[int])(for_json(l)) == l

@given(lists(integers()))
def test_list_jsonto_forjson(l):
	assert for_json(json_to(List[int])(l)) == l

@given(dictionaries(text(), integers()))
def test_dict_forjson(d):
	assert for_json(d) == d

@given(dictionaries(text(), integers()))
def test_dict_jsonto(d):
	assert json_to(Dict[str, int])(d) == d
	with raises(DVRIPDecodeError, match='not an object'):
		json_to(Dict[str, int])([])
	with raises(DVRIPDecodeError, match='not a string'):
		json_to(Dict[str, int])({42: 57})
	with raises(DVRIPDecodeError, match='not an integer'):
		json_to(Dict[str, int])({'key': False})
	with raises(TypeError, match='no value type specified'):
		json_to(dict)(d)

@given(dictionaries(text(), integers()))
def test_dict_forjson_jsonto(d):
	assert json_to(Dict[str, int])(for_json(d)) == d

@given(dictionaries(text(), integers()))
def test_dict_jsonto_forjson(d):
	assert for_json(json_to(Dict[str, int])(d)) == d

def test_jsontype():
	assert jsontype(int) == (json_to(int), for_json)

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

@given(integers())
def test_compose(i):
	assert _compose(lambda x: x+1, lambda x: 2*x)(i) == 2*i + 1

def fromhex(value: object) -> bytes:
	if not all(c in hexdigits for c in value):
		raise DVRIPDecodeError('not a hex string')
	return bytes.fromhex(value)

def tohex(value: SupportsBytes) -> object:
	return bytes(value).hex()

def hextext():
	return (text(sampled_from('0123456789abcdef'))
	            .filter(lambda s: len(s) % 2 == 0))

class AbsentExample(Object):
	mint: absentmember[int] = absentmember()

@given(integers())
def test_absentmember_forjson(i):
	obj = AbsentExample()
	assert obj.for_json() == {}
	obj.mint = i
	with raises(ValueError, match='value provided for absent member'):
		obj.for_json()

def test_absentmember_jsonto():
	assert AbsentExample.json_to({}).mint == NotImplemented

class Example(Object):
	# a descriptor but not a field
	@property
	def room(self):
		return 101

	mint: member[int]   = member('Int')
	mhex: member[bytes] = member('Hex', (fromhex, tohex), jsontype(str))

class NestedExample(Object):
	mint = member('Int', jsontype(int))
	mobj: member[Example] = member('Obj')

class ConflictExample(Object):
	mint: member[int] = member('Conflict')
	nint: member[int] = member('Conflict')

def test_Object():
	assert issubclass(Object, Value)

@no_type_check
def test_Member_nojsonto():
	with raises(TypeError, match='no type or conversions specified'):
		class FailingExample(Example):
			bad = member('Bad')
	with raises(TypeError, match='no type or conversions specified'):
		class FailingExample(Example):
			bad: 3 = member('Bad')
	with raises(TypeError):
		class FailingExample(Example):
			bad: member[NotImplementedError] = member('Bad')
		FailingExample(bad=NotImplementedError()).for_json()

@given(integers(), binary())
def test_Object_get(i, b):
	mobj = Example(mint=i, mhex=b)
	assert mobj.mint == i and mobj.mhex == b

@given(integers(), binary(), integers(), binary())
def test_Object_set(i, b, j, c):
	mobj = Example(mint=i, mhex=b)
	assert mobj.mint == i and mobj.mhex == b
	mobj.mint = j
	assert mobj.mint == j and mobj.mhex == b
	mobj.mhex = c
	assert mobj.mint == j and mobj.mhex == c

@given(integers(), binary())
def test_Object_repr(i, b):
	assert (repr(Example(mint=i, mhex=b)) ==
	        'Example(mint={!r}, mhex={!r})'.format(i, b))

@given(integers(), binary(), integers(), binary())
def test_Object_eq(i, b, j, c):
	assert ((Example(mint=i, mhex=b) == Example(mint=j, mhex=c)) ==
	         (i == j and b == c))
	assert Example(mint=i, mhex=b) != Ellipsis

@given(integers(), binary(), integers())
def test_Object_forjson(i, b, j):
	assert Example(mint=i, mhex=b).for_json() == {'Int': i, 'Hex': b.hex()}
	with raises(TypeError, match='already set'):
		ConflictExample(mint=i, nint=j).for_json()

@given(integers(), hextext())
def test_Object_jsonto(i, h):
	assert (Example.json_to({'Int': i, 'Hex': h}) ==
	        Example(mint=i, mhex=bytes.fromhex(h)))
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
	mobj = Example(mint=j, mhex=b)
	assert Example.json_to(mobj.for_json()) == mobj
	nst = NestedExample(mint=i, mobj=mobj)
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
