#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

MGMT_WORKER_SERVICE_NAME = 'mgmtworker'
CELERY_PATH = '/opt/mgmtworker/env/bin/celery'  # also hardcoded in create


@utils.retry(ValueError)
def check_worker_running():
    """Use `celery status` to check if the worker is running."""
    result = utils.sudo([
        'CELERY_WORK_DIR=/opt/mgmtworker/work',
        CELERY_PATH,
        '--config=cloudify.broker_config',
        'status'
    ], ignore_failures=True)
    if result.returncode != 0:
        raise ValueError('celery status: worker not running')


ctx.logger.info('Starting Management Worker Service...')
utils.start_service(MGMT_WORKER_SERVICE_NAME)

utils.systemd.verify_alive(MGMT_WORKER_SERVICE_NAME)

try:
    check_worker_running()
except ValueError:
    ctx.abort_operation('Celery worker failed to start')
