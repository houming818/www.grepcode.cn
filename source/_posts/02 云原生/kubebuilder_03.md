---
title: Kubebuilder实战/OAM学习笔记x01
link_title: Kubebuilder003
date: 2023-09-22 14:00:00
categories: Kubebuilder实战
tags: 运维 开发 DevOps Kubebuilder
---

基于 kubevela 的源码分析。

## 参考资料

环境配置 [link](https://www.grepcode.cn/2023/Kubebuilder001/)

WorkloadTrait架构分析, [link](https://xie.infoq.cn/article/17ca767b516610c5c53f7725f)

KubeVela参考资料一 [link](https://kubevela.io/docs/install)

## 实验操作

```shell
# 初始化mod
$ go mod init oam.yigong.pub

# 初始化kubebuilder
$ kubebuilder init --domain oam.yigong.pub

# 新建API
$ kubebuilder create api --group oam.yigong.pub --version v1 --kind CronJob
```

## 编写代码

servicetrait_types.go

```golang
type ServiceTraitStatus struct {
	runtimev1alpha1.ConditionedStatus `json:",inline"`

	// Resources managed by this service trait
	Resources []runtimev1alpha1.TypedReference `json:"resources,omitempty"`
}
```
