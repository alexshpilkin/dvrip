from socket import AF_INET, SOCK_STREAM, socket as Socket
from sys import stderr
from typing import List, NoReturn
from ..io import DVRIPClient
from . import EX_USAGE, guard, prog_connect


def usage() -> NoReturn:
	print('Usage: {} info'.format(prog_connect()), file=stderr)
	exit(EX_USAGE)


def run(host: str,  # pylint: disable=too-many-branches,too-many-locals
        serv: int,
        username: str,
        password: str,
        args: List[str]
       ) -> None:
	if args:
		usage()

	conn = DVRIPClient(Socket(AF_INET, SOCK_STREAM))
	conn.connect((host, serv), username, password)

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
		print('disk {}:'.format(disk.number))  # disk group
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


def main() -> None:
	from sys import argv
	from . import host, serv, username, password

	if host() is None:
		usage()
	guard(run, host(), serv(), username(), password(), argv[1:])
