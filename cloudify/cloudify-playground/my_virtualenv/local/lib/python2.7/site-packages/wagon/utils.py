########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

import os
import re
import sys
import time
import json
import shutil
import urllib
import tarfile
import zipfile
import logging
import platform
import tempfile
import subprocess
import pkg_resources
from threading import Thread
from contextlib import closing

from wheel import pep425tags as wheel_tags

from . import logger, codes


DEFAULT_INDEX_SOURCE_URL = 'https://pypi.python.org/pypi/{0}/json'
IS_VIRTUALENV = hasattr(sys, 'real_prefix')

PLATFORM = sys.platform
IS_WIN = (os.name == 'nt')
IS_DARWIN = (PLATFORM == 'darwin')
IS_LINUX = PLATFORM.startswith('linux')

PROCESS_POLLING_INTERVAL = 0.1

lgr = logger.init()


class PipeReader(Thread):
    def __init__(self, fd, proc, logger, log_level):
        Thread.__init__(self)
        self.fd = fd
        self.proc = proc
        self.logger = logger
        self.log_level = log_level
        self.aggr = ''

    def run(self):
        while self.proc.poll() is None:
            output = self.fd.readline()
            if len(output) > 0:
                self.aggr += output
                self.logger.log(self.log_level, output.strip())
            else:
                time.sleep(PROCESS_POLLING_INTERVAL)


# TODO: implement using sh
def run(cmd, suppress_errors=False, suppress_output=False):
    """Executes a command
    """
    lgr.debug('Executing: {0}...'.format(cmd))
    pipe = subprocess.PIPE
    proc = subprocess.Popen(cmd, shell=True, stdout=pipe, stderr=pipe)

    stderr_log_level = logging.NOTSET if suppress_errors else logging.ERROR
    stdout_log_level = logging.NOTSET if suppress_errors else logging.DEBUG

    stdout_thread = PipeReader(proc.stdout, proc, lgr, stdout_log_level)
    stderr_thread = PipeReader(proc.stderr, proc, lgr, stderr_log_level)

    stdout_thread.start()
    stderr_thread.start()

    while proc.poll() is None:
        time.sleep(PROCESS_POLLING_INTERVAL)

    stdout_thread.join()
    stderr_thread.join()

    proc.aggr_stdout = stdout_thread.aggr
    proc.aggr_stderr = stderr_thread.aggr

    return proc


def wheel(package, requirement_files=False, wheels_path='package',
          excluded_packages=None, wheel_args=None, no_deps=False):
    lgr.info('Downloading Wheels for {0}...'.format(package))
    pip_executable = _get_pip_path(os.environ.get('VIRTUAL_ENV'))
    wheel_cmd = [pip_executable, 'wheel']
    wheel_cmd.append('--wheel-dir={0}'.format(wheels_path))
    wheel_cmd.append('--find-links={0}'.format(wheels_path))
    if no_deps:
        wheel_cmd.append('--no-deps')
    if requirement_files:
        wheel_cmd_with_reqs = wheel_cmd
        for req_file in requirement_files:
            wheel_cmd_with_reqs.extend(['-r', req_file])
        process = run(' '.join(wheel_cmd_with_reqs))
        if not process.returncode == 0:
            lgr.error('Could not download wheels for: {0} ({1})'.format(
                req_file, process.aggr_stderr))
            sys.exit(codes.errors['failed_to_wheel'])
    if wheel_args:
        wheel_cmd.append(wheel_args)
    wheel_cmd.append(package)
    process = run(' '.join(wheel_cmd))
    if not process.returncode == 0:
        lgr.error('Could not download wheels for: {0} ({1})'.format(
            package, process.aggr_stderr))
        sys.exit(codes.errors['failed_to_wheel'])
    wheels = get_downloaded_wheels(wheels_path)
    excluded_packages = excluded_packages or []
    excluded_wheels = []
    for package in excluded_packages:
        wheel = get_wheel_for_package(wheels_path, package)
        if wheel:
            excluded_wheels.append(wheel)
            wheels.remove(wheel)
            os.remove(os.path.join(wheels_path, wheel))
        else:
            lgr.warn('Wheel not found for: {0}. Could not exclude.'.format(
                package))
    return wheels, excluded_wheels


def get_wheel_for_package(wheels_path, package):
    for wheel in os.listdir(wheels_path):
        if wheel.startswith(package.replace('-', '_')):
            return wheel


def install_package(package, wheels_path, virtualenv=None,
                    requirements_file=None, upgrade=False,
                    install_args=None):
    """This will install a Python package.

    Can specify a specific version.
    Can specify a prerelease.
    Can specify a virtualenv to install in.
    Can specify a list of paths or urls to requirement txt files.
    Can specify a local wheels_path to use for offline installation.
    Can request an upgrade.
    """
    # install_args = install_args or []

    lgr.info('Installing {0}...'.format(package))
    pip_executable = _get_pip_path(virtualenv)
    pip_cmd = [pip_executable, 'install']
    if requirements_file:
        pip_cmd.extend(['-r', requirements_file])
    if install_args:
        pip_cmd.append(install_args)
    pip_cmd.append(package)
    pip_cmd.extend(['--use-wheel', '--no-index', '--find-links', wheels_path])
    # pre allows installing both prereleases and regular releases depending
    # on the wheels provided.
    pip_cmd.append('--pre')
    if upgrade:
        pip_cmd.append('--upgrade')
    if IS_VIRTUALENV and not virtualenv:
        lgr.info('Installing within current virtualenv: {0}...'.format(
            IS_VIRTUALENV))
    result = run(' '.join(pip_cmd))
    if not result.returncode == 0:
        lgr.error(result.aggr_stdout)
        lgr.error('Could not install package: {0}.'.format(package))
        sys.exit(codes.errors['failed_to_install_package'])


def get_downloaded_wheels(wheels_path):
    """Returns a list of a set of wheel files.
    """
    return [f for f in os.listdir(wheels_path) if f.endswith('whl')]


def download_file(url, destination):
    lgr.info('Downloading {0} to {1}...'.format(url, destination))
    final_url = urllib.urlopen(url).geturl()
    if final_url != url:
        lgr.debug('Redirected to {0}'.format(final_url))
    f = urllib.URLopener()
    f.retrieve(final_url, destination)


def zip(source, destination):
    lgr.info('Creating zip archive: {0}...'.format(destination))
    with closing(zipfile.ZipFile(destination, 'w')) as zip:
        for root, _, files in os.walk(source):
            for f in files:
                file_path = os.path.join(root, f)
                source_dir = os.path.dirname(source)
                zip.write(file_path, os.path.relpath(file_path, source_dir))


def unzip(archive, destination):
    lgr.debug('Extracting zip {0} to {1}...'.format(archive, destination))
    with closing(zipfile.ZipFile(archive, "r")) as zip:
        zip.extractall(destination)


def tar(source, destination):
    lgr.info('Creating tar.gz archive: {0}...'.format(destination))
    with closing(tarfile.open(destination, "w:gz")) as tar:
        tar.add(source, arcname=os.path.basename(source))


def untar(archive, destination):
    """Extracts files from an archive to a destination folder.
    """
    lgr.debug('Extracting tar.gz {0} to {1}...'.format(archive, destination))
    with closing(tarfile.open(name=archive)) as tar:
        files = [f for f in tar.getmembers()]
        tar.extractall(path=destination, members=files)


def get_wheel_tags(wheel_name):
    filename, _ = os.path.splitext(os.path.basename(wheel_name))
    return filename.split('-')


def get_platform_from_wheel_name(wheel_name):
    """Extracts the platform of a wheel from its file name.
    """
    return get_wheel_tags(wheel_name)[-1]


def get_platform_for_set_of_wheels(wheels_path):
    """For any set of wheel files, extracts a single platform.

    Since a set of wheels created or downloaded on one machine can only
    be for a single platform, if any wheel in the set has a platform
    which is not `any`, it will be used. If a platform other than
    `any` was not found, `any` will be assumed.
    """
    for wheel in get_downloaded_wheels(wheels_path):
        platform = get_platform_from_wheel_name(
            os.path.join(wheels_path, wheel))
        if platform != 'any':
            return platform
    return 'any'


def get_python_version():
    version = sys.version_info
    return 'py{0}{1}'.format(version[0], version[1])


def get_platform():
    return wheel_tags.get_platform()


def get_os_properties():
    return platform.linux_distribution(full_distribution_name=False)


def _get_env_bin_path(env_path):
    """Returns the bin path for a virtualenv

    This provides a fallback for a race condition in which you're trying
    to use the script and create a virtualenv from within
    a virtualenv in which virtualenv isn't installed and so
    is not importable.
    """
    try:
        import virtualenv
        return virtualenv.path_locations(env_path)[3]
    except ImportError:
        return os.path.join(env_path, 'scripts' if IS_WIN else 'bin')


def _get_pip_path(virtualenv=None):
    if virtualenv:
        return os.path.join(
            _get_env_bin_path(virtualenv),
            'pip.exe' if IS_WIN else 'pip')
    else:
        return os.path.join(
            os.path.dirname(sys.executable),
            'Scripts' if IS_WIN else '',
            'pip.exe' if IS_WIN else 'pip')


def check_installed(package, virtualenv):
    """Checks to see if a package is installed within a virtualenv.
    """
    pip_executable = _get_pip_path(virtualenv)
    p = run('{0} freeze'.format(pip_executable), suppress_output=True)
    if re.search(r'{0}'.format(package), p.aggr_stdout.lower()):
        lgr.debug('Package {0} is installed in {1}'.format(
            package, virtualenv))
        return True
    lgr.debug('Package {0} is not installed in {1}'.format(
        package, virtualenv))
    return False


def make_virtualenv(virtualenv_dir):
    """This will create a virtualenv.
    """
    lgr.debug('Creating Virtualenv {0}...'.format(virtualenv_dir))
    result = run('virtualenv {0}'.format(virtualenv_dir))
    if not result.returncode == 0:
        lgr.error('Could not create virtualenv: {0}'.format(virtualenv_dir))
        sys.exit(codes.errors['failed_to_create_virtualenv'])


def get_package_version_from_pypi(source):
    pypi_url = DEFAULT_INDEX_SOURCE_URL.format(source)
    lgr.debug('Getting metadata for {0} from {1}...'.format(
        source, pypi_url))
    try:
        package_data = json.loads(urllib.urlopen(pypi_url).read())
    except Exception as ex:
        lgr.error('Failed to retrieve package info from index'
                  ' ({0})'.format(str(ex)))
        sys.exit(codes.errors['failed_to_retrieve_index_info'])
    return package_data['info']['version']


def get_package_version_from_wheel_name(source):
    tmpdir = tempfile.mkdtemp()
    try:
        wheels, _ = wheel(source, wheels_path=tmpdir, no_deps=True)
        wheel_version = get_wheel_tags(wheels[0])[1]
        return wheel_version
    except Exception as ex:
        lgr.error('Failed to retrieve package version from '
                  'wheel file ({0}).'.format(str(ex)))
        sys.exit(codes.errors['failed_retrieve_version_from_wheel'])
    finally:
        shutil.rmtree(tmpdir)


def get_wagon_version():
    return pkg_resources.get_distribution('wagon').version
