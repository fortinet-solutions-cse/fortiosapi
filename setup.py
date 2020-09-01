#!/usr/bin/env python

from setuptools import setup, find_packages

with open('README.md') as fh:
    long_description = fh.read()

setup(
    name='fortiosapi',
    version='1.0.5',
    description="Python modules to use Fortigate APIs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    # Valid Classifiers are here:
    # https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python ',
        'Topic :: Security',
    ],
    keywords='Fortinet fortigate fortios rest api',
    packages=find_packages(),
    install_requires=['requests', 'paramiko', 'oyaml'],
    author='Nicolas Thomas',
    author_email='nthomas@fortinet.com',
    url='https://github.com/fortinet-solutions-cse/fortiosapi',
    include_package_data=True,
)
