#!/bin/bash -ex
# Build the system under test SUT with the ENV variable (to be integrated in Jenkins).
# 

## remove any running VM
for l in `virsh list --name|grep FGT`
do
  virsh destroy $l
  virsh undefine $l
done

cd /home/fortinet/

[ -z "$flavor" ] && (echo "variable flavor must be set"; exit 2)
[ -z "${fgtversion}" ] && (echo "variable VERSION must be set"; exit 2)
export NAME=$flavor"_"$fgtversion
##need a map version to build as the zip images only have build in there name
build=`jq -r ".[] | select(.version == \"$fgtversion\")| .build" versions-build.json`
[ -z "$build" ] && (echo "Can't find build for $fgtversion"; exit 2)
echo "BUILD is $build"

## destroy running VM
fuser -vk $JENKINS_HOME/fortios-${NAME}.qcow2 || echo "no fortios-${NAME}.qcow2 probably cleaned" # should kill VM using it
(virsh list --all| grep ${NAME} ) && (echo "virtual machine ${NAME} removed"; virsh destroy ${NAME} ;virsh undefine ${NAME})
##erase and recreate the qcow2
rm -f $JENKINS_HOME/fortios-${NAME}.qcow2 /var/lib/libvirt/images/foslogs.qcow2
majorv=`echo $fgtversion|awk -F "-" '{print $2}'|awk -F'.' '{print $1}'`
cd $JENKINS_HOME
rm -f fortios.qcow2
unzip /home/fortinet/versions/FGT_VM64_KVM-v${majorv}-build$build-FORTINET.out.kvm.zip
mv fortios.qcow2 fortios-${NAME}.qcow2
# clean then create the config drive
rm -rf cfg-drv-fgt
rm -rf day0.iso
mkdir -p cfg-drv-fgt/openstack/latest/
mkdir -p cfg-drv-fgt/openstack/content/
cp /home/fortinet/flavors/${flavor}.lic cfg-drv-fgt/openstack/content/0000

# rely on dhcp !!
ROUTER_IP=192.168.122.1
## so you can adapt
envsubst < /home/fortinet/flavors/${flavor}.conf >cfg-drv-fgt/openstack/latest/user_data
genisoimage -publisher "OpenStack Nova 12.0.2" -J -R -V config-2 -o day0.iso cfg-drv-fgt
virt-install --name ${NAME} --os-variant linux \
--ram 2048 --disk path=fortios-${NAME}.qcow2,bus=virtio --disk day0.iso,device=cdrom,bus=ide,format=raw \
--vcpus=2 --os-type=linux --cpu=host --import --noautoconsole --keymap=en-us \
--network=default,model=virtio --network bridge=docker0,model=virtio --network bridge=docker0,model=virtio
##optionnal add a log disk for long running tests --disk path=/var/lib/libvirt/images/foslogs.qcow2,size=10,bus=virtio \

until (virsh domifaddr ${NAME} |grep vnet0)
do
 sleep 3
 echo "waiting the vm IP to be up"
done

export IP=`virsh domifaddr ${NAME} |grep vnet0 | awk '{print $4}' |awk -F '/' '{print $1}'`

##wait to have enough ping to avoid testing in the middle of the VM reboots for license
echo "waiting the vm to be up"
until (ping -c 15 $IP|grep ' 0% packet loss,')
do
 sleep 3
 echo "waiting the vm to be up"
done

#All good let's dump the virsh.yaml on the output

envsubst < /home/fortinet/flavors/${flavor}.yaml > $JENKINS_HOME/virsh${flavor}.yaml
## implement a timer or let jenkins ?

## to destroy
# virsh destroy
# virsh undefine