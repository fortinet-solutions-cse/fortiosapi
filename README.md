# fortiosAPI

Python library to configure Fortigate/Fortios devices (REST API and SSH)

## Ready for config management.
Compared to the REST API there a few add-ons:
 In addition to `get`, `put`, `post`, and `delete` methods there is a `set` which will
 try to POST and, on failure, will PUT and collect the mkey directly.
 The library will also find the mkey for you.

## New overlay configuration

You now have an `setoverlayconfig` call which takes a complex configuration change in yaml.
It can include multiple endpoints (name/path) as the simple example below shows:
```yaml
antivirus:
  profile:
    apisettree:
      "scan-mode": "quick"
      'http': {"options": "scan avmonitor",}
      "emulator": "enable"
firewall:
  policy:
    67:
      'name': "Testfortiosapi"
      'action': "accept"
      'srcintf': [{"name": "port1"}]
      'dstintf': [{"name": "port2"}]
      'srcaddr': [{"name": "all"}]
      'dstaddr': [{"name": "all"}]
      'schedule': "always"
      'service': [{"name": "HTTPS"}]
      "utm-status": "enable"
      "profile-type": "single"
      'av-profile': "apisettree"
      'profile-protocol-options': "default"
      'ssl-ssh-profile': "certificate-inspection"
      'logtraffic': "all"
```

The behaviour will be to change the parameters at the higher level first, then do a series of set on the tables.
Will fail if one of the set fails.
Order of commands should be preserved.

## Login methods
User/password

Token (API key) documented in the Fortigate API Spec that you can find if you have an account on http://fndn.fortinet.com/.

## Multi-VDOM
In multi-VDOM environment use `vdom=global` in the API call.
As it is a reserved word the API will switch to use `global=1` and
take care of the differences in the responses.

## Schema
There is a `get_schema` call and an example to get the schema of the
differents methods to ease writing them.

## License (5.6)
A rest call to check and force license validation check starting with 5.6
See license.
usage of schema and mkey for every call for 5.6

License validity is now checked at login

## Versions


## Test driven development
In tests folder you will find a tox based set of tests as examples.
The test_fortiosapi_virsh need you to have virsh access, especially to the console.
This allow to perform actions automatically from the CLI and check API calls actual results.
Other tests are welcomed.

## Files upload/download
You will find calls to exchange files (config, logs, licenses) with Fortigate in this library.


## Known Usage
Fortiosapi library is used in Fortinet Ansible modules and in Cloudify plugins.
It is maintained mainly by Fortinet employees.
