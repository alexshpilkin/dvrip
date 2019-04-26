#!/usr/bin/env python3

from setuptools               import setup
from setuptools.command.sdist import sdist as SDist
from setuptools.command.test  import test as Test


class Lint(Test):
	user_options = \
		[('pylint-args=', 'l', 'Arguments to pass to pylint')]

	def initialize_options(self):
		super().initialize_options()
		self.pylint_args = ' '.join([
		])

	def run_tests(self):  # pytest: disable=redefined-builtin
		from shlex       import split
		from sys         import exit  # pylint: disable=redefined-builtin
		from pylint.lint import Run as pylint

		exit(pylint(split(self.pylint_args) + packages + scripts +
		            ['setup.py']))


class CustomTest(Lint):
	user_options = \
		sorted(Lint.user_options +
		       [('pytest-args=', 't', 'Arguments to pass to pytest')],
		       key=lambda x: x[0])

	def initialize_options(self):
		super().initialize_options()
		self.pylint_args = ' '.join([
			'--disable fixme',
			self.pylint_args,
		])
		self.pytest_args = ' '.join([
			'-v',
			'--cov',
			'--cov-report term:skip-covered',
			'--cov-report annotate',
		])

	def run_tests(self):
		from shlex  import split
		from sys    import exit  # pylint: disable=redefined-builtin
		from pytest import main as pytest

		try:
			super().run_tests()
		except SystemExit as e:
			if e.code: raise
		exit(pytest(split(self.pytest_args)))


class CustomSDist(SDist):
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

packages=['dvrip']
scripts=['test_connect']

setup(
	name='dvrip',
	version='0.0.0',
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
		'Programming Language :: Python :: 3.5',
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

	packages=packages,
	scripts=scripts,
	python_requires='>=3.5, <4',
	install_requires=[],
	tests_require=['pylint', 'pytest', 'pytest-cov'],

	cmdclass={
		'lint':  Lint,
		'sdist': CustomSDist,
		'test':  CustomTest,
	},
)
