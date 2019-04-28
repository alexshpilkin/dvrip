from hypothesis import given
from hypothesis.strategies \
                import binary, integers as ints, sampled_from, text
from pytest     import raises  # type: ignore
from string     import hexdigits
from typing     import Type, TypeVar, no_type_check

from dvrip.errors import DVRIPDecodeError
from dvrip.typing import Integer, Member, Object, String, Value, member


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

def test_Integer():
	assert issubclass(Integer, Value)

@given(ints())
def test_Integer_int(i):
	assert int(Integer(i)) == i

@given(ints(), ints())
def test_Integer_eq(i, j):
	assert (Integer(i) == Integer(j)) == (i == j)

@given(ints())
def test_Integer_repr(i):
	assert repr(Integer(i)) == 'Integer({})'.format(i)

@given(ints())
def test_Integer_str(i):
	assert str(Integer(i)) == str(i)

@given(ints())
def test_Integer_forjson(i):
	assert Integer(i).for_json() == i

@given(ints())
def test_Integer_jsonto(i):
	assert Integer.json_to(i) == Integer(i)
	with raises(DVRIPDecodeError, match='not an integer'):
		# False and True are tricky, because issubclass(bool, int)
		Integer.json_to(False)

@given(ints())
def test_Integer_forjson_jsonto(i):
	i = Integer(i)
	assert Integer.json_to(i.for_json()) == i

@given(ints())
def test_Integer_jsonto_forjson(i):
	assert Integer.json_to(i).for_json() == i

def integers():
	return ints().map(Integer)

def test_String():
	assert issubclass(String, Value)

@given(text())
def test_String_str(s):
	assert str(String(s)) == s

@given(text(), text())
def test_String_eq(s, t):
	assert (String(s) == String(t)) == (s == t)

@given(text())
def test_String_repr(s):
	assert repr(String(s)) == 'String({!r})'.format(s)

@given(text())
def test_String_forjson(s):
	assert String(s).for_json() == s

@given(text())
def test_String_jsonto(s):
	assert String.json_to(s) == String(s)
	with raises(DVRIPDecodeError, match='not a string'):
		String.json_to(57)

@given(text())
def test_String_forjson_jsonto(s):
	s = String(s)
	assert String.json_to(s.for_json()) == s

@given(text())
def test_String_jsonto_forjson(s):
	assert String.json_to(s).for_json() == s

def strings():
	return map(String, text())

class SubclassMember(Member):
	pass

class DuckMember(object):
	def __set_name__(self, _type: Type['Object'], _name: str) -> None:
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
	int: member[Integer] = member('Int', Integer.json_to, default=Integer(2))
	hex: member[str]     = member('Hex', fromhex, tohex, default=b'\x57')

class BigExample(Example):
	# a descriptor but not a field
	@property
	def room(self):
		return 101
	# note the single quote
	int_: member[Integer] = member("Int'")
	hex_: member[str]     = member("Hex'", fromhex, tohex, default=b'\x42')

class NestedExample(Object):
	int = member('Int', Integer.json_to)  # type: ignore
	rec: member[Example] = member('Rec')

class ConflictExample(Object):
	int1: member[Integer] = member('Conflict')
	int2: member[Integer] = member('Conflict')

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

@given(integers(), binary())
def test_Object_get(i, b):
	rec = Example(i, b)
	assert rec.int == i and rec.hex == b

@given(integers(), binary(), integers(), binary())
def test_Object_set(i, b, j, c):
	rec = Example(i, b)
	assert rec.int == i and rec.hex == b
	rec.int = j
	assert rec.int == j and rec.hex == b
	rec.hex = c
	assert rec.int == j and rec.hex == c

@given(integers(), binary(), integers())
def test_Object_defaults(i, b, j):
	assert Example().int == Integer(2) and Example().hex == b'\x57'
	assert Example(i).hex == b'\x57'
	assert Example(hex=b).int == Integer(2)
	assert BigExample(i, b, j).hex_ == b'\x42'
	with raises(TypeError):
		BigExample(int=i, int_=j)

@given(integers(), binary())
def test_Object_repr(i, b):
	assert repr(Example(i, b)) == 'Example(int={!r}, hex={!r})'.format(i, b)

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

@given(ints(), hextext())
def test_Object_jsonto(i, h):
	assert (Example.json_to({'Int': i, 'Hex': h}) ==
	        Example(Integer(i), bytes.fromhex(h)))
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
	rec = Example(j, b)
	assert Example.json_to(rec.for_json()) == rec
	nst = NestedExample(i, rec)
	assert NestedExample.json_to(nst.for_json()) == nst

@given(ints(), ints(), hextext())
def test_Object_jsonto_forjson(i, j, h):
	obj = {'Int': j, 'Hex': h}
	assert Example.json_to(obj).for_json() == obj
	nst = {'Int': i, 'Rec': obj}
	assert NestedExample.json_to(nst).for_json() == nst
