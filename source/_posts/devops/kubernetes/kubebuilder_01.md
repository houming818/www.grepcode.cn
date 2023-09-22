---
title: Kubebuilder/实战环境搭建与测试项目
link_title: Kubebuilder001
date: 2023-09-22 13:00:00
categories: Kubebuilder实战
tags: 运维 开发 DevOps Kubebuilder
---

[参考地址-helloworld](https://book.kubebuilder.io/quick-start.html)

[中文说明1](https://juejin.cn/post/6844903952241131534)


## 安装

安装 kubebuilder

```shell
os=$(go env GOOS)
arch=$(go env GOARCH)

# 下载 kubebuilder 并解压到 tmp 目录中
curl -L -o kubebuilder https://go.kubebuilder.io/dl/latest/$(go env GOOS)/$(go env GOARCH)
chmod +x kubebuilder && mv kubebuilder /usr/local/bin
```



## 创建一个项目

```shell
$ mkdir $GOPATH/src/kubehello
$ cd $GOPATH/src/kubehello
$ kubebuilder init --domain kubehello.local --repo kubehello.local/guestbook
```

## 配置Registry的密钥

```shell
$ kubectl create secret docker-registry regcred --namespace=kubehello-system --docker-server=**** --docker-username=**** --docker-password=**** --docker-email=stdhi@grepcode.cn
```


## 创建一个 API

```shell
$ kubebuilder create api --group webapp --version v1 --kind Guestbook
```

## 测试

```shell
$ make install
$ make run
```

## 配置Registry授权

编辑 `./config/manager/manager.yaml`

```shell
...
    spec:
      securityContext:
        runAsNonRoot: true
      imagePullSecrets:
        - name: regcred
      containers:
      - command:
...
```

## 安装Resource

```shell
$ kubectl apply -f config/samples/
```

## 在Cluster运行

```
# 打包Example镜像
$ make docker-build docker-push IMG=hm.grepcode.cn:55582/guestbook:latest

# 部署Example镜像
$ make deploy IMG=hm.grepcode.cn:55582/guestbook:latest
```

## 删除CRDs

```
$ make uninstall
```

## 卸载Controller

```
$ make undeploy
```
