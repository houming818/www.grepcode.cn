---
title: 如何使用外部MySQL
link_title: blueking006
categories:
  - 01 蓝鲸计划
tags: 运维 开发 DevOps 蓝鲸 blueking 外部数据库 MySQL MongoDB
date: 2023-11-16 18:00:00
---


## 变更environments/default/values.yaml

1. 禁用bitnami中的MySQL和MongoDB

```
### Storage Settings
# 是否安装内置的bitnami charts的各类存储
bitnamiMysql:
  enabled: false
bitnamiRedis:
  enabled: true
bitnamiRedisCluster:
  enabled: true
bitnamiMongodb:
  enabled: true
bitnamiElasticsearch:
  enabled: true

## 配置外部MySQL
# 集群内一定要可访问
mysql:
  # 处于同一集群可以使用k8s service 名
  host: "mysql.ftjd.org"
  port: 3306
  rootPassword: ********
  # 默认平台和saas都复用该mysql示例时，请分配大一点的磁盘空间给数据盘。
  size: 50Gi

```

初始化MySQL数据库

```
## seq=first
CREATE DATABASE bkauth CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE bk_apigateway CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE bk_esb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE open_paas CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

## seq=second
CREATE DATABASE bk_log_search CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE bk_login CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
