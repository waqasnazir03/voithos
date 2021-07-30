# Octavia Post-deployment Steps
These steps are only required if openstack release is older than wallaby or
`octavia_auto_configure` is `no` in globals file for wallaby or newer release.
## Create External Network
Using cli or webui, create external network that will act as loadbalancers management network.
Port security should be enabled on this network.

## Create and source octavia-openrc.sh
In wallaby cloud, `kolla-ansible post-deploy` creates both `admin-openrc.sh` 
and `octavia-openrc.sh`. For older versions, use this template:
```yaml
# Get <auth_url> from admin-openrc.sh
# Get <octavia_keystone_password> using following command:
# cat cloud-configs/passwords.yml | grep octavia_keystone_password
for key in $( set | awk '{FS="="}  /^OS_/ {print $1}' ); do unset $key ; done
export OS_PROJECT_DOMAIN_NAME=Default
export OS_USER_DOMAIN_NAME=Default
export OS_PROJECT_NAME=service
export OS_USERNAME=octavia
export OS_PASSWORD=<octavia_keystone_password>
export OS_AUTH_URL=<auth_url>
export OS_INTERFACE=internal
export OS_ENDPOINT_TYPE=internalURL
export OS_IDENTITY_API_VERSION=3
export OS_REGION_NAME=RegionOne
export OS_AUTH_PLUGIN=password
```
Source openrc file.
```yaml
source ~/cloud-configs/octavia-openrc.sh
```

## Create Flavor For Amphora
```yaml
openstack flavor create --vcpus 1 --ram 1024 --private "amphora"
```

## Create Keypair
Kolla-ansible uses this keypair name. Don't use any other name.
```yaml
openstack keypair create --public-key id_rsa.pub octavia_ssh_key
```
This public key will be stored in loadbalancer's `authorized_hosts` file.
It's better to use deployment server's public key.

## Create Security Group
```yaml
openstack security group create lb-mgmt-sec-grp
openstack security group rule create --protocol icmp lb-mgmt-sec-grp
openstack security group rule create --protocol tcp --dst-port 22 lb-mgmt-sec-grp
openstack security group rule create --protocol tcp --dst-port 9443 lb-mgmt-sec-grp
```

## Update Globals File
```yaml
# Use the ids of network, security group and flavor created in the steps above.
octavia_amp_boot_network_list: <network-id>
octavia_amp_secgroup_list: <secgrp-id>
octavia_amp_flavor_id: <flavor-id>
```

## Reconfigure Octavia
Run this command to reconfigure octavia.
```yaml
voithos openstack kolla-ansible reconfigure \
  --release <openstack-release> --ssh-key ~/.ssh/id_rsa \
  --globals globals.yml   --passwords passwords.yml \
  --inventory inventory   --certificates certificates/  \
  --config config/ -t octavia
```
