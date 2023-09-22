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

![高级概述图](/images/kubegems001_01.png)

## 如何安装

目前提供三种安装模式

    1. kubectl apply
    2. helm
    3. OperatorHub

由于我们采用了Kubegems，这里我们用kubegems的一键安装：

![一键安装](/images/kubegems001_02.png)

安装说明：

由于笔者采用的Kubegems的cert-manager是1.8.0版本，按照官方文档，建议K8S为`1.24`

## CD 持续发布

你知道如何配置你的 Cert-Manager 设置，并希望自动化这个过程。

📖 helm：你可以直接使用 Cert-Manager Helm 图表与诸如 Flux、ArgoCD 和 Anthos 等系统一起使用。

📖 helm template：你可以使用 helm template 生成自定义的 Cert-Manager 安装清单。请参阅使用 helm template 输出 YAML 获取更多详细信息。然后，你可以将这个模板化的 Cert-Manager 清单传输到你首选的部署工具中。

## 验证安装

1. 确认安装了[cmctl](https://cert-manager.io/docs/reference/cmctl/#installation)

    如果没有安装，大概流程如下：
    ```bash
    $ OS=$(go env GOOS); ARCH=$(go env GOARCH); curl -fsSL -o cmctl.tar.gz https://github.com/cert-manager/cert-manager/releases/latest/download/cmctl-$OS-$ARCH.tar.gz
    $ tar xzf cmctl.tar.gz
    $ sudo mv cmctl /usr/local/bin
    $ cmctl help

    cmctl is a CLI tool manage and configure cert-manager resources for Kubernetes

    Usage: cmctl [command]

    Available Commands:
    approve      Approve a CertificateRequest
    check        Check cert-manager components
    completion   Generate completion scripts for the cert-manager CLI
    convert      Convert cert-manager config files between different API versions
    create       Create cert-manager resources
    deny         Deny a CertificateRequest
    experimental Interact with experimental features
    help         Help about any command
    inspect      Get details on certificate related resources
    renew        Mark a Certificate for manual renewal
    status       Get details on current status of cert-manager resources
    upgrade      Tools that assist in upgrading cert-manager
    version      Print the cert-manager CLI version and the deployed cert-manager version

    Flags:
    -h, --help                           help for cmctl
        --log-flush-frequency duration   Maximum number of seconds between log flushes (default 5s)

    Use "cmctl [command] --help" for more information about a command.
    ```

2. 试一试搞个自动化证书
   
   1. 