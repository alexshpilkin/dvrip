from getopt import GetoptError, getopt
from socket import gethostbyname
from sys import stderr
from typing import List, NoReturn
from ..io import DVRIPClient
from . import EX_USAGE, EX_NOHOST, guard, osexit, prog


def usage() -> NoReturn:
	print('Usage: {} discover'.format(prog()), file=stderr)
	exit(EX_USAGE)


def run(args: List[str]) -> None:
	try:
		opts, args = getopt(args, 'i:t:')
	except GetoptError:
		usage()
	if args:
		usage()

	interface = ''
	timeout   = 1.0
	for opt, arg in opts:
		if opt == '-i':
			try:
				interface = gethostbyname(arg)
			except OSError as e:
				osexit(e, EX_NOHOST)
		if opt == '-t':
			try:
				timeout = float(arg)
			except ValueError:
				usage()

	for result in DVRIPClient.discover(interface, timeout):
		print('{} {} {} {}/{} via {} port {} channels {}'
		      .format(result.serial, result.mac, result.name,
		              result.host, result.mask, result.router,
		              result.tcpport, result.channels))


def main() -> None:
	from sys import argv
	from . import host

	if host() is not None:
		usage()
	guard(run, argv[1:])
