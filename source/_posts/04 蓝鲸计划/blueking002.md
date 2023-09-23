---
title: 搭建蓝鲸
link_title: blueking002
date: 2023-09-23 00:00:00
categories: blueking
tags: 运维 开发 DevOps 蓝鲸 blueking 搭建
---

## 参考链接

1. [准备中控机](https://bk.tencent.com/docs/markdown/ZH/DeploymentGuides/7.1/prepare-bkctrl.md)

2. [快速部署基础套餐](https://bk.tencent.com/docs/markdown/ZH/DeploymentGuides/7.0/install-bkce.md)

## 过程说明

蓝鲸基础套餐的部署过程大致可以分为 5 个阶段：

    1. 完善配置文件
    2. 部署存储服务
    3. 部署后台服务
    4. 完善 SaaS 运行环境
    5. 部署 SaaS：流程服务和标准运维

详细内容，从参考文件一条条看。

总结概述：

```bash
$ mkdir -p ~/bin/                      
$ curl -sSf https://bkopen-1252002024.file.myqcloud.com/ce7/7.1-stable/bkdl-7.1-stable.sh -o ~/bin/bkdl-7.1-stable.sh
$ chmod +x ~/bin/bkdl-7.1-stable.sh
$ ~/bin/bkdl-7.1-stable.sh -r latest tools


```