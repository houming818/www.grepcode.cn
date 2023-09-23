---
title: kubernetes运维/搭建单点Kubernetes cluster
link_title: kubernetes001
categories:
  - 04 kubernetes
tags: 运维 开发 DevOps 搭建环境
date: 2023-09-22 13:00:00
---

## 配置与环境

```
硬件: 4Cpu 16G 1T Nvidia-GTX-1650
OS: Ubuntu-20.04
```

[参考链接](https://computingforgeeks.com/deploy-kubernetes-cluster-on-ubuntu-with-kubeadm/)


## 执行步骤

### 升级系统组件到最新组件

```shell
$ sudo apt update
$ sudo apt -y upgrade
$ sudo systemctl reboot
```


### 安装 `kubelet kubeadm kubectl`

配置安装源

```shell
$ sudo apt update
$ sudo apt -y install curl apt-transport-https
$ curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
$ echo "deb https://apt.kubernetes.io/ kubernetes-xenial main" | sudo tee /etc/apt/sources.list.d/kubernetes.list
```

安装包

```shell
$ sudo apt update
$ sudo apt -y install vim git curl wget kubelet kubeadm kubectl
$ sudo apt-mark hold kubelet kubeadm kubectl
```

确认版本

```shell
$ kubectl version --client && kubeadm version
Client Version: version.Info{Major:"1", Minor:"21", GitVersion:"v1.21.0", GitCommit:"cb303e613a121a29364f75cc67d3d580833a7479", GitTreeState:"clean", BuildDate:"2021-04-08T16:31:21Z", GoVersion:"go1.16.1", Compiler:"gc", Platform:"linux/amd64"}
kubeadm version: &version.Info{Major:"1", Minor:"21", GitVersion:"v1.21.0", GitCommit:"cb303e613a121a29364f75cc67d3d580833a7479", GitTreeState:"clean", BuildDate:"2021-04-08T16:30:03Z", GoVersion:"go1.16.1", Compiler:"gc", Platform:"linux/amd64"}
```



### 配置

关闭 swap 分区

配置sysctl

```shell
$ sudo modprobe overlay
$ sudo modprobe br_netfilter

$ sudo tee /etc/sysctl.d/kubernetes.conf<<EOF
net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
net.ipv4.ip_forward = 1
EOF

$ sudo sysctl --system
```


### 安装容器引擎-docker

### 初始化节点

确保br_netfilter mod加载成功

```shell
$ lsmod | grep br_netfilter
br_netfilter           28672  0
bridge                192512  1 br_netfilter
```

启动kubelet

```shell
$ sudo systemctl enable kubelet
```

拉取镜像

```shell
$ sudo kubeadm config images pull
```

kubeadm 初始化

```shell
$ sudo kubeadm init \
  --pod-network-cidr=192.168.3.0/24 \
  --control-plane-endpoint=k8s.grepcode.cn
```


### 访问权限配置

```shell
$ mkdir -p $HOME/.kube
$ sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
$ sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

添加自动补全

```shell
$ sudo bash -c 'kubectl completion bash >/etc/bash_completion.d/kubectl'
```


### 安装网络组件

```shell
$ kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml
```

### 设置master非污点

```shell
$ kubectl taint node h2 node-role.kubernetes.io/master-
```
