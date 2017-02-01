
# Openstack specifics:

MTU is 1500 by default no autoadapt

Config-drive mandatory even if no license file is passed. If not available can start one configure, create a snapshot and use that as the "golden" image.

Provided port on overlay network must have anti-spoofing disabled.
neutron port-update 02f54ebf-57ce-45d2-b690-0526ee7e7429 --no-security-groups --port_security_enabled=False
(prior to mitaka needs to be adapted and find ways to know if Openstack supports it)


Cloud-init can be configured per Openstack and point to fortimanager for licensing (Fortios+PAYG) or localy deployed (license files + fortigate)

First interface is mgmt be sur to start/connect with the management netwrok as the first on the image (to be checked)

. /nova.rc

#Push image
openstack image create --disk-format qcow2 --container-format bare  --public  "FGT VM64 1100"  --file fortios.qcow2
#http://docs.openstack.org/user-guide/cli-cheat-sheet.html
cat << EOF > fgt-user-data.txt
config system interface
 edit "port1"
  set mode dhcp
  set allowaccess ping https ssh http snmp fgfm
  set mtu 1456
 next
 edit "port2"
  set mode dhcp
  set allowaccess ping
  set mtu 1456
 next
end

config router static
    edit 1
        set gateway 192.168.16.1
        set device "port1"
    next
end

config system dns
 set primary 10.10.10.1
 unset secondary
end
config sys global
 set hostname fgt
end
EOF


#Tried (ref http://docs.openstack.org/cli-reference/nova.html)

nova boot --image "FGT VM64 1100" FGT1 --key-name default --security-group default --flavor m1.small --user-data fgt-user-data.txt --config-drive=true --file license=FGVMUL0000075926.lic --nic net-name=private
nova boot --image "Trusty x86_64" U --key-name default --security-group default --flavor m1.small --nic net-name=private

#nova floating-ip-create

nova floating-ip-associate U 10.10.11.14

nova floating-ip-associate FGT1 10.10.11.15
sudo iptables -t nat -A PREROUTING -p tcp --dport 4043 -j DNAT --to-destination 10.10.11.15:443
sudo iptables -t nat -A PREROUTING -p tcp --dport 4022 -j DNAT --to-destination 10.10.11.15:22