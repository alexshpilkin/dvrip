#!/usr/bin/env python3

from os.path import exists, join
from setuptools import Command, setup   # type: ignore
from setuptools.command.build_py import build_py as _build_py  # type: ignore
from setuptools.command.egg_info import egg_info as _egg_info  # type: ignore
from setuptools.command.egg_info import manifest_maker as _manifest_maker  # type: ignore # pylint: disable=line-too-long
from setuptools.command.egg_info import write_file  # type: ignore
from setuptools.command.test import test as _test  # type: ignore
from setuptools.command.sdist import sdist as _sdist  # type: ignore
from shlex import split  # type: ignore
from sys import exit   # pylint: disable=redefined-builtin

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
			'--cov-report term:skip-covered',
			'--cov-report annotate',
		])

	def finalize_options(self):
		self.pytest_args = split(self.pytest_args)
		for package in self.distribution.packages or []:
			self.pytest_args.extend(['--cov', package])
		for module in self.distribution.py_modules or []:
			self.pytest_args.extend(['--cov', module + '.py'])
		for script in self.distribution.scripts or []:
			self.pytest_args.extend(['--cov', script])

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


# Workaround for pypa/setuptools#1064

def makever(cmd, pkgdir):
	cmd.mkpath(pkgdir)
	with open(join(pkgdir, '_version_lock.py'), 'w') as file:
		print('version = {!r}'.format(version), file=file)  # pylint: disable=undefined-variable

class sdist(_sdist):
	def make_release_tree(self, base_dir, files):
		super().make_release_tree(base_dir, files)
		for package in self.distribution.packages:
			if not self.dry_run:
				makever(self, join(base_dir, package))

class egg_info(_egg_info):
	def find_sources(self):
		# exact copy of setuptools, to override manifest_maker
		manifest_filename = join(self.egg_info, "SOURCES.txt")
		mm = manifest_maker(self.distribution)
		mm.manifest = manifest_filename
		mm.run()
		self.filelist = mm.filelist

class manifest_maker(_manifest_maker):
	def prune_file_list(self):
		super().prune_file_list()
		for package in self.distribution.packages:
			if not exists(join(package, '_version.py')):
				continue
			self.filelist.files.append(join(package, '_version_lock.py'))

	def write_manifest(self):
		# exact copy of setuptools except for no _repair() call
		files = [self._manifest_normalize(f)
		         for f in self.filelist.files]
		msg = "writing manifest file '%s'" % self.manifest
		self.execute(write_file, (self.manifest, files), msg)

class build_py(_build_py):
	def run(self):
		if not self.dry_run:
			for package in self.distribution.packages:
				if not exists(join(package, '_version.py')):
					continue
				makever(self, join(self.build_lib, package))
		super().run()


_repo = '.git'
exec(open('dvrip/_version.py').read())  # pylint: disable=exec-used

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
	version=version,  # type: ignore  # pylint: disable=undefined-variable
	author='Alexander Shpilkin',
	author_email='ashpilkin@gmail.com',
	description=title,
	long_description=readme,
	long_description_content_type='text/x-rst',
	url='https://github.com/alexshpilkin/dvrip',
	classifiers=[
		'Development Status :: 2 - Pre-Alpha',
		'Intended Audience :: Developers',
		'Intended Audience :: System Administrators',
		'License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication',
		'Operating System :: OS Independent',
		'Programming Language :: Python',
		'Programming Language :: Python :: 3',
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
	scripts=['dvrip_test'],
	entry_points={
		'console_scripts': [
			'dvr = dvrip.__main__:run',
		],
	},
	include_package_data = True,
	exclude_package_data = {
		'': [
			'.coveragerc',
			'pylintrc',
			'pytest.ini',
			'test_*.py',
		],
	},

	python_requires='>=3.7, <4',
	install_requires=[
		'typing_inspect >=0.4, <0.5',
	],
	extras_require={
		'dvr-find': ['dateparser', 'humanize'],
		'dvr-time': ['dateparser'],
	},
	tests_require=[
		'hypothesis',
		'mock',
		'mypy >=0.700',
		'pylint >=2.3.0',
		'pytest',
		'pytest-cov',
		'typing_extensions',
	],

	cmdclass={
		'build_py': build_py,
		'egg_info': egg_info,
		'lint': pylint,
		'sdist': sdist,
		'test': test,
		'type': mypy,
	},
)
