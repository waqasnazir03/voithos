## Update Service Project Quota
If octavia will be used by bks then increase the quota for following resources in service project:

```bash
source admin-openrc.sh

openstack quota set --volumes -1 service
openstack quota set --secgroup-rules -1 service
openstack quota set --secgroups -1 service
```

**Note**: -1 denotes infinite in these quota commands. 
