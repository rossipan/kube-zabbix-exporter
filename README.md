kube-zabbix-exporter
===

kube-zabbix-exporter based on [prometheus/client_python](https://github.com/prometheus/client_python) and [shamil/zabbix-etcd](https://github.com/shamil/zabbix-etcd), copy from [bhuisgen/docker-zabbix-coreos](https://github.com/bhuisgen/docker-zabbix-coreos)


## Pre-required
* CoreOS
* kubernetes v1.7 or later
* [kube-prometheus](https://github.com/coreos/prometheus-operator/tree/master/contrib/kube-prometheus)


## Usage

### Import templates

Import the needed templates in templates/*

### Create auto-registration action (optional)

To automatically create new host on the zabbix server, create a auto-registration action (Configuration/Actions/Auto-registration):

* conditions: Host metadata like <stage>-<k8s version> or for your want
* actions: Add Host, Add host to groups, Link to templates (Template CoreOS, Template_ETCD, Template_Kube_apiserver, Template_Kubelet)

The host metadata value is the value shared by all your cluster nodes. Each node must shared the same value.

If you don't want to use the auto-registration, you must add each node in the frontend.


### Install

The needed options are:

* *ZBX_SERVER_HOST* (required): the IP address of the Zabbix server
* *ZBX_METADATA* (required): the metadata value shared by all servers on the same cluster. This value will match the autoregistration action
* *ZBX_HOSTNAME* (optional): the hostname used by this agent in the zabbix frontend. If no value is given, the machine id of the host will be used

The agent will start and the auto-registration will add your agent if a auto-registration action is matched for your host metadata. If you don't want to auto-register your nodes, you need to specify the hostname value to use.


deploy the zabbix agent on etcd node with docker:

```
docker run -d -p 10050:10050 -c 1024 -m 64M --memory-swap=-1 \
    -v /:/rootfs:ro \
    --privileged \
    --net=host \
    --pid=host \
    --restart=always \
    --env ZBX_SERVER_HOST="<ZBX_SERVER_HOST>" \
    --env ZBX_METADATA="<ZBX_METADATA>" \
    --name zabbix-coreos rossipan/docker-zabbix-coreos/3.0.17
```

for example:

```
docker run -d -p 10050:10050 -c 1024 -m 64M --memory-swap=-1 \
    -v /:/rootfs:ro \
    --privileged \
    --net=host \
    --pid=host \
    --restart=always \
    --env ZBX_SERVER_HOST="10.0.0.100" \
    --env ZBX_METADATA="prod-etcd" \
    --name zabbix-coreos rossipan/docker-zabbix-coreos/3.0.17
```

deploy the zabbix agent with daemonset:

```
# edit zabbix-agent-daemonset.yaml.j2 & rename to zabbix-agent-daemonset.yaml
$ kubectl create namespace monitoring
$ kubectl apply -f zabbix-agent-daemonset.yaml
```

## Available metrics


### etcd

| Zabbix Item Name | Zabbix Item Key |
| ------------ | ----------- |
| **etcd node: health**| healthz|
| **etcd node: receive requests**| v2/stats/self:recvAppendRequestCnt |
| **etcd node: send requests**| v2/stats/self:sendAppendRequestCnt |
| **etcd node: state**| v2/stats/self:state |
| **etcd node: expires**| v2/stats/store:expireCount |
| **etcd node: gets fail**| v2/stats/store:getsFail |
| **etcd node: gets success**| v2/stats/store:getsSuccess |
| **etcd node: watchers**| v2/stats/store:watchers |
| **etcd cluster: sets fail**| v2/stats/store:setsFail |
| **etcd cluster: sets success**| v2/stats/store:setsSuccess |
| **etcd cluster: update fail**| v2/stats/store:updateFail |
| **etcd cluster: update success**| v2/stats/store:updateSuccess |
| **etcd cluster: compare and delete fail**| v2/stats/store:compareAndDeleteFail |
| **etcd cluster: compare and delete success**| v2/stats/store:compareAndDeleteSuccess |
| **etcd cluster: compare and swap fail**| v2/stats/store:compareAndSwapFail |
| **etcd cluster: compare and swap success**| v2/stats/store:compareAndSwapSuccess |
| **etcd cluster: create fail**| v2/stats/store:createFail |
| **etcd cluster: create success**| v2/stats/store:createSuccess |
| **etcd cluster: delete fail**| v2/stats/store:deleteFail |
| **etcd cluster: delete success**| v2/stats/store:deleteSuccess |
| **ETCD MEMBERS**| v2/members |
| **etcd follower: {#MEMBER NAME} failed raft requests**| v2/stats/leader:followers/{#MEMBER ID}/counts/fail |
| **etcd follower: {#MEMBER NAME} successful raft requests**| v2/stats/leader:followers/{#MEMBER ID}/counts/success |
| **etcd follower: {#MEMBER NAME} latency to leader**| v2/stats/leader:followers/{#MEMBER ID}/latency/current | 


### Kubernetes apiserver/controller/scheduler

| Zabbix Item Name | Zabbix Item Key |
| ------------ | ----------- |
| **apiserver_request_count: error_rate (verb=DELETE)**| apiserver_request_error_rate[DELETE]|
| **apiserver_request_count: error_rate (verb=GET)**| apiserver_request_error_rate[GET]|
| **apiserver_request_count: error_rate (verb=LIST)**| apiserver_request_error_rate[LIST]|
| **apiserver_request_count: error_rate (verb=PATCH)**| apiserver_request_error_rate[PATCH]|
| **apiserver_request_count: error_rate (verb=POST)**| apiserver_request_error_rate[POST]|
| **apiserver_request_count: error_rate (verb=PUT)**| apiserver_request_error_rate[PUT]|
| **apiserver_request_count: verb=DELETE, metrics=error_count**| metrics_exporter[https://{HOST.IP}:443/metrics,counter,apiserver_request_count,DELETE:error_count]|
| **apiserver_request_count: verb=DELETE, metrics=total_count**| metrics_exporter[https://{HOST.IP}:443/metrics,counter,apiserver_request_count,DELETE:total_count]|
| **apiserver_request_count: verb=GET, metrics=error_count**| metrics_exporter[https://{HOST.IP}:443/metrics,counter,apiserver_request_count,GET:error_count]|
| **apiserver_request_count: verb=GET, metrics=total_count**| metrics_exporter[https://{HOST.IP}:443/metrics,counter,apiserver_request_count,GET:total_count]|
| **apiserver_request_count: verb=LIST, metrics=error_count**| metrics_exporter[https://{HOST.IP}:443/metrics,counter,apiserver_request_count,LIST:error_count]|
| **apiserver_request_count: verb=POST, metrics=total_count**| metrics_exporter[https://{HOST.IP}:443/metrics,counter,apiserver_request_count,LIST:total_count]|
| **apiserver_request_count: verb=PATCH, metrics=error_count**| metrics_exporter[https://{HOST.IP}:443/metrics,counter,apiserver_request_count,PATCH:error_count]|
| **apiserver_request_count: verb=PATCH, metrics=total_count**| metrics_exporter[https://{HOST.IP}:443/metrics,counter,apiserver_request_count,PATCH:total_count]|
| **apiserver_request_count: verb=POST, metrics=error_count**| metrics_exporter[https://{HOST.IP}:443/metrics,counter,apiserver_request_count,POST:error_count]|
| **apiserver_request_count: verb=POST, metrics=total_count**| metrics_exporter[https://{HOST.IP}:443/metrics,counter,apiserver_request_count,POST:total_count]|
| **apiserver_request_count: verb=PUT, metrics=error_count**| metrics_exporter[https://{HOST.IP}:443/metrics,counter,apiserver_request_count,PUT:error_count]|
| **apiserver_request_count: verb=PUT, metrics=total_count**| metrics_exporter[https://{HOST.IP}:443/metrics,counter,apiserver_request_count,PUT:total_count]|
| **apiserver_request_latencies: DELETE**| metrics_exporter[https://{HOST.IP}:443/metrics,summary,apiserver_request_latencies_summary,DELETE]|
| **apiserver_request_latencies: GET**| metrics_exporter[https://{HOST.IP}:443/metrics,summary,apiserver_request_latencies_summary,GET]|
| **apiserver_request_latencies: LIST**| metrics_exporter[https://{HOST.IP}:443/metrics,summary,apiserver_request_latencies_summary,LIST]|
| **apiserver_request_latencies: PATCH**| metrics_exporter[https://{HOST.IP}:443/metrics,summary,apiserver_request_latencies_summary,PATCH]|
| **apiserver_request_latencies: POST**| metrics_exporter[https://{HOST.IP}:443/metrics,summary,apiserver_request_latencies_summary,POST]|
| **apiserver_request_latencies: PUT**| metrics_exporter[https://{HOST.IP}:443/metrics,summary,apiserver_request_latencies_summary,PUT]|
| **apiserver_request_latencies: POST**| metrics_exporter[https://{HOST.IP}:443/metrics,summary,apiserver_request_latencies_summary,POST]|
| **apiserver: healthz**| metrics_exporter[https://{HOST.IP}:443/healthz,healthz]|
| **kube-scheduler: healthz**| metrics_exporter[http://{HOST.IP}:10251/healthz,healthz]|
| **kube-scheduler: current leader**| metrics_exporter[https://{HOST.IP}:443,get_leader,kube-scheduler]|
| **kube-controller-manager: healthz**| metrics_exporter[http://{HOST.IP}:10252/healthz,healthz]|
| **kube-controller-manager: current leader**| metrics_exporter[https://{HOST.IP}:443,get_leader,kube-controller-manager]|


### Kubelet
| Zabbix Item Name | Zabbix Item Key |
| ------------ | ----------- |
| **kubelet: healthz**| metrics_exporter[https://{HOST.IP}:10250/healthz,healthz]|
| **UBELET_RUNNING_POD_COUNT**| metrics_exporter[https://{HOST.IP}:10250/metrics,gauge,kubelet_running_pod_count]|
