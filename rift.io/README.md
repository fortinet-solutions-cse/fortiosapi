lxc launch ubuntu:16.04 riftio-launchpad

Follow https://open.riftio.com/documentation/riftware/4.3/a/install/install-riftware-on-generic-system.htm
Run curl or wget to download the install-launchpad script. For example:

$ wget http://repo.riftio.com/releases/open.riftio.com/4.3.3/install-launchpad
Run the install-launchpad script.
apt install libxml2-dev libxslt-dev
$ bash install-launchpad
Installation can take several minutes, depending on your internet speed.

After the installation process completes, start the Launchpad service:

$ sudo systemctl start launchpad.service
