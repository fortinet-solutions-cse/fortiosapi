# fortiosAPI

Python library to configure Fortinet devices (REST API and SSH)

Monitoring is pending.

Compare to the REST API there a few add-ons:
 In addition to get,put,post,delete methods there is a set which will
 try to post and if failing will put and collect the mkey directly.

## Muli vdom
In multi vdom environment use vdom=global in the API call.
As it is a reserved word the API will switch to use the global=1 and
take care of the differences in the repsonses.

## Schema
There is a get_schema call and an example to get the schema of the
differents methods to ease writting them.

## Roadmap
unittests
monitoring
license upload and update-now.
