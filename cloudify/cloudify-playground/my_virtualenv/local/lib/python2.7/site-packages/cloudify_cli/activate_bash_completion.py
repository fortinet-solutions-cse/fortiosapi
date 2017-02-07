########
# Copyright (c) 2013 GigaSpaces Technologies Ltd. All rights reserved
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

import platform
import subprocess
from getpass import getuser
from sys import executable
from os.path import expanduser, dirname
import sys

__author__ = 'nir'


def main():
    try:
        distro = platform.dist()[0]
        print 'distribution identified: {0}'.format(distro)
    except:
        sys.exit('failed to retrieve os distribution')

    if distro in ('Ubuntu', 'debian'):
        user = getuser()
        home = expanduser("~")
        intd = dirname(executable)

        print 'adding bash completion for user {0}, in {1}'.format(user, intd)
        cmd_check_if_registered = ('grep "{0}/register-python-argcomplete '
                                   'cfy" {1}/.bashrc')
        x = subprocess.Popen(cmd_check_if_registered.format(intd, home),
                             shell=True,
                             stdout=subprocess.PIPE)
        output = x.communicate()[0]
        if output == '':
            print 'adding autocomplete to ~/.bashrc'
            cmd_register_to_bash = ('''echo 'eval "$({0}/register-python-argcomplete cfy)"' >> {1}/.bashrc''')  # NOQA
            subprocess.Popen(cmd_register_to_bash.format(intd, home),
                             shell=True,
                             stdout=subprocess.PIPE)
            try:
                print 'attempting to source bashrc'
                execfile('{0}/.bashrc'.format(home))
            except:
                print 'could not source bashrc'
            print 'if cfy autocomplete doesn\'t work, reload your shell or run ". ~/.bashrc'  # NOQA
        else:
            print 'autocomplete already installed'
    elif platform.dist()[0] == 'Windows':
        return
    elif platform.dist()[0] == 'CentOS':
        return
    elif platform.dist()[0] == 'openSUSE':
        return
    else:
        sys.exit('your distribution ({0}) is not supported.'
                 ' could not complete activation.'
                 .format(distro))

if __name__ == '__main__':
    main()
