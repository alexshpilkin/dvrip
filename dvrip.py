from hashlib import md5
from string  import ascii_lowercase, ascii_uppercase, digits

MD5MAGIC = (digits + ascii_uppercase + ascii_lowercase).encode('ascii')
def md5crypt(password):
	mdfive = md5(bytes(password)).digest()
	return bytes(MD5MAGIC[(a+b) % len(MD5MAGIC)]
	             for a, b in zip(mdfive[0::2], mdfive[1::2]))[:8]
