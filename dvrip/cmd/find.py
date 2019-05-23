from datetime import datetime
from getopt import GetoptError, getopt
from socket import AF_INET, SOCK_STREAM, socket as Socket
from sys import stderr
from typing import List, NoReturn
from ..files import FileType
from ..io import DVRIPClient
from ..message import EPOCH
from . import EX_USAGE, guard, prog_connect


def usage() -> NoReturn:
	print('Usage: {} find {{-i|-v}} [-l] [-s START] [-e END] -c CHANNEL'
	      .format(prog_connect()),
	      file=stderr)
	exit(EX_USAGE)


def run(host: str,  # pylint: disable=too-many-branches,too-many-locals
        serv: int,
        username: str,
        password: str,
        args: List[str]
       ) -> None:
	try:
		opts, args = getopt(args, 'lhivs:e:c:')
	except GetoptError:
		usage()
	if args:
		usage()

	long = False
	size = lambda L: str(L) + 'K'
	filetype, start, end, channel = None, None, None, None
	for opt, arg in opts:
		if opt == '-l':
			long = True
		if opt == '-h':
			from humanize import naturalsize  # type: ignore
			size = lambda L: naturalsize(L*1024, gnu=True)  # pylint:disable=cell-var-from-loop
		if opt == '-i':
			if filetype is not None:
				usage()
			filetype = FileType.IMAGE
		if opt == '-v':
			if filetype is not None:
				usage()
			filetype = FileType.VIDEO
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
		if opt == '-c':
			try:
				channel = int(arg, base=0)
			except ValueError:
				usage()
	if filetype is None or channel is None:
		usage()
	if start is None:
		start = EPOCH
	if end is None:
		end = datetime.now()

	conn = DVRIPClient(Socket(AF_INET, SOCK_STREAM))
	conn.connect((host, serv), username, password)
	for file in conn.files(start=start,
	                       end=end,
	                       channel=channel,
	                       type=filetype):
		if long:
			print('{} {} {} {} {:>8} {}'
			      .format(file.disk, file.part,
			              file.start.isoformat(),
			              file.end.isoformat(),
			              size(file.length),
			              file.name))
		else:
			print(file.name)


def main() -> None:
	from sys import argv
	from . import host, serv, username, password

	if host() is None:
		usage()
	guard(run, host(), serv(), username(), password(), argv[1:])
