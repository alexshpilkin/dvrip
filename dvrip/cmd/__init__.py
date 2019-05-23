from os import environ, execvp
from os.path import basename
from sys import executable, stderr
from typing import List, NoReturn

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


DVR_HOST         = 'DVR_HOST'
DVR_SERV         = 'DVR_SERV'
DVR_USERNAME     = 'DVR_USERNAME'
DVR_PASSWORD     = 'DVR_PASSWORD'
DVR_PROG         = 'DVR_PROG'
DVR_PROG_CONNECT = 'DVR_PROG_CONNECT'


def host():
	return environ.get(DVR_HOST)
def serv():
	return int(environ.get(DVR_SERV))
def username():
	return environ.get(DVR_USERNAME)
def password():
	return environ.get(DVR_PASSWORD)
def prog():
	return environ.get(DVR_PROG)
def prog_connect():
	return environ.get(DVR_PROG_CONNECT)


def run(prog: str, args: List[str]):  # pylint: disable=redefined-outer-name
	prog = basename(prog)
	if prog in {'__main__.py', '-c'}:
		prog = '{} -m dvrip'.format(executable)
	environ[DVR_PROG] = prog
	environ[DVR_PROG_CONNECT] = ('{} -h HOST [-p PORT] [-u USERNAME]'
	                             .format(prog))

	name = 'dvr-' + args[0]
	try:
		execvp(name, [name] + args[1:])
	except OSError as e:
		osexit(e)


def main():
	from sys import argv
	run(argv[0], argv[1:])
