#!/usr/bin/env python

from setuptools import setup

setup(
      name='fortiosapi',
      version='0.5.2',
      description='Python modules to interact with fortinet products configuration rest and ssh',
      install_requires=['requests','paramiko'],
      author='Nicolas Thomas',
      author_email='nthomas@fortinet.com',
      url='https://github.com/thomnico/fortiosapi',
      packages=['fortiosapi'],
      )
