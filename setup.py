#!/usr/bin/env python

from setuptools import setup


def readme():
    with open('README.md') as f:
        return f.read()

setup(
    name='fortiosapi',
    version='0.6',
    description='Python modules to interact with fortinet products configuration rest and ssh',
    long_description=readme(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache v2 License',
        'Programming Language :: Python ',
        'Topic :: Security :: Fortinet products management',
    ],
    keywords='Fortinet fortigate fortios rest api',
    install_requires=['requests', 'paramiko'],
    author='Nicolas Thomas',
    author_email='nthomas@fortinet.com',
    url='https://github.com/thomnico/fortiosapi',
    include_package_data=True,
    packages=['fortiosapi'],
)

