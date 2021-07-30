# Octavia Certificates

## Manual/Train Procedure
This procedure is for openstack train. It also works with wallaby.
### Clone Octavia Repository
```yaml
cd ~
git clone https://opendev.org/openstack/octavia
git checkout stable/<openstack-release-name>
```
### Get octavia_ca_password 
```yaml
cat cloud-configs/passwords.yml | grep octavia_ca_password
```
### Update Cert Generation Script
```yaml
cd octavia/bin
# <octavia_ca_password> is the password you get from "cat cloud-config/passwords.yml | grep octavia_ca_password"
sed -i 's/not-secure-passphrase/<octavia_ca_password>/g' create_single_CA_intermediate_CA.sh
```
### Generate Certs
```yaml
./create_single_CA_intermediate_CA.sh openssl.cnf
```
### Copy Certs to config/octavia
```yaml
mkdir ~/cloud-configs/config/octavia
cd single_ca/etc/octavia/certs/
cp * ~/cloud-configs/config/octavia
```

## Kolla-ansible Procedure
This procedure only works with openstack wallaby.
First use `voithos openstack kolla-ansible DEBUG` command to create kolla-ansible wallaby container.
Then run these commands to generate and copy certs.
```yaml
mkdir ~/cloud-configs/config/octavia
docker exec -it kolla-ansible-wallaby bash
cd /etc/kolla
kolla-ansible octavia-certificates
```
Certs generated at `/etc/kolla/config/octavia` inside container can be seen at
`<cloud-configs>/config/octavia` on deployment server.