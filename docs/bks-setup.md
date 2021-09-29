# Breqwatr Kubernetes Service Setup

Before installing BKS, ensure that the Octavia service is functioning correctly.

## Deploy the Cluster-API Glance Image

On the OpenStack cluster's deployment server, download the glance image. If your Glance is
Ceph-backed, also convert it to raw format before uploading it.

```
voithos openstack image download -i capi-kube-v1.20.9
# capi-kube-v1.20.9.qcow2 will download, it is about 4GB

# example of a ceph-backed image
qemu-img convert -f qcow2 -O raw capi-kube-v1.20.9.qcow2  capi-kube-v1.20.9.raw
openstack image create \
  --project breqwatr \
  --private \
  --container-format bare \
  --disk-format raw \
  --file capi-kube-v1.20.9.raw \
  --min-disk 4 \
  bks-v1.20.9
```

## Validate the default storage type

Cluster-API uses [bootfromvolume](https://pkg.go.dev/github.com/gophercloud/gophercloud/openstack/compute/v2/extensions/bootfromvolume)
from the `gophercloud` Go library to boot an OpenStack instance from a volume. Doing so only
supports using the default volume type.

You can show the default type by running the following on your bmc:
```
cinder --insecure type-default
```

If the default name is `__DEFAULT__`, then you're going to get errors when you create a cluster.
Breqwatr clouds set the quota for the `__DEFAULT__` type to 0GB to prevent accidental usage of that
storage type.

Edit the cinder-api cinder.conf file to contain a `default_volume_type`. In Kolla-Ansible this
means creating a `config/cinder/cinder-api.conf` file prior to running deploy or reconfigure.

```
[DEFAULT]
...
enabled_backends = Breqwatr
default_volume_type = Ceph
```

## Create a bootstrap CAPI cluster

On a routed external VLAN, create an Ubuntu 20.04 VM with at least 20GB disk, 8GB RAM and 4 cores.
Call it something like `bootstrap-bks` and place it in any project. Ensure you can SSH to it.
By convention, we create this VM in the `breqwatr` project.

Log into the server and run the bootstrap script.

```
curl -s https://gist.githubusercontent.com/breqwatr/90b45dedd10f3a01b1091758cf7bbaa1/raw/67f097fc2ca58490a5279b279258a8045caf0064/setup-kind.sh | bash
```

Show the cluster to confirm it installed correctly:

```
kubectl cluster-info --context kind-kind
kubectl get nodes
```

Install the OpenStack infrastructure provider
```
clusterctl init --infrastructure openstack --core 'cluster-api:v0.4.1' --control-plane 'kubeadm:v0.4.1' --bootstrap 'kubeadm:v0.4.1'
```

---


## Create an OpenStack service account for Cluster-API (CAPI)

On a system with administrative access and an OpenStack command-line, create the user. The
deployment server is a good place to run these.

```
openstack user create bks-service-account --password-prompt
openstack role add --user bks-service-account --project breqwatr admin
openstack role add --user bks-service-account --project admin admin
openstack role add --user bks-service-account --project admin service
```

### Create a CapiKey keyring

This keyring is used to administer the VMs that run Kubernetes. End-users should not have access
to this private key. You can use the deployment server's key, just be sure it's created under the
`bks-service-account` user.

```
cd ~/.ssh
openstack keypair create --user bks-service-account --public-key id_rsa.pub CapiKey
```

While you're here, show the public endpoint for keystone to use in the next step
```
openstack endpoint list  --service keystone --interface public -c URL -f value
```


### Enable remote access to Kind cluster

The Kind cluster is temporary and not secure, but it can be used to power BKS until BKS builds its
own cluster.

SSH into the Kind server with a terminal session you can leave open. Kind is only really meant to
be used locally, so the kube-api port listening on `127.0.0.1` needs to be forwarded to `0.0.0.0`.

```
socat tcp-l:443,fork,reuseaddr tcp:127.0.0.1:38866
```

The terminal will block. Just leave it open. You can now curl to your Kind cluster's floating IP
address on https: `curl -k https://<floating ip>`. You should get a 403 Forbidden response.

Next, download the `~/.kube/config` kubeconfig file to your workstation. It needs to end up on each
control node, but edit it first to change the kube-API IP address to the floating IP and to disable
the TLS warnings.

`vi config`

Remove the `certificate-authority-data` value. Replace the `server:` value with
`https://<floating ip>`. Also add `insecure-skip-tls-verify: true`.
Example:

```
- cluster:
    insecure-skip-tls-verify: true
        server: https://10.106.250.138
```

Distribute this kubeconfig file to each control node. You can put it anywhere, by convention we
place it in `/etc/arcus/capi/kind.kubeconfig`.



## Launch the ACAPI service

Arcus-CAPI will operate against the Kind Cluster-API cluster for now. It will then be deleted and
recreated once a production-quality Cluster-API cluster exists.



### Pull the latest Arcus-CAPI image:

On each control-node, ensure Voithos is installed, updated, and licensed.

```
voithos service arcus capi pull -r latest
mkdir -p /etc/arcus/capi
```

Transfer the kubeconfig file to the control nodes - it will be needed by arcus-capi.
Place it in `/etc/arcus/capi/bks.kubeconfig`

### Deploy OpenStack OpenRC File

Grab or create an openrc file which uses the public endpoints. You can write one as follows.

Ensure you insert your own username and `AUTH_URL` value.
`vi /etc/arcus/capi/openrc.sh`

```
# Clear any old environment that may conflict.
for key in $( set | awk '{FS="="}  /^OS_/ {print $1}' ); do unset $key ; done
export OS_PROJECT_DOMAIN_NAME=Default
export OS_USER_DOMAIN_NAME=Default
export OS_PROJECT_NAME=breqwatr
export OS_TENANT_NAME=breqwatr
export OS_USERNAME=bks-service-account
export OS_PASSWORD=
export OS_AUTH_URL=
export OS_INTERFACE=public
export OS_ENDPOINT_TYPE=publicURL
export OS_ENDPOINT_TYPE=publicURL
export OS_IDENTITY_API_VERSION=3
export OS_REGION_NAME=RegionOne
export OS_AUTH_PLUGIN=password
export OS_CACERT=/etc/kolla/certificates/haproxy-ca.crt
```

### [Optional] Deploy the CA Certificate

When you use a self-signed cert and don't pass the CA certificate file along to Cluster-API, you
will encounter a problem where the first control node spawns but can't start Kubelet, causing the
remainder of the automation to fail. To allow Kubernetes's OpenStack cloud provider to trust the
OpenStack cloud, you must copy the CA cert file to each control node.

By convention, create the file as `/etc/certs/cacert`.

```
scp haproxy-ca.crt root@<node>:/etc/certs/cacert
```

### Launch Arcus-CAPI service against the Kind cluster

Launch the CAPI service on each control node. The `--kubeconfig` file you use will point to the
Kind cluster for now. We'll be deleting this container and relaunching it once we have a new file.

```

voithos service arcus capi start -r latest --openrc /etc/arcus/capi/openrc.sh --kubeconfig /etc/arcus/capi/kind.kubeconfig
# or if you have a self-signed cert:
# voithos service arcus capi start -r latest --openrc /etc/arcus/capi/openrc.sh --kubeconfig /etc/arcus/capi/kind.kubeconfig --cacert /etc/certs/cacert

# Verify
docker logs arcus_capi
curl localhost:8888
```

### Add Arcus-API Integration

Find the image ID of the Cluster-API image, you'll use it in one of the integration's fields.
Also determine the volume type ID that each cluster should use.

```
openstack image list | grep bks
openstack volume type list
```

Create the integration - Use any OpenStack admin account account to create the integration,
similar to how storage integrations are created for Arcus-API.

```
voithos service arcus api integrations create \
  -u arcusadmin \
  -p <password> \
  -a http://<vip>:1234 \
  -t Clusterapi \
  -f display_name Arcus-CAPI \
  -f image_id <image id> \
  -f acapi_url http://<vip>:8888 \
  -f volume_type_id <volume type id>
```

Validate:

```
# Show the integration
voithos service arcus api integrations list -p <password> -u arcusadmin -a http://<api ip>:1234
```

With the integration created, Arcus-API will know how to communicate with Arcus-CAPI. Arcus-Client
will now display the Kubernetes icon in the project accordion.



## Create the permanent parent cluster

This is the cluster that BKS will use to operate Cluster-API long-term. The Kind cluster can be
deleted once this procedure is complete.

Open the Arcus web UI and navigate to the `breqwatr` project's Kubernetes page. Create a cluster
and name it `bks`. The cluster can be small, with either 1 and 1 or 3 and 2 nodes depending on your
availability requirements.

Once the cluster is created and in the `CNI_REQUIRED` state, you can download the `kubeconfig` file
from the web UI. Transfer `bks.kubeconfig` to the Kind VM, since it already has `kubectl` and
`clusterctl` installed.

Validate that the kubeconfig file works from the Kind VM:
```
kubectl --kubeconfig bks.kubeconfig get nodes
```

Make the kubeconfig file your default one:
```
mv ~/.kube/config ~/.kube/kind-config
cp bks.kubeconfig ~/.kube/config
kubectl get nodes
```

### Install Cluster-API on the new cluster:

The `clusterctl` tool uses the default kubeconfig file in `~/.kube/config`. Run it again from the
kind/bootstrap-cluster to initialize Cluster-API on the BKS cluster.

```
clusterctl init --infrastructure openstack --core 'cluster-api:v0.4.1' --control-plane 'kubeadm:v0.4.1' --bootstrap 'kubeadm:v0.4.1'
```


## Redeploy Arcus-CAPI on the new cluster

Place the same `bks.kubeconfig` file on the control nodes in `/etc/arcus/capi/bks.kubeconfig`.
Delete the current Arcus-CAPI service from the control nodes and redeploy it using the new
`etc/arcus/capi/bks.kubeconfig` file.

```
docker rm -f arcus_capi
voithos service arcus capi start -r latest --openrc /etc/arcus/capi/openrc.sh --kubeconfig /etc/arcus/capi/bks.kubeconfig
# or if you have a self-signed cert:
# voithos service arcus capi start -r latest --openrc /etc/arcus/capi/openrc.sh --kubeconfig /etc/arcus/capi/bks.kubeconfig --cacert /etc/certs/cacert
```


### Decommission the bootstrap/kind cluster

Shut down and delete the bootstrap cluster. Now that the BKS cluster exists, the bootstrap cluster
is not needed.



