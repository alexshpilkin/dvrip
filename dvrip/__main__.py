#!/usr/bin/env python3

from datetime import datetime
from getopt import GetoptError, getopt
from getpass import getpass
from os import environ
from os.path import basename
from socket import AF_INET, SOCK_STREAM, socket as Socket, gethostbyname, \
                   getservbyname
from sys import argv, executable, exit, stderr  # pylint: disable=redefined-builtin
from typing import List, NoReturn, Tuple
from .errors import DVRIPDecodeError, DVRIPRequestError
from .files import FileType
from .io import DVRIPClient
from .message import EPOCH

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


def info_usage() -> NoReturn:
	print('Usage: {} info'.format(prog_connected()), file=stderr)
	exit(EX_USAGE)

def run_info(conn: DVRIPClient, args: List[str]) -> None:
	if args:
		info_usage()

	info = conn.systeminfo()
	line = [info.chassis, info.board, info.serial]
	for attr in ('hardware', 'eeprom', 'software', 'build', 'videoin',
	             'videoout', 'commin', 'commout', 'triggerin',
	             'triggerout', 'audioin', 'views'):
		value = getattr(info, attr)
		if value:
			line.append('{} {}'.format(attr, value))
	print(' '.join(line))  # system line

	for disk in conn.storageinfo():
		print('disk {}'.format(disk.number))  # disk group
		for i, part in zip(range(disk.parts), disk.partinfo):
			line = ['  part {}'.format(i)]
			if part.current:
				line.append('current')
			line.append('size {}M free {}M'
			            .format(part.size, part.free))
			for attr in ('viewedstart', 'viewedend',
			             'unviewedstart', 'unviewedend'):
				date = getattr(part, attr)
				line.append('{} {}'
				            .format(attr, date.isoformat()))
			print(' '.join(line))  # partition line

	actv = conn.activityinfo()
	line = []
	for i, chan in zip(range(info.videoin), actv.channels):
		print('channel {} bitrate {}K/s'.format(i, chan.bitrate) +
		      (' recording' if chan.recording else ''))

	line = []
	line.append(conn.time().isoformat())
	minutes = info.uptime
	hours, minutes = divmod(minutes, 60)
	days, hours = divmod(hours, 24)
	if days:
		line.append("up P{}dT{:02}h{:02}m".format(days, hours, minutes))
	else:
		line.append("up PT{}h{:02}m".format(hours, minutes))
	line.append('triggers')
	for attr in ('in_', 'out', 'obscure', 'disconnect', 'motion'):
		value = getattr(actv.triggers, attr)
		if value:
			line.append('{} {}'.format(attr.rstrip('_'), value))
	if len(line) <= 3:
		line.append('none')
	print(' '.join(line))  # status line


def find_usage() -> NoReturn:
	print('Usage: {} find -{{i|v}} [-l] [-s START] [-e END] -c CHANNEL'
	      .format(prog_connected()),
	      file=stderr)
	exit(EX_USAGE)

def run_find(conn: DVRIPClient, args: List[str]) -> None:
	try:
		opts, args = getopt(args, 'lhivs:e:c:')
	except GetoptError:
		find_usage()
	if args:
		find_usage()

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
				find_usage()
			filetype = FileType.IMAGE
		if opt == '-v':
			if filetype is not None:
				find_usage()
			filetype = FileType.VIDEO
		if opt == '-s':
			from dateparser import parse  # type: ignore
			start = parse(arg)
			if start is None:
				find_usage()
		if opt == '-e':
			from dateparser import parse  # type: ignore
			end = parse(arg)
			if end is None:
				find_usage()
		if opt == '-c':
			try:
				channel = int(arg, base=0)
			except ValueError:
				find_usage()
	if filetype is None or channel is None:
		find_usage()
	if start is None:
		start = EPOCH
	if end is None:
		end = datetime.now()

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


def prog() -> str:
	name = basename(argv[0])
	return ('{} -m dvrip'.format(executable)
	        if name in {'__main__.py', '-c'}
	        else name)

def prog_connected() -> str:
	return '{} -h HOST [-p PORT] [-u USERNAME]'.format(prog())

def usage() -> NoReturn:
	print('Usage: {} [-h HOST] [-p PORT] [-u USERNAME] COMMAND ...\n'
	      '       COMMAND is one of find, info, or reboot'
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

	if command == 'info':
		if host is None:
			usage()
		assert password is not None
		conn = connect(resolve(host, port), username, password)
		try:
			run_info(conn, args)
		finally:
			conn.logout()
	elif command == 'find':
		if host is None:
			find_usage()
		assert password is not None
		conn = connect(resolve(host, port), username, password)
		try:
			run_find(conn, args)
		finally:
			conn.logout()
	elif command == 'reboot':
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
