# Create Amphora Image

## Download Amphora Image
Run this command to download amphora image.
```yaml
voithos openstack image download -i amphora-<openstack-release>
# Supported releases for <openstack-release> are train and wallaby
```

## Create Amphora Image
Source octavia openrc file.
```yaml
source ~/cloud-configs/octavia-openrc.sh
```
Create image.
```yaml
openstack image create amphora-x64-haproxy \
  --container-format bare \
  --disk-format qcow2 --private \
  --tag amphora --file amphora-<openstack-release>.qcow2
```
