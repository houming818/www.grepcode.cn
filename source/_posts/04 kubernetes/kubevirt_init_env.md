---
title: Kubevirt实战/环境搭建与测试项目
link_title: Kubevirt001
categories:
  - 04 kubernetes
tags: 运维 开发 DevOps Kubevirt
date: 2023-09-22 13:00:00
---

## 参考资料

1. [官方文档-安装](https://kubevirt.io/user-guide/operations/installation/)
2. [kubevirt-101](https://www.katacoda.com/kubevirt/scenarios/kubevirt-101)

## 环境说明
|主机名|IP|OS|role|
|---|---|---|---|
|c12|192.168.1.112|CentOS-7|master|
|c13|192.168.1.113|CentOS-7|node|
|c14|192.168.1.114|CentOS-7|node|

> kubevirt: v0.49.0

<!-- #region -->
## 安装文档

KubeVirt 是 Kubernetes 的虚拟化插件，本指南假定已安装 Kubernetes 集群。

> 安装kubernets单点测试集群可参考 [搭建单点Kubernetes cluster](https://www.grepcode.cn/devops/kubernetes/standalone.html)
>
> 安装kubernets多点测试集群可参考 [如何使用kubespray](https://github.com/kubernetes-sigs/kubespray)

### 要求

在开始之前需要满足一些要求：

- 基于 Kubernetes 1.10 或更高版本的Kubernetes集群或衍生产品（如OpenShift 、Tectonic)
- Kubernetes apiserver 必须具有--allow-privileged=true才能运行 KubeVirt 的特权 DaemonSet。
- kubectl 客户端实用程序
- 容器运行时支持

验证硬件虚拟化支持

推荐使用支持虚拟化的硬件。您可以使用 virt-host-validate 来确保您的主机能够运行虚拟化工作负载：

```
$ virt-host-validate qemu
  QEMU: Checking for hardware virtualization     : PASS
  QEMU: Checking if device /dev/kvm exists      : PASS
  QEMU: Checking if device /dev/kvm is accessible : PASS
  QEMU: Checking if device /dev/vhost-net exists  : PASS
  QEMU: Checking if device /dev/net/tun exists   : PASS
```

### 在 Kubernetes 上安装 KubeVirt

KubeVirt 可以使用 KubeVirt 操作符安装，该操作符管理所有 KubeVirt 核心组件的生命周期。以下是如何使用官方版本安装 KubeVirt 的示例。

```
# Pick an upstream version of KubeVirt to install
$ export RELEASE=v0.49.0
# Deploy the KubeVirt operator
$ kubectl apply -f https://github.com/kubevirt/kubevirt/releases/download/${RELEASE}/kubevirt-operator.yaml
# Create the KubeVirt CR (instance deployment request) which triggers the actual installation
$ kubectl apply -f https://github.com/kubevirt/kubevirt/releases/download/${RELEASE}/kubevirt-cr.yaml
# wait until all KubeVirt components are up
$ kubectl -n kubevirt wait kv kubevirt --for condition=Available
```

如果硬件虚拟化不可用，则 可以通过在 KubeVirt CR中设置如下来启用软件仿真回退：`spec.configuration.developerConfiguration.useEmulation=true`

```
$ kubectl edit -n kubevirt kubevirt kubevirt
```

将以下内容添加到`kubevirt.yaml`文件中

```
    spec:
      ...
      configuration:
        developerConfiguration:
          useEmulation: true
```

> 注意：在发布 v0.20.0 之前，kubectl wait 命令的条件被命名为“Ready”而不是“Available”
>
> 注意：在 KubeVirt 0.34.2 之前，kubevirt-config在 install-namespace 中调用的 ConfigMap 用于配置 KubeVirt。自 0.34.2 起，此方法已被弃用。configmap 仍然优先configuration于 CR 存在，但它不会接收未来的更新，您应该将任何自定义配置迁移到spec.configurationKubeVirt CR 上。

所有新组件都将部署在kubevirt命名空间下：

```
kubectl get pods -n kubevirt
NAME                                           READY     STATUS        RESTARTS   AGE
virt-api-6d4fc3cf8a-b2ere                      1/1       Running       0          1m
virt-controller-5d9fc8cf8b-n5trt               1/1       Running       0          1m
virt-handler-vwdjx                             1/1       Running       0          1m
...
```


### 安装每日开发者构建

KubeVirt 每天从当前主分支发布一个开发人员构建。通过查看我们的 nightly-build-jobs可以了解上一次发布的时间。

要安装最新的开发人员版本，请运行以下命令：

```
$ LATEST=$(curl -L https://storage.googleapis.com/kubevirt-prow/devel/nightly/release/kubevirt/kubevirt/latest)
$ kubectl apply -f https://storage.googleapis.com/kubevirt-prow/devel/nightly/release/kubevirt/kubevirt/${LATEST}/kubevirt-operator.yaml
$ kubectl apply -f https://storage.googleapis.com/kubevirt-prow/devel/nightly/release/kubevirt/kubevirt/${LATEST}/kubevirt-cr.yaml
```

要找出此构建基于哪个提交，请运行：

```
$ LATEST=$(curl -L https://storage.googleapis.com/kubevirt-prow/devel/nightly/release/kubevirt/kubevirt/latest)
$ curl https://storage.googleapis.com/kubevirt-prow/devel/nightly/release/kubevirt/kubevirt/${LATEST}/commit
d358cf085b5a86cc4fa516215f8b757a4e61def2
```

### 实验性 ARM64 开发人员构建

可以像这样安装实验性 ARM64 开发人员版本：

```
$ LATEST=$(curl -L https://storage.googleapis.com/kubevirt-prow/devel/nightly/release/kubevirt/kubevirt/latest-arm64)
$ kubectl apply -f https://storage.googleapis.com/kubevirt-prow/devel/nightly/release/kubevirt/kubevirt/${LATEST}/kubevirt-operator-arm64.yaml
$ kubectl apply -f https://storage.googleapis.com/kubevirt-prow/devel/nightly/release/kubevirt/kubevirt/${LATEST}/kubevirt-cr-arm64.yaml
```

### 从源头部署

请参阅开发人员入门指南 以了解如何从源代码构建和部署 KubeVirt。

### 安装网络插件（可选）

KubeVirt 本身并没有带来任何额外的网络插件，它只是允许用户使用它们。如果您想将您的虚拟机连接到多个网络（Multus CNI）或完全控制 L2（OVS CNI），您需要部署相应的网络插件。有关详细信息，请参阅 OVS CNI 安装指南。

> 注意： KubeVirt Ansible网络剧本 默认安装这些插件。

### 限制 KubeVirt 组件节点放置

您可以通过编辑 KubeVirt CR 来限制 KubeVirt 组件在集群节点中的放置：

KubeVirt 控制平面组件（virt-controller、virt-api）的放置由`KubeVirt CR`中的字段`.spec.infra.nodePlacement`控制。

virt-handler DaemonSet pod 的放置（以及因此调度到集群的 VM 工作负载的放置）由`KubeVirt CR`中的字段`.spec.workloads.nodePlacement`控制。

对于这些.nodePlacement对象中的每一个.affinity，可以配置.nodeSelector和子字段。 有关使用这些字段的更多信息，.tolerations请参阅API 参考中的说明。

例如，要将 virt-controller 和 virt-api pod 限制为仅在 control-plane 节点上运行：

```
kubectl patch -n kubevirt kubevirt kubevirt --type merge --patch '{"spec": {"infra": {"nodePlacement": {"nodeSelector": {"node-role.kubernetes.io/control-plane": ""}}}}}'
```

要将 virt-handler pod 限制为仅在具有`region=primary`标签的节点上运行：

```
kubectl patch -n kubevirt kubevirt kubevirt --type merge --patch '{"spec": {"workloads": {"nodePlacement": {"nodeSelector": {"region": "primary"}}}}}'
```

### 安装Virtctl

```
wget -O /usr/local/bin/virtctl https://github.com/kubevirt/kubevirt/releases/download/${RELEASE}/virtctl-${RELEASE}-linux-amd64
```

<!-- #endregion -->

<!-- #region -->
## 实际安装

在C12 C13 C14上执行安装过程

### apply
```bash
# Pick an upstream version of KubeVirt to install
root@c12$ export RELEASE=v0.49.0
# output

```

```bash
# Deploy the KubeVirt operator
root@c12$ kubectl apply -f https://github.com/kubevirt/kubevirt/releases/download/${RELEASE}/kubevirt-operator.yaml
# output
namespace/kubevirt created
customresourcedefinition.apiextensions.k8s.io/kubevirts.kubevirt.io created
priorityclass.scheduling.k8s.io/kubevirt-cluster-critical created
clusterrole.rbac.authorization.k8s.io/kubevirt.io:operator created
serviceaccount/kubevirt-operator created
role.rbac.authorization.k8s.io/kubevirt-operator created
rolebinding.rbac.authorization.k8s.io/kubevirt-operator-rolebinding created
clusterrole.rbac.authorization.k8s.io/kubevirt-operator created
clusterrolebinding.rbac.authorization.k8s.io/kubevirt-operator created
deployment.apps/virt-operator created
```

```bash
# Create the KubeVirt CR (instance deployment request) which triggers the actual installation
root@c12$ kubectl apply -f https://github.com/kubevirt/kubevirt/releases/download/${RELEASE}/kubevirt-cr.yaml
# output
kubevirt.kubevirt.io/kubevirt created
```

### 验证安装结果

```bash
# wait until all KubeVirt components are up
root@c12$ kubectl -n kubevirt wait kv kubevirt --for condition=Available
# 等待一段时间
error: timed out waiting for the condition on kubevirts/kubevirt

root@c12$ kubectl get pods -A
...
kubevirt      virt-controller-7556586574-g5jcb   1/1     Running            0          8m11s
kubevirt      virt-controller-7556586574-z54jk   0/1     ImagePullBackOff   0          8m11s
kubevirt      virt-handler-29qpt                 1/1     Running            0          8m11s
...

# 有个pod有问题，查看log
root@c12$ kubectl describe pod -n kubevirt virt-controller-7556586574-z54jk
...
  Normal   Scheduled  10m                  default-scheduler  Successfully assigned kubevirt/virt-controller-7556586574-z54jk to c13
  Warning  Failed     4m40s                kubelet            Failed to pull image "quay.io/kubevirt/virt-controller:v0.49.0": rpc error: code = Unknown desc = context canceled
  Warning  Failed     4m40s                kubelet            Error: ErrImagePull
  Normal   BackOff    4m40s                kubelet            Back-off pulling image "quay.io/kubevirt/virt-controller:v0.49.0"
  Warning  Failed     4m40s                kubelet            Error: ImagePullBackOff
  Normal   Pulling    4m28s (x2 over 10m)  kubelet            Pulling image "quay.io/kubevirt/virt-controller:v0.49.0
...

# 镜像拉取失败，用ansible执行镜像拉取
root@*$ ansible -i inventory/hosts c12,c13,c14 -m shell -a 'docker pull quay.io/kubevirt/virt-controller:v0.49.0' -b

# 再次执行,结果符合预期
root@c12$ kubectl -n kubevirt wait kv kubevirt --for condition=Available
kubevirt.kubevirt.io/kubevirt condition met

# 查看kubevirt状态
root@c12$ kubectl get pods -n kubevirt
NAME                               READY   STATUS    RESTARTS   AGE
virt-api-b9fc66c44-78bxs           1/1     Running   0          163m
virt-api-b9fc66c44-cqv7w           1/1     Running   0          163m
virt-controller-7556586574-g5jcb   1/1     Running   0          162m
virt-controller-7556586574-z54jk   1/1     Running   0          162m
virt-handler-29qpt                 1/1     Running   0          162m
virt-handler-8gv78                 1/1     Running   0          162m
virt-handler-sqnlz                 1/1     Running   0          162m
virt-operator-7c67945b69-8782n     1/1     Running   0          164m
virt-operator-7c67945b69-lsrbr     1/1     Running   0          164m
```

### 下载virtctl

```
root@c12$ wget -O /usr/local/bin/virtctl https://github.com/kubevirt/kubevirt/releases/download/${RELEASE}/virtctl-${RELEASE}-linux-amd64
root@c12$ chmod +x /usr/local/bin/virtctl
```
<!-- #endregion -->

<!-- #region -->
## 实际使用

现在一切准备就绪，可以继续并启动 VM。

### 创建 Definition

下面的命令将虚拟机`Definition(定义)`的 YAML 应用到我们当前的 Kubernetes 环境中，定义 VM 名称、所需资源（磁盘、CPU、内存）等。

```
root@c12$ kubectl apply -f https://kubevirt.io/labs/manifests/vm.yaml
virtualmachine.kubevirt.io/testvm created
```

得益于在我们的环境中启用了 KubeVirt 功能，我们正在以与创建任何其他 Kubernetes 资源相同的方式创建虚拟机。现在我们有一个虚拟机作为 Kubernetes 资源。

创建 vm 资源后，您可以使用标准的“kubectl”命令管理 VM：

```
root@c12$ kubectl get vms
NAME     AGE   STATUS    READY
testvm   18s   Stopped   False

root@c12$ kubectl get vms -o yaml testvm
apiVersion: kubevirt.io/v1                    
kind: VirtualMachine           
metadata:               
  annotations:     
    kubectl.kubernetes.io/last-applied-configuration: |
...
```

检查是否定义了 VM（使用命令`kubectl get vms`）：

```
root@c12$ kubectl get vms
NAME     AGE     STATUS    READY
testvm   2m21s   Stopped   False
```

从输出中注意到 VM 尚未运行。


### 创建 Instance

要启动 VM Instance(实例)，使用 virtctl 执行如下操作：

```
root@c12$ virtctl start testvm
VM testvm was scheduled to start
```

现在您可以再次检查 VM 状态：

```
root@c12$ kubectl get vms
NAME     AGE   STATUS     READY
testvm   3m    Starting   False
# 等待一会再次执行
NAME     AGE     STATUS    READY
testvm   3m31s   Running   True
```

VirtualMachine资源包含 VM 的Definition和Status。具有实例附加的关联资源，即VirtualMachineInstance.

虚拟机运行后，您可以检查其状态：

```
root@c12$ kubectl get vmis
NAME     AGE   PHASE     IP             NODENAME   READY
testvm   63s   Running   10.233.66.10   c14        True

root@c12$ kubectl get vmis -o yaml testvm
# output 略

```

准备就绪后，命令`kubectl get vmis`将打印如下内容：

```
root@c12$ kubectl get vmis
NAME     AGE    PHASE     IP             NODENAME   READY
testvm   109s   Running   10.233.66.10   c14        True
```

访问虚拟机（串行控制台和 vnc）

现在 VM 正在运行，您可以访问其串行控制台：

> 注意： ^]表示,按“CTRL”和“]”键退出控制台。

```
# Connect to the serial console
root@c12$ virtctl console testvm
# 显示prompt，输入用户名：'cirros' 密码：'gocubsgo'登录
testvm login: cirros
Password: 
$ id
uid=1000(cirros) gid=1000(cirros) groups=1000(cirros)
$ hostname
testvm
$ 
```


在可以访问 VNC 客户端的环境中，可以使用virtctl vnc命令访问 VM 的图形控制台。

### 关闭和清理 Definition 和 Instance

关闭 VM 还使用以下virtctl命令：

```
root@c12$ virtctl stop testvm
VM testvm was scheduled to stop

root@c12$ kubectl get vm
NAME     AGE     STATUS    READY
testvm   9m48s   Stopped   False
```

最后，可以使用以下命令删除 VM Definition：

```
root@c12$ kubectl delete vms testvm
virtualmachine.kubevirt.io "testvm" deleted
```
<!-- #endregion -->

## 总结分析

  **TODO**
