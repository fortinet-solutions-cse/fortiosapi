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
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
############

# Install Cloudify on Debian and Ubuntu
# apt-get update
# apt-get install -y curl
# curl -O -L http://gigaspaces-repository-eu.s3.amazonaws.com/org/cloudify3/get-cloudify.py && python get-cloudify.py -f  # NOQA

# Install Cloudify on Arch Linux
# pacman -Syu --noconfirm
# pacman-db-upgrade
# pacman -S python2 --noconfirm
# curl -O -L http://gigaspaces-repository-eu.s3.amazonaws.com/org/cloudify3/get-cloudify.py && python2 get-cloudify.py -f # NOQA

# Install Cloudify on CentOS/RHEL
# yum -y update
# yum groupinstall -y development
# yum install -y zlib-dev openssl-devel sqlite-devel bzip2-devel wget gcc tar
# wget http://www.python.org/ftp/python/2.7.6/Python-2.7.6.tgz
# tar -xzvf Python-2.7.6.tgz
# cd Python-2.7.6
# ./configure --prefix=/usr/local && make && make altinstall
# curl -O -L http://gigaspaces-repository-eu.s3.amazonaws.com/org/cloudify3/get-cloudify.py && python2.7 get-cloudify.py -f # NOQA

# Install Cloudify on Windows (Python 32/64bit)
# Install Python 2.7.x 32/64bit from https://www.python.org/downloads/release/python-279/  # NOQA
# Make sure that when you install, you choose to add Python to the system path.
# Download http://gigaspaces-repository-eu.s3.amazonaws.com/org/cloudify3/get-cloudify.py to any directory  # NOQA
# Run python get-cloudify.py -f


import sys
import subprocess
import argparse
import platform
import os
import urllib
import struct
import tempfile
import logging
import shutil
import time
import tarfile
from threading import Thread

# Future proofing for python 3.4+ - imp is being deprecated, but importlib
# does not have all required functions in 2.7
import importlib
if not hasattr(importlib, 'find_loader'):
    import imp

version = (2, 0, 0)
version_str = '.'.join(str(ver) for ver in version)

DESCRIPTION = '''This script installs Cloudify's CLI on Linux,
Windows (with Python32 AND 64), and OS X (Darwin).
On the linux front, it supports Debian/Ubuntu, CentOS/RHEL and Arch.

Note that the script attempts to not be instrusive by forcing the user
to explicitly declare installation of various dependencies.

Installations are supported for both system python, the currently active
virtualenv and a declared virtualenv (using the --virtualenv flag).

If you're already running the script from within a virtualenv and you're not
providing a --virtualenv path, Cloudify will be installed within the virtualenv
you're in.

The script allows you to install requirement txt files when installing from
--source (or with --use-branch).
If --with-requirements is provided with a value (a URL or path to
a requirements file) it will use it. If it's provided without a value, it
will try to download the archive provided in --source or extrapolated from
--use-branch, extract it, and look for dev-requirements.txt and
requirements.txt files within it.

The script will attempt to install all necessary requirements including
python-dev and gcc (for Fabric on Linux), pycrypto (for Fabric on Windows),
pip and virtualenv (if --virtualenv was specified) depending on the OS and
Distro you're running on if requested with --install-pythondev or
--install-pycrypto, or if called with --force.
Note that to install certain dependencies (like pip or pythondev), you must
run the script as sudo, or (NOT RECOMMENDED) as root.

It's important to note that even if you're running as sudo, if you're
installing in a declared virtualenv, the script will drop the root privileges
since you probably declared a virtualenv so that it can be installed using
the current user.
Also note, that if you're running using sudo and wish to use a virtualenv you
must specify it with the --virtualenv argument as simply activating the env
will not cause it to be used while sudo is in use.

The script will use the interpreter that the script was run with as the path,
e.g. for creating virtualenvs, etc.

Please refer to Cloudify's documentation at http://getcloudify.org for
additional information.'''

IS_VIRTUALENV = hasattr(sys, 'real_prefix')

REQUIREMENT_FILE_NAMES = ['dev-requirements.txt', 'requirements.txt']

# TODO: put these in a private storage
repo = 'http://repository.cloudifysource.org/org/cloudify3/components'
PIP_URL = '{repo}/get-pip.py'.format(repo=repo)
PYCR64_URL = '{repo}/pycrypto-2.6.win-amd64-py2.7.exe'.format(repo=repo)
PYCR32_URL = '{repo}/pycrypto-2.6.win32-py2.7.exe'.format(repo=repo)

PLATFORM = sys.platform
IS_DARWIN = (PLATFORM == 'darwin')
IS_LINUX = (PLATFORM.startswith('linux'))
# Using os.name to allow cygwin to be detected as windows as well
IS_WIN = (os.name == 'nt')

PROCESS_POLLING_INTERVAL = 0.1

# defined below
logger = None


def _init_logger(logger_name):
    logger = logging.getLogger(logger_name)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(fmt='%(asctime)s [%(levelname)s] '
                                      '[%(name)s] %(message)s',
                                  datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def _exit(message, status):
    exit_codes = {
        'unsupported_platform': 200,
        'virtualenv_creation_failure': 210,
        'dependency_download_failure': 220,
        'dependency_extraction_failure': 221,
        'dependency_installation_failure': 222,
        'dependency_unsupported_on_distribution': 223,
        'cloudify_already_installed': 230,
    }

    logger.error(message)
    sys.exit(exit_codes[status])


def _run(cmd, suppress_errors=False):
    """Executes a command
    """
    logger.debug('Executing: {0}...'.format(cmd))
    pipe = subprocess.PIPE
    proc = subprocess.Popen(
        cmd, shell=True, stdout=pipe, stderr=pipe)

    stderr_log_level = logging.NOTSET if suppress_errors else logging.ERROR

    stdout_thread = _PipeReader(proc.stdout, proc, logger, logging.DEBUG)
    stderr_thread = _PipeReader(proc.stderr, proc, logger, stderr_log_level)

    stdout_thread.start()
    stderr_thread.start()

    while proc.poll() is None:
        time.sleep(PROCESS_POLLING_INTERVAL)

    stdout_thread.join()
    stderr_thread.join()

    proc.aggr_stdout = stdout_thread.aggr
    proc.aggr_stderr = stderr_thread.aggr

    return proc


def _is_root():
    return os.getuid() == 0


def _drop_root_privileges():
    """Drop root privileges

    This is used so that when installing cloudify within a virtualenv
    using sudo, the default behavior will not be to install using sudo
    as a virtualenv is created especially so that users don't have to
    install in the system Python or using a sudoer.
    """
    # maybe we're not root
    if not _is_root():
        return

    logger.info('Dropping root permissions...')
    os.setegid(int(os.environ.get('SUDO_GID', 0)))
    os.seteuid(int(os.environ.get('SUDO_UID', 0)))


def _make_virtualenv(virtualenv_dir, python_path):
    """This will create a virtualenv. If no `python_path` is supplied,
    will assume that `python` is in path. This default assumption is provided
    via the argument parser.
    """
    logger.info('Creating Virtualenv {0}...'.format(virtualenv_dir))
    result = _run('virtualenv -p {0} {1}'.format(python_path, virtualenv_dir))
    if not result.returncode == 0:
        logger.error(
            'Virtualenv creation output: {out}. '
            'Error output: {error}.'.format(
                out=result.aggr_stdout,
                error=result.aggr_stderr,
            )
        )
        _exit(
            message='Could not create virtualenv: {path}'.format(
                path=virtualenv_dir,
            ),
            status='virtualenv_creation_failure',
        )


def _install_package(package, version=False, pre=False, virtualenv_path=False,
                     requirement_files=None, upgrade=False,
                     pip_args=''):
    """This will install a Python package.

    Can specify a specific version.
    Can specify a prerelease.
    Can specify a virtualenv to install in.
    Can specify a list of paths or urls to requirement txt files.
    Can specify a local wheels path to use for offline installation.
    Can request an upgrade.
    """
    logger.info('Installing {0}...'.format(package))
    pip_cmd = ['pip', 'install']
    if pip_args is not None:
        pip_cmd.extend(pip_args.split())
    if virtualenv_path:
        pip_cmd[0] = os.path.join(
            _get_env_bin_path(virtualenv_path), pip_cmd[0])
    elif IS_VIRTUALENV:
        logger.info('Installing within current virtualenv.')
    if requirement_files:
        for req_file in requirement_files:
            pip_cmd.extend(['-r', req_file])
    package = '{0}=={1}'.format(package, version) if version else package
    pip_cmd.append(package)
    if pre:
        pip_cmd.append('--pre')
    if upgrade:
        pip_cmd.append('--upgrade')
    result = _run(' '.join(pip_cmd))
    if not result.returncode == 0:
        logger.error(result.aggr_stdout)
        _exit(
            message='Could not install package: {0}.'.format(package),
            status='dependency_installation_failure',
        )


def _untar_requirement_files(archive, destination):
    """This will extract requirement files from an archive.
    """
    with tarfile.open(name=archive) as tar:
        req_files = [req_file for req_file in tar.getmembers()
                     if os.path.basename(req_file.name)
                     in REQUIREMENT_FILE_NAMES]
        tar.extractall(path=destination, members=req_files)


def _download_file(url, destination):
    logger.info('Downloading {0} to {1}'.format(url, destination))
    final_url = urllib.urlopen(url).geturl()
    if final_url != url:
        logger.debug('Redirected to {0}'.format(final_url))
    f = urllib.URLopener()
    f.retrieve(final_url, destination)


def _get_os_props():
    distro, _, release = platform.linux_distribution(
        full_distribution_name=False)
    return distro, release


def _get_env_bin_path(env_path):
    """returns the bin path for a virtualenv
    """
    # Not using virtualenv's path_locations due to potential race conditions.
    # Therefore we use just the fallback method to get reliable behaviour
    return os.path.join(env_path, 'scripts' if IS_WIN else 'bin')


# Underscored as not part of public interface
# Looks ugly, but is at least explicit
class _PipeReader(Thread):
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
                self.logger.log(self.log_level, output)
            else:
                time.sleep(PROCESS_POLLING_INTERVAL)


class ArgumentNotValidForOS(Exception):
    pass


class ArgumentCombinationInvalid(Exception):
    pass


class CloudifyInstaller():
    def __init__(self,
                 force=False,
                 upgrade=False,
                 virtualenv='',
                 version='',
                 pre=False,
                 source='',
                 with_requirements='',
                 pip_args='',
                 python_path=sys.executable,
                 install_pip=False,
                 install_virtualenv=False,
                 install_pythondev=False,
                 install_pycrypto=False,
                 os_distro=None,
                 os_release=None):
        self.force = force
        self.upgrade = upgrade
        self.virtualenv = virtualenv
        self.version = version
        self.pre = pre
        self.source = source
        self.with_requirements = with_requirements
        self.pip_args = pip_args
        self.python_path = python_path
        self.install_pip = install_pip
        self.install_virtualenv = install_virtualenv
        self.install_pythondev = install_pythondev
        self.install_pycrypto = install_pycrypto

        # When using the command line it should be impossible to reach these.
        # However, if importing this class to use elsewhere they can be, so
        # exceptions will be raised.
        if not IS_WIN and self.install_pycrypto:
            raise ArgumentNotValidForOS(
                'Pycrypto is only relevant on Windows.'
            )
        if not (IS_LINUX or IS_DARWIN) and self.install_pythondev:
            raise ArgumentNotValidForOS(
                'Pythondev is only relevant on Linux or OSX'
            )
        # This mutually exclusive check could use simplified logic, but that
        # would make the intent less clear
        if (
            (version and (pre or source)) or
            (pre and (version or source)) or
            (source and (version or pre))
        ):
            raise ArgumentCombinationInvalid(
                'Setting more than one of version, pre, and source '
                'is not supported.'
            )

        os_props = _get_os_props()
        self.distro = os_distro or os_props[0].lower()
        self.release = os_release or os_props[1].lower()

    def execute(self):
        """Installation Logic

        --force argument forces installation of all prerequisites.
        """
        logger.debug('Identified Platform: {0}'.format(PLATFORM))
        logger.debug('Identified Distribution: {0}'.format(self.distro))
        logger.debug('Identified Release: {0}'.format(self.release))

        package = self.source or 'cloudify'

        self.handle_upgrade()

        if self.force or self.install_pip:
            self.get_pip()

        if self.virtualenv:
            if self.force or self.install_virtualenv:
                self.get_virtualenv()
            env_bin_path = _get_env_bin_path(self.virtualenv)

        if IS_LINUX and (self.force or self.install_pythondev):
            self.get_pythondev(self.distro)
        if (IS_VIRTUALENV or self.virtualenv) and not IS_WIN:
            # drop root permissions so that installation is done using the
            # current user.
            _drop_root_privileges()
        if self.virtualenv:
            if not os.path.isfile(os.path.join(
                    env_bin_path, ('activate.bat' if IS_WIN else 'activate'))):
                _make_virtualenv(self.virtualenv, self.python_path)

        if IS_WIN and (self.force or self.install_pycrypto):
            self.get_pycrypto(self.virtualenv)

        # if with_requirements is not provided, this will be False.
        # if it's provided without a value, it will be a list.
        if isinstance(self.with_requirements, list):
            self.with_requirements = self.with_requirements \
                or self._get_default_requirement_files(self.source)

        _install_package(package=package,
                         version=self.version,
                         pre=self.pre,
                         pip_args=self.pip_args,
                         virtualenv_path=self.virtualenv,
                         requirement_files=self.with_requirements,
                         upgrade=self.upgrade)

        if self.virtualenv:
            activate_path = os.path.join(env_bin_path, 'activate')
            activate_command = \
                '{0}.bat'.format(activate_path) if IS_WIN \
                else 'source {0}'.format(activate_path)
            logger.info('You can now run: "{0}" to activate '
                        'the Virtualenv.'.format(activate_command))

    def is_installed(self, module):
        if hasattr(importlib, 'find_loader'):
            found = importlib.find_loader(module)
        else:
            try:
                found = imp.find_module(module)
            except ImportError:
                found = False
        # Coerce result to boolean
        if found:
            return True
        else:
            return False

    def get_virtualenv(self):
        if not self.is_installed('virtualenv'):
            logger.info('Installing virtualenv...')
            _install_package('virtualenv', pip_args=self.pip_args)
        else:
            logger.info('virtualenv is already installed in the path.')

    def get_pip(self):
        if not self.is_installed('pip'):
            logger.info('Installing pip...')
            try:
                tempdir = tempfile.mkdtemp()
                get_pip_path = os.path.join(tempdir, 'get-pip.py')
                try:
                    _download_file(PIP_URL, get_pip_path)
                except StandardError as e:
                    _exit(
                        message='Failed pip download from {0}. ({1})'.format(
                            PIP_URL, e.message
                        ),
                        status='dependency_download_failure',
                    )
                result = _run('{0} {1}'.format(
                    self.python_path, get_pip_path))
                if not result.returncode == 0:
                    _exit(
                        message='Could not install pip',
                        status='dependency_installation_failure',
                    )
            finally:
                shutil.rmtree(tempdir)
        else:
            logger.info('pip is already installed in the path.')

    @staticmethod
    def _get_default_requirement_files(source):
        if os.path.isdir(source):
            return [os.path.join(source, f) for f in REQUIREMENT_FILE_NAMES
                    if os.path.isfile(os.path.join(source, f))]
        else:
            tempdir = tempfile.mkdtemp()
            archive = os.path.join(tempdir, 'cli_source')
            # TODO: need to handle deletion of the temp source dir
            try:
                _download_file(source, archive)
            except Exception as ex:
                _exit(
                    message='Could not download {0} ({1})'.format(
                        source, str(ex)),
                    status='dependency_download_failure',
                )
            try:
                _untar_requirement_files(archive, tempdir)
            except Exception as ex:
                _exit(
                    message='Could not extract {0} ({1})'.format(
                        archive, str(ex)),
                    status='dependency_extraction_failure',
                )
            finally:
                os.remove(archive)
            # GitHub always adds a single parent directory to the tree.
            # TODO: look in parent dir, then one level underneath.
            # the GitHub style tar assumption isn't a very good one.
            req_dir = os.path.join(tempdir, os.listdir(tempdir)[0])
            return [os.path.join(req_dir, f) for f in REQUIREMENT_FILE_NAMES
                    if os.path.isfile(os.path.join(req_dir, f))]

    def get_pythondev(self, distro):
        """Installs python-dev and gcc

        This will try to match a command for your platform and distribution.
        """
        logger.info('Installing python-dev...')
        if distro in ('ubuntu', 'debian'):
            cmd = 'apt-get install -y gcc python-dev'
        elif distro in ('centos', 'redhat', 'fedora'):
            cmd = 'yum -y install gcc python-devel'
        elif os.path.isfile('/etc/arch-release'):
            # Arch doesn't require a python-dev package.
            # It's already supplied with Python.
            cmd = 'pacman -S gcc --noconfirm'
        elif IS_DARWIN:
            logger.info('python-dev package not required on Darwin.')
            return
        else:
            _exit(
                message='python-dev package installation not supported '
                        'in current distribution.',
                status='dependency_unsupported_on_distribution',
            )
        _run(cmd)

    # Windows only
    def get_pycrypto(self, virtualenv_path):
        """This will install PyCrypto to be used by Fabric.
        PyCrypto isn't compiled with Fabric on Windows by default thus it needs
        to be provided explicitly.
        It will attempt to install the 32 or 64 bit version according to the
        Python version installed.
        """
        # check 32/64bit to choose the correct PyCrypto installation
        is_pyx32 = True if struct.calcsize("P") == 4 else False

        logger.info('Installing PyCrypto {0}bit...'.format(
            '32' if is_pyx32 else '64'))
        # easy install is used instead of pip as pip doesn't handle windows
        # executables.
        cmd = 'easy_install {0}'.format(PYCR32_URL if is_pyx32 else PYCR64_URL)
        if virtualenv_path:
            cmd = os.path.join(_get_env_bin_path(virtualenv_path), cmd)
        _run(cmd)

    def handle_upgrade(self):
        if self.check_cloudify_installed():
            logger.info('Cloudify is already installed in the path.')
            if self.upgrade:
                logger.info('Upgrading...')
            else:
                logger.warn('If your previous attempt to install failed, '
                            'cloudify may be partially installed. You can '
                            "'upgrade' to fix this.")
                _exit(
                    message='Use the --upgrade flag to upgrade.',
                    status='cloudify_already_installed',
                )

    def check_cloudify_installed(self):
        if self.virtualenv:
            result = _run(
                os.path.join(_get_env_bin_path(self.virtualenv),
                             'python -c "import cloudify"'),
                suppress_errors=True)
            return result.returncode == 0
        else:
            return self.is_installed('cloudify')


def parse_args(args=None):
    class VerifySource(argparse.Action):
        def __call__(self, parser, args, values, option_string=None):
            if not args.source and not args.use_branch:
                parser.error('--source or --use-branch is required when '
                             'calling with --with-requirements.')
            setattr(args, self.dest, values)

    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # Used it --use-branch is specified
    repo_url = 'https://github.com/{user}/cloudify-cli/archive/{branch}.tar.gz'

    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose level logging to shell.',
    )
    verbosity_group.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Only print errors.',
    )

    version_group = parser.add_mutually_exclusive_group()
    version_group.add_argument(
        '--version',
        type=str,
        help='Attempt to install a specific version of Cloudify.',
    )
    version_group.add_argument(
        '--pre',
        action='store_true',
        help='Attempt to install the latest Cloudify Milestone.',
    )
    version_group.add_argument(
        '-s', '--source',
        type=str,
        help='Install from the provided URL or local path.',
    )
    version_group.add_argument(
        '-b', '--use-branch',
        type=str,
        help='Branch to use. Specified as either branch or user/branch. '
             'By default the user will be cloudify-cosmo. '
             'You will likely want --with-requirements when using this. '
             'This will result in installing from: {0}'.format(repo_url)
    )

    # Deprecated argument, used to print warning and allow us to cleanly
    # remove it in the future
    parser.add_argument(
        '--forceonline',
        action='store_true',
        help=argparse.SUPPRESS,
    )

    # Non group arguments
    parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='Force install any requirements (USE WITH CARE!).',
    )
    parser.add_argument(
        '-e', '--virtualenv',
        type=str,
        help='Path to a Virtualenv to install Cloudify in.',
    )
    # Deprecated argument, used to print warning and allow us to cleanly
    # remove it in the future
    parser.add_argument(
        '--pythonpath',
        help=argparse.SUPPRESS,
    )
    # Deprecated argument, used to print warning and allow us to cleanly
    # remove it in the future
    parser.add_argument(
        '--installpip',
        action='store_true',
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        '--install-pip',
        action='store_true',
        help='Attempt to install pip.',
    )
    # Deprecated argument, used to print warning and allow us to cleanly
    # remove it in the future
    parser.add_argument(
        '--installvirtualenv',
        action='store_true',
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        '--install-virtualenv',
        action='store_true',
        help='Attempt to install Virtualenv.',
    )
    # Deprecated argument, used to print warning and allow us to cleanly
    # remove it in the future
    parser.add_argument(
        '--withrequirements',
        nargs='*',
        help=argparse.SUPPRESS,
        action=VerifySource,
    )
    parser.add_argument(
        '-r', '--with-requirements',
        nargs='*',
        help='Install default or provided requirements file.',
        action=VerifySource,
    )
    parser.add_argument(
        '-u', '--upgrade',
        action='store_true',
        help='Upgrades Cloudify if already installed.',
    )
    parser.add_argument(
        '-p', '--pip-args',
        type=str,
        help='Additional arguments to supply to pip. These will be used for '
             'the duration of this script but will not apply when, e.g. '
             'bootstrapping cloudify. You will likely need to quote this if '
             'you are using more than one argument.',
    )
    parser.add_argument(
        '--get-version',
        action='version',
        version=version_str,
    )

    # OS dependent arguments
    if IS_LINUX:
        # Deprecated argument, used to print warning and allow us to cleanly
        # remove it in the future
        parser.add_argument(
            '--installpythondev',
            action='store_true',
            help=argparse.SUPPRESS,
        )
        parser.add_argument(
            '--install-pythondev',
            action='store_true',
            help='Attempt to install Python Developers Package.',
        )
    elif IS_WIN:
        # Deprecated argument, used to print warning and allow us to cleanly
        # remove it in the future
        parser.add_argument(
            '--installpycrypto',
            action='store_true',
            help=argparse.SUPPRESS,
        )
        parser.add_argument(
            '--install-pycrypto',
            action='store_true',
            help='Attempt to install PyCrypto.',
        )

    # Get args as a dict
    parsed_args = vars(parser.parse_args(args))

    # Handle deprecation warnings
    # TODO: It might be possible to generate the parser args automatically
    # from this, but that would require using the same actions for the
    # deprecated methods as the updated ones, which does not seem to be
    # possible with argparse short of defining the args from dicts, which
    # would also need to handle groups. This is probably only worth
    # investigating if we are deprecating args a lot of the time.
    # NOTE: Except where used in mutually exclusive groups, these will
    # override the new arguments. Given that the deprecated arguments are now
    # undocumented, this should only be a problem when someone is switching
    # from old to new args and puts different values for each.
    deprecations = {
        'withrequirements': 'with_requirements',
        'installvirtualenv': 'install_virtualenv',
        'installpip': 'install_pip',
        'pythonpath': 'python_path',
        'forceonline': 'force_online',
        'installpycrypto': 'install_pycrypto',
        'installpythondev': 'install_pythondev',
    }
    for deprecated, new_value in deprecations.items():
        if deprecated in parsed_args and parsed_args[deprecated]:
            # Make sure we use the value that was set
            parsed_args[new_value] = parsed_args[deprecated]
            # ...then complain:
            if deprecated == 'pythonpath':
                # Special case as pythonpath is being fully removed
                logger.warning(
                    '--pythonpath is deprecated. '
                    'To use a different interpreter, run this script with '
                    'your preferred interpreter and that interpreter will be '
                    'used.'
                )
            elif deprecated == 'forceonline':
                # Special case as we currently ignore this.
                # It will be removed below
                logger.warning(
                    '--forceonline is deprecated. '
                    'Online install is currently the only option, so this '
                    'argument will be ignored.'
                )
            else:
                logger.warning(
                    '--{depvar} is deprecated. Use --{newvar}. '
                    '--{depvar} will be removed in a future release.'.format(
                        depvar=deprecated.replace('_', '-'),
                        newvar=new_value.replace('_', '-'),
                    )
                )

    # Deprecated args should now be discarded
    for arg in deprecations.keys():
        if arg in parsed_args.keys():
            parsed_args.pop(arg)

    # force_online is currently meaningless and should be discarded
    if 'force_online' in parsed_args:
        parsed_args.pop('force_online')

    # Process branch selection, if applicable
    if parsed_args['use_branch']:
        user = 'cloudify-cosmo'
        branch = parsed_args['use_branch']
        if '/' in branch:
            if len(branch.split('/')) > 2:
                parser.error('--use-branch should be specified either as '
                             '<branch> or as <user>/<branch>. '
                             'Too many "/" found in arguments.')
            else:
                user, branch = parsed_args['use_branch'].split('/')

        # Form source string from user and branch
        url = repo_url.format(user=user, branch=branch)

        parsed_args['source'] = url

    # use_branch should be discarded now as it is just used to set source
    parsed_args.pop('use_branch')

    if parsed_args['source'] and not parsed_args['with_requirements']:
        logger.warning(
            'A source URL or branch was specified, but '
            '--with-requirements was omitted. You may need to retry using '
            '--with-requirements if the installation fails.'
        )
    return parsed_args


def main():
    if not (IS_LINUX or IS_DARWIN or IS_WIN):
        _exit(
            message='Platform {0} not supported.'.format(PLATFORM),
            status='unsupported_platform',
        )

    args = parse_args()
    if args['quiet']:
        logger.setLevel(logging.ERROR)
    elif args['verbose']:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    excluded_args = ['quiet', 'verbose']
    for arg in excluded_args:
        if arg in args:
            args.pop(arg)
    installer = CloudifyInstaller(**args)
    installer.execute()

logger = _init_logger(__file__)


if __name__ == '__main__':
    main()
