# fortiosAPI

Python library to configure Fortigate/Fortios devices (REST API and SSH)

## Ready for config management.
Compare to the REST API there a few add-ons:
 In addition to get,put,post,delete methods there is a set which will
 try to post and if failing will put and collect the mkey directly.

## Login methods
User/password
Token (api key)

## Multi vdom
In multi vdom environment use vdom=global in the API call.
As it is a reserved word the API will switch to use the global=1 and
take care of the differences in the repsonses.

## Schema
There is a get_schema call and an example to get the schema of the
differents methods to ease writting them.

## License (5.6)
A rest call to check and force license validation check starting with 5.6
See license.
usage of schema and mkey for every call for 5.6 

License validity is checked at login 

## Versions

## Test driven development

## Files upload/download