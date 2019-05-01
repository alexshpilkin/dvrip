try:
	# For distributions
	from ._version_lock import version  # type: ignore # pylint: disable=unused-import
except ImportError:
	# For development trees
	from os import environ
	from os.path import dirname, join

	try:
		from dulwich.porcelain import describe  # type: ignore
	except ImportError:
		from subprocess import SubprocessError, run
		from warnings import warn

		def describe(repo):
			env = dict(environ)
			env['GIT_DIR'] = repo
			try:
				return (run(['git', 'describe'],
				             capture_output=True,
				             check=True,
				             env=env,
				             encoding='ascii')
				            .stdout.rstrip('\n'))
			except SubprocessError as e:  # pragma: no cover
				warn("Could not determine dvrip version: {}"
				     .format(e))
				return '0.0.0-0-unknown'

	if '_repo' not in globals():  # except for setup.py
		_repo = join(dirname(dirname(__file__)), '.git')
	_desc = describe(_repo).split('-', 3)
	version = ('{0}.dev{1}+{2}'.format(*_desc)
	           if len(_desc) == 3 else _desc[0])
