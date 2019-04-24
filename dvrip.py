from hashlib import md5
from string  import ascii_lowercase, ascii_uppercase, digits

HASHMAGIC = (digits + ascii_uppercase + ascii_lowercase).encode('ascii')
def hash(password):
	mdfive = md5(bytes(password)).digest()
	return bytes(HASHMAGIC[(a+b) % len(HASHMAGIC)]
	             for a, b in zip(mdfive[0::2], mdfive[1::2]))[:8]
