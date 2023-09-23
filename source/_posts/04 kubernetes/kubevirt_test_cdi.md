---
title: Kubevirt实战/使用 CDI 导入并启动 VM
link_title: Kubevirt002
categories:
  - 04 kubernetes
tags: 运维 开发 DevOps Kubevirt
date: 2023-09-22 13:00:00
---

## 容器化数据导入器介绍

CDI是一个实用程序，旨在导入虚拟机映像以与 Kubevirt 一起使用。

在较高级别上，创建了 PersistentVolumeClaim (PVC)。自定义controller监视导入程序的特定声明，并在发现时启动导入过程以创建名为disk.img的原始图像，并将所需内容放入关联的 PVC。

我们将首先探索每个组件，然后我们将安装它们。在本练习中，我们创建了一个主机路径配置器和存储类。此外，我们将使用 Operator 部署 CDI 组件。

### 安装主机路径供应商

下载 hostpath-provisioner 部署 YAML 并应用它。

```
root@c12$ wget https://raw.githubusercontent.com/kubevirt/hostpath-provisioner/main/deploy/kubevirt-hostpath-provisioner.yaml
root@c12$ kubectl create -f kubevirt-hostpath-provisioner.yaml
root@c12$ kubectl annotate storageclass kubevirt-hostpath-provisioner storageclass.kubernetes.io/is-default-class=true
```

验证您现在有一个默认存储类。您应该看到“kubevirt-hostpath-provisioner（默认）”

```
root@c12$ kubectl get storageclass
```

### 安装 CDI

#### 启动

获取最新版本的 CDI 并应用启动部署的 Operator 和自定义资源定义 (CR)：

```
root@c12$ export VERSION=$(curl -s https://github.com/kubevirt/containerized-data-importer/releases/latest | grep -o "v[0-9]\.[0-9]*\.[0-9]*")
```

#### 部署operator

```
root@c12$ kubectl create -f https://github.com/kubevirt/containerized-data-importer/releases/download/$VERSION/cdi-operator.yaml
```

#### 创建CRD

创建 CRD 以触发 CDI 的operator部署：

```
root@c12$ kubectl create -f https://github.com/kubevirt/containerized-data-importer/releases/download/$VERSION/cdi-cr.yaml
```

#### 检查CDI状态

检查 CDI 部署的状态。您可以根据需要重复此命令，直到 CDI "PHASE" 显示为 "Deployed"

```
root@c12$ kubectl get cdi -n cdi
```

#### 查看CDI-pod

查看已添加的“CDI”pod。

```
root@c12$ kubectl get pods -n cdi
```

#### 使用 CDI

例如，我们将导入 Fedora34 云镜像作为 PVC 并启动使用它的虚拟机。

```
root@c12$ cat <<EOF > pvc_fedora.yml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: "fedora"
  labels:
    app: containerized-data-importer
  annotations:
    cdi.kubevirt.io/storage.import.endpoint: "https://mirror.23media.com/fedora/linux/releases/34/Cloud/x86_64/images/Fedora-Cloud-Base-34-1.2.x86_64.raw.xz"
    kubevirt.io/provisionOnNode: node01
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 5500Mi
EOF

root@c12$ kubectl create -f pvc_fedora.yml
```

这将创建带有适当注释的 PVC，以便 CDI 控制器检测到它并启动导入器 pod 以收集cdi.kubevirt.io/storage.import.endpoint注释中指定的图像。

获取 pod 名称以稍后检查日志。如果 pod 尚未列出，请稍等片刻，因为 Operator 仍在执行所需的操作。

```
root@c12$ kubectl get pod
```

然后检查导入过程（这将是一个漫长的过程，可能需要一些时间）：

```
root@c12$ kubectl logs -f $(kubectl get pods -o name)
```

请注意，导入程序下载了公开可用的 Fedora Cloud qcow 映像。一旦 importer pod 完成，这个 PVC 就可以在 KubeVirt 中使用了。

如果导入器 pod 错误完成，您可能需要重试它或为 fedora 云映像指定不同的 URL。要重试，请先删除 importer pod 和 PVC，然后重新创建 PVC。

让我们创建一个使用新 PVC 的虚拟机。查看文件vm1_pvc.yml。

```
$ wget https://kubevirt.io/labs/manifests/vm1_pvc.yml
```

我们更改此虚拟机的 YAML 定义，以在云实例中注入用户的默认公钥。这个 Katacoda 场景提供了一个已设置 ssh 密钥的环境，因此我们将使用在 authorized_keys 文件中找到的公钥。

```
$ PUBKEY=$(cat ~/.ssh/authorized_keys)
$ sed -i "s%ssh-rsa YOUR_SSH_PUB_KEY_HERE%$PUBKEY%" vm1_pvc.yml
```

现在，我们将使用修补过的 YAML 创建 VM：

```
kubectl create -f vm1_pvc.yml
```

这将创建并启动一个名为 vm1 的虚拟机。我们可以使用以下命令来检查我们的虚拟机是否正在运行，并且可以gather its IP. 您正在寻找virt-launcherpod 旁边的 IP 地址。

```
kubectl get pod -o wide
```

等待虚拟机启动并可以登录。您可以通过控制台监控其进度。VM 启动的速度取决于是否使用裸机硬件。使用嵌套虚拟化时速度要慢得多，如果您在云提供商的实例上完成本实验，则可能会出现这种情况。

从这里开始，有一些在玩虚拟机，等到它启动（您可以检查控制台以查看启动进度）

最后，我们将像普通用户一样连接到 vm1 虚拟机 (VM)，即通过 ssh。这可以通过 ssh 到收集的 IP 来实现。

检查IP地址：

```
controlplane $ kubectl get vmis
NAME      AGE       PHASE     IP           NODENAME
testvm    1m        Running   10.32.0.11   controlplane
```

现在，通过 SSH 连接

```
ssh fedora@10.32.0.11
```

结束。
