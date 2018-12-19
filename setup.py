#!/usr/bin/env python

from setuptools import setup


def readme():
    with open('README.md') as f:
        return f.read()


setup(
    name='fortiosapi',
    version='0.10.0',
    description=('Python modules to use Fortigate APIs'
                 'full configuration, monitoring, lifecycle rest and ssh'),
    long_description=readme(),
    # Valid Classifiers are here:
    # https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python ',
        'Topic :: Security',
    ],
    keywords='Fortinet fortigate fortios rest api',
    install_requires=['requests', 'paramiko', 'oyaml'],
    author='Nicolas Thomas',
    author_email='nthomas@fortinet.com',
    url='https://github.com/fortinet-solutions-cse/fortiosapi',
    include_package_data=True,
    packages=['fortiosapi'],
)
