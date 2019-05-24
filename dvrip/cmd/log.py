from datetime import datetime
from getopt import GetoptError, getopt
from socket import AF_INET, SOCK_STREAM, socket as Socket
from sys import stderr
from typing import List, NoReturn
from ..io import DVRIPClient
from ..message import EPOCH
from . import EX_USAGE, guard, prog_connect


def usage() -> NoReturn:
	print('Usage: {} log [-s START] [-e END]'.format(prog_connect()),
	      file=stderr)
	exit(EX_USAGE)


def run(host: str,
        serv: int,
        username: str,
        password: str,
        args: List[str]
       ) -> None:
	try:
		opts, args = getopt(args, 's:e:')
	except GetoptError:
		usage()
	if args:
		usage()

	start = EPOCH
	end = datetime.now()
	for opt, arg in opts:
		if opt == '-s':
			from dateparser import parse  # type: ignore
			start = parse(arg)
			if start is None:
				usage()
		if opt == '-e':
			from dateparser import parse  # type: ignore
			end = parse(arg)
			if end is None:
				usage()

	conn = DVRIPClient(Socket(AF_INET, SOCK_STREAM))
	conn.connect((host, serv), username, password)
	try:
		for entry in conn.log(start=start, end=end):
			print('{:>8} {} {:>12} {}'
			      .format(entry.number,
			              entry.time.isoformat(),
			              entry.type.name.lower(),
			              entry.data))
	finally:
		conn.logout()


def main() -> None:
	from sys import argv
	from . import host, serv, username, password

	if host() is None:
		usage()
	guard(run, host(), serv(), username(), password(), argv[1:])
