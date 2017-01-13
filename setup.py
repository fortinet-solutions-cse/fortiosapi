#!/usr/bin/env python

from setuptools import setup

setup(
      name='fortigateconf',
      version='0.4.3',
      description='Python modules to interact with Fortigate configuration rest and ssh',
      install_requires=['requests','paramiko'],
      author='Nicolas Thomas',
      author_email='nthomas@fortinet.com',
      url='https://github.com/thomnico/fortigateconf',
      packages=['fortigateconf'],
      )
