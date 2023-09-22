---
title: kubegems/cert-manager使用手册
link_title: kubegems001
date: 2023-09-22 13:00:00
categories: Kubegems
tags: 运维 开发 DevOps Kubegems 证书 cert-manager
---

## 参考文档

[cert-manager官方文档](https://cert-manager.io/docs/)

    证书管理器
    cert-manager 将证书和证书颁发者添加为 Kubernetes 集群中的资源类型，并简化了获取、更新和使用这些证书的过程。

    它可以从各种受支持的来源颁发证书，包括 Let's Encrypt、HashiCorp Vault 和 Venafi 以及私有 PKI。

    它将确保证书有效且最新，并尝试在到期前的配置时间续订证书。

    它大致基于 kube-lego 的工作，并借鉴了其他类似项目（例如 kube-cert-manager）的一些智慧。

    解释证书管理器架构的高级概述图

![高级概述图](images/kubegems_01_01.png.png)