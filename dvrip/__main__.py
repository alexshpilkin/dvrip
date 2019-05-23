#!/usr/bin/env python3

from getopt import GetoptError, getopt
from getpass import getpass
from os import environ
from os.path import basename
from socket import AF_INET, SOCK_STREAM, socket as Socket, gethostbyname, \
                   getservbyname
from sys import argv, executable, exit, stderr  # pylint: disable=redefined-builtin
from typing import List, NoReturn, Tuple
from .errors import DVRIPDecodeError, DVRIPRequestError
from .io import DVRIPClient

try:
	# pylint: disable=ungrouped-imports
	from os import EX_USAGE, EX_NOHOST, EX_IOERR, EX_PROTOCOL
except ImportError:  # BSD value  # pragma: no cover
	EX_USAGE    = 64
	EX_NOHOST   = 68
	EX_IOERR    = 74
	EX_PROTOCOL = 76

# pylint: disable=too-many-branches,too-many-locals,too-many-statements


def ioerr(e: OSError, code: int = EX_IOERR) -> NoReturn:
	message = ('{}: {}'.format(e.filename, e.strerror) \
	           if e.filename is not None else e.strerror)
	print(message, file=stderr)
	exit(code)


def resolve(host: str, port: str) -> Tuple[str, int]:
	try:
		serv = int(port, base=0)
	except ValueError:
		try:
			serv = getservbyname(port)
		except OSError as e:
			ioerr(e, EX_NOHOST)
	try:
		host = gethostbyname(host)
	except OSError as e:
		ioerr(e, EX_NOHOST)
	return host, serv


def connect(address: Tuple[str, int], user: str, password: str) -> DVRIPClient:
	conn = DVRIPClient(Socket(AF_INET, SOCK_STREAM))
	try:
		conn.connect(address, user, password)
	except DVRIPDecodeError as e:
		print(e, file=stderr)
		exit(EX_PROTOCOL)
	except DVRIPRequestError as e:
		print(e, file=stderr)
		exit(2)  # FIXME more granular codes
	except OSError as e:
		ioerr(e)
	return conn


def prog() -> str:
	name = basename(argv[0])
	return ('{} -m dvrip'.format(executable)
	        if name in {'__main__.py', '-c'}
	        else name)

def prog_connected() -> str:
	return '{} -h HOST [-p PORT] [-u USERNAME]'.format(prog())

def usage() -> NoReturn:
	print('Usage: {} [-h HOST] [-p PORT] [-u USERNAME] COMMAND ...\n'
	      '       COMMAND is info or reboot'
	      .format(prog()),
	      file=stderr)
	exit(EX_USAGE)


def run(args: List[str] = argv[1:]) -> None:  # pylint: disable=dangerous-default-value
	try:
		opts, args = getopt(args, 'h:p:u:')
	except GetoptError:
		usage()
	if not args:
		usage()
	command, *args = args
	if not all(c.isalnum() or c == '-' for c in command):
		usage()

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

	if command == 'reboot':
		if host is None or args:
			print('Usage: {} reboot'.format(prog_connected()),
			      file=stderr)
			exit(EX_USAGE)
		assert password is not None
		conn = connect(resolve(host, port), username, password)
		conn.reboot()
	else:
		usage()


if __name__ == '__main__':
	run()
