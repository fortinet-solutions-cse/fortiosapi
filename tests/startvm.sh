#!/bin/bash -e

#Example url to get build: https://info.fortinet.com/files/FortiOS/v5.00/images/build1449/FOS_VM64_KVM-v5-build1449-FORTINET.out.kvm.zip
(virsh list --all| grep fostest )||virt-install --name fostest \
--ram 1024 --disk path=fortios.qcow2 --disk path=/var/lib/libvirt/images/fostest.qcow2,size=10,bus=virtio \
--vcpus=1 --os-type=linux --cpu=host --import --noautoconsole --keymap=en-us --network=default,model=virtio,mac=40:40:40:01:02:03

## froce mac adress so that the ip will always be the same to avoid changing conf files
## virsh undefine fostest
# to delete the domain
