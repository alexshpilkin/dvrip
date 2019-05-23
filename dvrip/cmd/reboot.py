from socket import AF_INET, SOCK_STREAM, socket as Socket
from sys import stderr
from typing import List, NoReturn
from ..io import DVRIPClient
from . import EX_USAGE, guard, prog_connect


def usage() -> NoReturn:
	print('Usage: {} reboot'.format(prog_connect()),
	      file=stderr)
	exit(EX_USAGE)


def run(host: str,
        serv: int,
        username: str,
        password: str,
        args: List[str]
       ) -> None:
	if args:
		usage()

	conn = DVRIPClient(Socket(AF_INET, SOCK_STREAM))
	conn.connect((host, serv), username, password)
	conn.reboot()


def main() -> None:
	from sys import argv
	from . import host, serv, username, password

	if host() is None:
		usage()
	guard(run, host(), serv(), username(), password(), argv[1:])
