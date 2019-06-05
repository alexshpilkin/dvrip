from getopt import GetoptError, getopt
from getpass import getpass
from os import environ, execvp
from os.path import basename
from socket import gethostbyname, getservbyname
from sys import stderr
from typing import List, NoReturn, Optional
from ..errors import DVRIPDecodeError, DVRIPRequestError

try:
	# pylint: disable=ungrouped-imports
	from os import EX_USAGE, EX_NOHOST, EX_IOERR, EX_PROTOCOL
except ImportError:  # BSD values  # pragma: no cover
	EX_USAGE    = 64
	EX_NOHOST   = 68
	EX_IOERR    = 74
	EX_PROTOCOL = 76


def osexit(e: OSError, code: int = EX_IOERR) -> NoReturn:
	message = ('{}: {}'.format(e.filename, e.strerror) \
	           if e.filename is not None else e.strerror)
	print(message, file=stderr)
	exit(code)


def guard(_func, *args, **kwargs):
	try:
		_func(*args, **kwargs)
	except DVRIPDecodeError as e:
		print(e, file=stderr)
		exit(EX_PROTOCOL)
	except DVRIPRequestError as e:
		print(e, file=stderr)
		exit(2)  # FIXME more granular codes
	except OSError as e:
		osexit(e)


DVR_HOST         = 'DVR_HOST'
DVR_SERV         = 'DVR_SERV'
DVR_USERNAME     = 'DVR_USERNAME'
DVR_PASSWORD     = 'DVR_PASSWORD'
DVR_PROG         = 'DVR_PROG'
DVR_PROG_CONNECT = 'DVR_PROG_CONNECT'


def host() -> Optional[str]:
	return environ.get(DVR_HOST)
def serv() -> int:
	return int(environ.get(DVR_SERV, ''))
def username() -> str:
	return environ.get(DVR_USERNAME, '')
def password() -> str:
	return environ.get(DVR_PASSWORD, '')
def prog() -> str:
	return environ.get(DVR_PROG, '')
def prog_connect() -> str:
	return environ.get(DVR_PROG_CONNECT, '')


def usage(prog: str) -> NoReturn:  # pylint: disable=redefined-outer-name
	print('Usage: {} [-h HOST] [-p PORT] [-u USERNAME] COMMAND ...'
	      .format(prog),
	      file=stderr)
	exit(EX_USAGE)


def run(prog: str, args: List[str]) -> None:  # pylint: disable=redefined-outer-name
	# pylint: disable=redefined-outer-name,too-many-branches,too-many-statements

	prog = basename(prog)
	environ[DVR_PROG] = prog
	environ[DVR_PROG_CONNECT] = ('{} -h HOST [-p PORT] [-u USERNAME]'
	                             .format(prog))

	try:
		opts, args = getopt(args, 'h:p:u:')
	except GetoptError:
		usage(prog)
	if not args:
		usage(prog)
	command, *args = args
	if not all(c.isalnum() or c == '-' for c in command):
		usage(prog)

	host = None
	port = environ.get('DVR_PORT', '34567')
	username = environ.get('DVR_USERNAME', 'admin')
	for opt, arg in opts:
		if opt == '-h':
			host = arg
		if opt == '-p':
			port = arg
		if opt == '-u':
			username = arg

	password = environ.get('DVR_PASSWORD', None)
	if host is not None and password is None:
		try:
			password = getpass('Password: ')
		except EOFError:
			exit(EX_IOERR)

	if host is None:
		environ.pop(DVR_HOST, None)
		environ.pop(DVR_SERV, None)
		environ.pop(DVR_USERNAME, None)
		environ.pop(DVR_PASSWORD, None)
	else:
		try:
			serv = int(port, base=0)
		except ValueError:
			try:
				serv = getservbyname(port)
			except OSError as e:
				osexit(e, EX_NOHOST)

		try:
			host = gethostbyname(host)
		except OSError as e:
			osexit(e, EX_NOHOST)

		assert password is not None

		environ[DVR_HOST] = host
		environ[DVR_SERV] = str(serv)
		environ[DVR_USERNAME] = username
		environ[DVR_PASSWORD] = password

	name = 'dvr-' + command
	try:
		execvp(name, [name] + args)
	except OSError as e:
		osexit(e)


def main() -> None:
	from sys import argv
	run(argv[0], argv[1:])
