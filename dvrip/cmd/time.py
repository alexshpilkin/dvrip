from socket import AF_INET, SOCK_STREAM, socket as Socket
from sys import stderr
from typing import List, NoReturn
from ..io import DVRIPClient
from . import EX_USAGE, guard, prog_connect


def usage() -> NoReturn:
	print('Usage: {} time [TIME]'.format(prog_connect()), file=stderr)
	exit(EX_USAGE)


def run(host: str,
        serv: int,
        username: str,
        password: str,
        args: List[str]
       ) -> None:
	if args:
		from dateparser import parse  # type: ignore
		time = parse(args[0])
		if len(args) > 2 or time is None or time.tzinfo is not None:
			usage()

	conn = DVRIPClient(Socket(AF_INET, SOCK_STREAM))
	conn.connect((host, serv), username, password)
	print((conn.time(time) if args else conn.time()).isoformat())


def main() -> None:
	from sys import argv
	from . import host, serv, username, password

	if host() is None:
		usage()
	guard(run, host(), serv(), username(), password(), argv[1:])
