#!/usr/bin/env python3

from datetime import datetime
from getopt import GetoptError, getopt
from getpass import getpass
from os import environ
from os.path import basename
from shutil import copyfileobj
from socket import AF_INET, SOCK_STREAM, socket as Socket, gethostbyname, \
                   getservbyname
from sys import argv, executable, exit, stderr, stdout  # pylint: disable=redefined-builtin
from typing import List, NoReturn, TextIO, Tuple
from .errors import DVRIPDecodeError, DVRIPRequestError
from .io import DVRIPClient
from .message import EPOCH, RESOLUTION
from .search import FileType

try:
	# pylint: disable=ungrouped-imports
	from os import EX_USAGE, EX_NOHOST, EX_IOERR, EX_PROTOCOL
except ImportError:  # BSD value  # pragma: no cover
	EX_USAGE    = 64
	EX_NOHOST   = 68
	EX_IOERR    = 74
	EX_PROTOCOL = 76

# pylint: disable=too-many-branches,too-many-locals,too-many-statements


def prog():
	name = basename(argv[0])
	return ('{} -m dvrip'.format(executable)
	        if name in {'__main__.py', '-c'}
	        else name)


def ioerr(e, code=EX_IOERR):
	message = ('{}: {}'.format(e.filename, e.strerror) \
	           if e.filename is not None else e.strerror)
	print(message, file=stderr)
	exit(code)


def resolve(host: str, port: str):
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


def run_info(conn: DVRIPClient, args: List[str]) -> None:
	if args:
		print('Usage: {} ... info'.format(prog()),
		      file=stderr)
		exit(EX_USAGE)

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


def run_time(conn: DVRIPClient, args: List[str]) -> None:
	from dateparser import parse as dateparse  # type: ignore

	time = dateparse(args[0] if args else '1970-01-01')
	if len(args) > 2 or time is None or time.tzinfo is not None:
		print('Usage: {} ... time [TIME]'.format(prog()))
		exit(EX_USAGE)

	print((conn.time(time) if args else conn.time()).isoformat())


def find_usage() -> NoReturn:
	print('Usage: {} ... time [-liv] [-s START] [-e END] -c CHANNEL'
	      .format(prog()))
	exit(EX_USAGE)


def run_find(conn: DVRIPClient, args: List[str]) -> None:
	from dateparser import parse as dateparse  # type: ignore

	try:
		opts, args = getopt(args, 'livs:e:c:')
	except GetoptError:
		find_usage()
	if args:
		find_usage()

	long = False
	filetype, start, end, channel = None, None, None, None
	for opt, arg in opts:
		if opt == '-l':
			long = True
		if opt == '-i':
			if filetype is not None:
				find_usage()
			filetype = FileType.IMAGE
		if opt == '-v':
			if filetype is not None:
				find_usage()
			filetype = FileType.VIDEO
		if opt == '-s':
			start = dateparse(arg)
			if start is None:
				find_usage()
		if opt == '-e':
			end = dateparse(arg)
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
		start = EPOCH + RESOLUTION
	if end is None:
		end = datetime.now()

	for file in conn.search(start=start,
	                        end=end,
	                        channel=channel,
	                        type=filetype):
		if long:
			print('{} {} {} {} {:7}K {}'
			      .format(file.disk, file.part,
			              file.start.isoformat(),
			              file.end.isoformat(),
			              file.length,
			              file.name))
		else:
			print(file.name)


def run_cat(conn: DVRIPClient, sock: Socket, args: List[str]) -> None:
	if len(args) != 1:
		print('Usage: {} ... cat FILENAME'.format(prog()),
		      file=stderr)
		exit(EX_USAGE)
	name, = args
	try:
		file = conn.download(sock, name)
		copyfileobj(file, stdout.buffer)
	finally:
		sock.close()


def usage(code: int = EX_USAGE, file: TextIO = stderr) -> NoReturn:
	print('Usage: {} [-p PORT] [-u USERNAME] HOST COMMAND ...'
	      .format(prog()),
	      file=file)
	print(' where COMMAND is one of cat, info, find, reboot, or time',
	      file=file)
	exit(code)


def run(args: List[str] = argv[1:]) -> None:  # pylint: disable=dangerous-default-value
	try:
		opts, args = getopt(args, 'hp:u:')
	except GetoptError:
		usage()
	if len(args) < 2:
		usage()
	host, command, *args = args
	if not all(c.isalnum() or c == '-' for c in command):
		usage()

	port = environ.get('DVR_PORT', '34567')
	username = environ.get('DVR_USERNAME', 'admin')
	for opt, arg in opts:
		if opt == '-p':
			port = arg
		if opt == '-u':
			username = arg
		if opt == '-h':
			if len(opts) != 1:
				usage()
			usage(0, file=stdout)

	password = environ.get('DVR_PASSWORD', None)
	if password is None:
		try:
			password = getpass('Password: ')
		except EOFError:
			exit(EX_IOERR)

	if command == 'cat':
		addr = resolve(host, port)
		sock = Socket(AF_INET, SOCK_STREAM)
		try:
			sock.connect(addr)
		except OSError as e:
			ioerr(e)
		conn = connect(addr, username, password)
		try:
			run_cat(conn, sock, args)
		finally:
			conn.logout()
	elif command == 'info':
		conn = connect(resolve(host, port), username, password)
		try:
			run_info(conn, args)
		finally:
			conn.logout()
	elif command == 'find':
		conn = connect(resolve(host, port), username, password)
		try:
			run_find(conn, args)
		finally:
			conn.logout()
	elif command == 'reboot':
		conn = connect(resolve(host, port), username, password)
		conn.reboot()
	elif command == 'time':
		conn = connect(resolve(host, port), username, password)
		try:
			run_time(conn, args)
		finally:
			conn.logout()
	else:
		usage()


if __name__ == '__main__':
	run()
