
## fortiosAPI Overview


Opensource python library to configure Fortigate/Fortios devices (Fortigate REST API)

### Ready for config management.
Compare to the REST API there a few add-ons:
 In addition to get,put,post,delete methods there is a set which will
 try to post and if failing will put and collect the mkey directly.
 The lib will also find the mkey for you 
 

### Examples



You can find and propose examples here: https://github.com/fortinet-solutions-cse/fortiosapi-examples 
Separated to avoid cluttering those who integrate the fortiosapi module.

 

### New overlay configuration

You now have an overlayconfig call which can be pass a complex configuration change in yaml. 
Including multiple endpoints (name/path) as the simple example below shows:
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

The behaviour is to change the parameters at the higher level in the CMDB tree first then do a serie of set on the tables.

Will fail if one of the set fails. 

Order in the yaml is preserved.

### Login methods
User/password

Token (api key) documented in the Fortigate API Spec that you can find if having an account on http://fndn.fortinet.net/

### Multi vdom
In multi vdom environment use vdom=global in the API call.
As it is a reserved word the API will switch to use the global=1 and
take care of the differences in the repsonses.

### Schema
There is a get_schema call and an example to get the schema of the
differents methods to ease writting them.

### License (5.6)
A rest call to check and force license validation check starting with 5.6
See license.
usage of schema and mkey for every call for 5.6 

License validity is now checked at login 

### Versions


### Test driven development
In tests folder you will find a tox based set of tests as examples.
The test_fortiosapi_virsh need you to have virsh access, especially to the console.
This allow to perform actions automatically from the CLI and check API calls actual results.
Other tests are welcomed.

### Files upload/download
You will find the calls to exchange files (config, logs, licenses) with Fortigate in this LIB


### Known Usage
Fortiosapi library is used in Home-Assistant, Fortinet Ansible modules and in Cloudify plugins. 

Maintained mainly by Fortinet employees. 
