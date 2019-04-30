#!/usr/bin/env python3

from setuptools               import Command, setup   # type: ignore
from setuptools.command.test  import test as _test    # type: ignore
from setuptools.command.sdist import sdist as _sdist  # type: ignore
from shlex                    import split  # type: ignore
from sys                      import exit   # pylint: disable=redefined-builtin

# pylint: disable=attribute-defined-outside-init  # *_args are conventionally so


class mypy(Command):
	description = 'validate type annotations with mypy'
	user_options = [('mypy-args=', 'm', 'Arguments to pass to mypy')]

	def initialize_options(self):
		self.mypy_args = ' '.join([
		])

	def finalize_options(self):
		self.mypy_args = split(self.mypy_args)

	def run(self):
		from mypy.main import main as run_mypy
		for package in self.distribution.packages or []:
			run_mypy(None, self.mypy_args + ['--package', package])
		for module in self.distribution.py_modules or []:
			run_mypy(None, self.mypy_args + ['--module', module])
		for script in self.distribution.scripts or []:
			run_mypy(None, self.mypy_args + ['--', script])
		run_mypy(None, self.mypy_args + ['setup.py'])


class pytest(Command):
	description = 'run tests with pytest'
	user_options = [('pytest-args=', 't', 'Arguments to pass to pytest')]

	def initialize_options(self):
		self.pytest_args = ' '.join([
			'--cov',
			'--cov-report term:skip-covered',
			'--cov-report annotate',
		])

	def finalize_options(self):
		self.pytest_args = split(self.pytest_args)

	def run(self):
		from pytest import main as run_pytest  # type: ignore
		code = run_pytest(self.pytest_args)
		if code: exit(code)


class pylint(Command):
	description  = 'check for code standard violations with pylint'
	user_options = [('pylint-args=', 'l', 'Arguments to pass to pylint')]

	def initialize_options(self):
		self.pylint_args = ' '.join([
		])

	def finalize_options(self):
		self.pylint_args = split(self.pylint_args)
		if '--' not in self.pylint_args:
			self.pylint_args.append('--')
		self.pylint_args.extend(self.distribution.packages   or [])
		self.pylint_args.extend(self.distribution.py_modules or [])
		self.pylint_args.extend(self.distribution.scripts    or [])
		self.pylint_args.append('setup.py')

	def run(self):
		from pylint.lint import Run as run_pylint  # type: ignore
		try:
			run_pylint(self.pylint_args)
		except SystemExit as e:
			if e.code: raise


class test(_test, pylint, pytest, mypy):
	description  = 'run unit tests'
	user_options = sorted(mypy.user_options +
	                      pytest.user_options +
	                      pylint.user_options,
	                      key=lambda x: x[0])

	def initialize_options(self):
		for base in test.__bases__:
			base.initialize_options(self)
		self.pylint_args = ' '.join([
			'--disable fixme',
			self.pylint_args,
		])

	def finalize_options(self):
		for base in test.__bases__:
			base.finalize_options(self)

	def run_tests(self):
		for base in reversed(test.__bases__[1:]):
			base.run(self)


class sdist(_sdist):
	def initialize_options(self):
		super().initialize_options()
		self.formats = ['gztar', 'zip']


with open('README.rst', 'r') as fp:
	title = None
	for line in fp:
		if title is None:
			title = line
		if not line[:-1]:
			break
	readme = ''.join(line for line in fp)

setup(
	name='dvrip',
	version='0.0.1',
	author='Alexander Shpilkin',
	author_email='ashpilkin@gmail.com',
	description=title,
	long_description=readme,
	long_description_content_type='text/x-rst',
	url='https://github.com/alexshpilkin/hattifnatt',
	classifiers=[
		'Development Status :: 2 - Pre-Alpha',
		'Intended Audience :: Developers',
		'Intended Audience :: System Administrators',
		'License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication',
		'Operating System :: OS Independent',
		'Programming Language :: Python',
		'Programming Language :: Python :: 3',
		'Programming Language :: Python :: 3.6',
		'Programming Language :: Python :: 3.7',
		'Topic :: Communications',
		'Topic :: Internet',
		'Topic :: Multimedia :: Sound/Audio :: Capture/Recording',
		'Topic :: Multimedia :: Video :: Capture',
		'Topic :: Office/Business',
		'Topic :: Software Development :: Libraries :: Python Modules',
		'Topic :: Utilities',
	],

	packages=['dvrip'],
	scripts=['dvr', 'test_connect'],
	python_requires='>=3.6, <4',
	install_requires=[
		'typing_inspect >=0.4, <0.5'
	],
	tests_require=[
		'hypothesis',
		'mypy >=0.700',
		'pylint >=2.3',
		'pytest',
		'pytest-cov',
	],

	cmdclass={
		'lint':  pylint,
		'sdist': sdist,
		'test':  test,
		'type':  mypy,
	},
)
