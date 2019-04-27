from hypothesis import given
from hypothesis.strategies \
                import binary, integers, sampled_from, text
from pytest import raises
from string import hexdigits

from dvrip.errors import DVRIPDecodeError
from dvrip.typing import Object as _Object, member


def fromint(value):
	if not isinstance(value, int):
		raise DVRIPDecodeError('not an integer')
	return value

def toint(value):
	assert isinstance(value, int)
	return value

def fromhex(value):
	if not isinstance(value, str) or not all(c in hexdigits for c in value):
		raise DVRIPDecodeError('not a hex string')
	return bytes.fromhex(value)

def tohex(value):
	return memoryview(value).hex()

def hextext():
	return (text(sampled_from('0123456789abcdef'))
	            .filter(lambda s: len(s) % 2 == 0))

class Object(_Object):
	int = member('Int', fromint, toint, 2)
	hex = member('Hex', fromhex, tohex, default=b'\x57')

class BigObject(Object):
	# note the single quote
	int_ = member("Int'", fromint, toint)
	hex_ = member("Hex'", fromhex, tohex, default=b'\x42')

class NestedObject(_Object):
	int = member('Int', fromint, toint)
	rec = member('Rec', Object.json_to)

@given(integers(), binary())
def test_Object_get(i, b):
	rec = Object(i, b)
	assert rec.int == i and rec.hex == b

@given(integers(), binary(), integers(), binary())
def test_Object_set(i, b, j, c):
	rec = Object(i, b)
	assert rec.int == i and rec.hex == b
	rec.int = j
	assert rec.int == j and rec.hex == b
	rec.hex = c
	assert rec.int == j and rec.hex == c

@given(integers(), binary(), integers(), binary())
def test_Object_defaults(i, b, j, c):
	assert Object().int == 2 and Object().hex == b'\x57'
	assert Object(i).hex == b'\x57'
	assert Object(hex=b).int == 2
	assert BigObject(i, b, j).hex_ == b'\x42'
	with raises(TypeError):
		BigObject(int=i, int_=j)

@given(integers(), binary())
def test_Object_repr(i, b):
	assert repr(Object(i, b)) == 'Object(int={}, hex={})'.format(i, b)

@given(integers(), binary(), integers(), binary())
def test_Object_eq(i, b, j, c):
	assert ((Object(i, b) == Object(j, c)) ==
	         (i == j and b == c))
	assert Object(i, b) != Ellipsis

@given(integers(), binary())
def test_Object_forjson(i, b):
	assert Object(i, b).for_json() == {'Int': i, 'Hex': b.hex()}

@given(integers(), hextext())
def test_Object_jsonto(i, h):
	assert (Object.json_to({'Int': i, 'Hex': h}) ==
	        Object(i, bytes.fromhex(h)))
	with raises(DVRIPDecodeError, match='not an object'):
		Object.json_to([])
	with raises(DVRIPDecodeError, match='no member'):
		Object.json_to({})
	with raises(DVRIPDecodeError, match='no member'):
		Object.json_to({'Int': i})
	with raises(DVRIPDecodeError, match='no member'):
		Object.json_to({'Hex': h})
	with raises(DVRIPDecodeError, match='extra member'):
		Object.json_to({'Int': i, 'Hex': h, 'Extra': Ellipsis})

@given(integers(), integers(), binary())
def test_Object_forjson_jsonto(i, j, b):
	rec = Object(j, b)
	assert Object.json_to(rec.for_json()) == rec
	nst = NestedObject(i, rec)
	assert NestedObject.json_to(nst.for_json()) == nst

@given(integers(), integers(), hextext())
def test_Object_forjson_jsonto(i, j, h):
	obj = {'Int': j, 'Hex': h}
	assert Object.json_to(obj).for_json() == obj
	nst = {'Int': i, 'Rec': obj}
	assert NestedObject.json_to(nst).for_json() == nst
