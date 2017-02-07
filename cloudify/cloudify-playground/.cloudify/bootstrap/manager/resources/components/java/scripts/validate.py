#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


java_result = utils.sudo(['java', '-version'], ignore_failures=True)
if java_result.returncode != 0:
    ctx.abort_operation('Java runtime error: java was not installed')
