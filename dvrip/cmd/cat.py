from shutil import copyfileobj
from socket import AF_INET, SOCK_STREAM, socket as Socket
from sys import exit, stderr, stdout  # pylint: disable=redefined-builtin
from typing import List, NoReturn
from ..io import DVRIPClient
from ..monitor import Stream
from . import EX_USAGE, guard, prog_connect


def usage() -> NoReturn:
	print('Usage: {} cat {{FILE|MONITOR}}'.format(prog_connect()),
	      file=stderr)
	exit(EX_USAGE)


def run(host: str,
        serv: int,
        username: str,
        password: str,
        args: List[str]
       ) -> None:
	if len(args) != 1:
		usage()

	conn = DVRIPClient(Socket(AF_INET, SOCK_STREAM))
	sock = Socket(AF_INET, SOCK_STREAM)

	name, = args
	if name.startswith('/'):
		reader = lambda: conn.download(sock, name)
	elif name.startswith('monitor:'):
		if ';' not in name:
			name += ';hd'
		chanstr, strstr = name[len('monitor:'):].split(';', 1)
		try:
			channel = int(chanstr, base=0)
		except ValueError:
			usage()
		try:
			stream = Stream[strstr.upper()]
		except KeyError:
			usage()
		reader = lambda: conn.monitor(sock, channel, stream)
	else:
		usage()

	conn.connect((host, serv), username, password)
	sock.connect((host, serv))
	try:
		file = reader()
		try:
			copyfileobj(file, stdout.buffer, length=256)
		except (BrokenPipeError, KeyboardInterrupt):
			pass
	finally:
		sock.close()
		conn.logout()


def main() -> None:
	from sys import argv
	from . import host, serv, username, password

	if host() is None:
		usage()
	guard(run, host(), serv(), username(), password(), argv[1:])
