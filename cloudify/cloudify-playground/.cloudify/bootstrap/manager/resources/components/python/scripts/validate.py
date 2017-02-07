#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


pip_result = utils.sudo(['pip'], ignore_failures=True)
if pip_result.returncode != 0:
    ctx.abort_operation('Python runtime installation error: '
                        'pip was not installed')
