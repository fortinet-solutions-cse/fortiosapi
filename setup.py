#!/usr/bin/env python

import setuptools

with open('README.md') as fh:
    long_description = fh.read()

setuptools.setup(
    name='fortiosapi',
    version='0.10.7',
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
    packages=setuptools.find_packages(),
    author='Nicolas Thomas',
    author_email='nthomas@fortinet.com',
    url='https://github.com/fortinet-solutions-cse/fortiosapi',
    include_package_data=True,
)
