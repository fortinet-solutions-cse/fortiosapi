# Rift.io usage for automated demo..

Run ./deploy.sh
wait a bit .. then you should be able to login on
http://10.10.10.x:8443/

do lxc list and look for the riftio-lauchpad conatiner IP
is 10.10.10.x 

login admin/admin

# build the packages
cd apache_vnf_src ; make
cd fortigate_vnfd_src; make

You will create vnfd.tar.gz package you can upload in rift.io
Then upload: FortigateApache_nsd.yaml

*Workaround for now
You will have to upload an already configured fortigate image and
create a snapshot called Fortigate. 

# Going deeper on rift
Check rift documentation https://open.riftio.com/documentation/riftware/4.3/

