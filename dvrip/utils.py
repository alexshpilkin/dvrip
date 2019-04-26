from inspect import currentframe
from .errors import DVRIPError


def init(type, obj=None):  # pylint: disable=redefined-builtin
	frame = currentframe().f_back
	for attr in type.__slots__:
		setattr(obj, attr, frame.f_locals[attr])

def pun(attrs):
	frame = currentframe().f_back
	return {attr: frame.f_locals[attr] for attr in attrs}


def checkbool(json, description):
	if not isinstance(json, bool):
		raise DVRIPError('not a boolean in {}'.format(description))
	return json

def checkint(json, description):
	if not isinstance(json, int):
		raise DVRIPError('not an integer in {}'.format(description))
	return json

def checkstr(json, description):
	if not isinstance(json, str):
		raise DVRIPError('not a string in {}'.format(description))
	return json

def checkdict(json, description):
	if not isinstance(json, dict):
		raise DVRIPError('not a dictionary in {}'.format(description))
	return json

def checkempty(json, description):
	assert isinstance(json, dict)
	if json:
		raise DVRIPError('extra keys in {}'.format(description))
	return json

def popkey(json, key, description):
	assert isinstance(json, dict)
	value = json.pop(key, Ellipsis)
	if value is Ellipsis:
		raise DVRIPError('{} missing'.format(description))
	return value

def popint(json, key, description):
	return checkint(popkey(json, key, description), description)

def popstr(json, key, description):
	return checkstr(popkey(json, key, description), description)
