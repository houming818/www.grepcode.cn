---
title: 如何使用外部MySQL
link_title: blueking006
categories:
  - 01 蓝鲸
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
CREATE DATABASE IF NOT EXISTS open_paas DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bk_login DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bkauth DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bkiam DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bkiam_saas DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bkssm DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bk_apigateway DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bk_esb DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bk_user_api DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bk_user_saas DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bkpaas3_engine DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bkpaas3_apiserver DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bkpaas3_svc_mysql DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bkpaas3_svc_bkrepo DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bkpaas3_svc_rabbitmq DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bkpaas3_svc_otel DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bk_monitor DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bk_monitor_grafana DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bk_log_search DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bklog_grafana DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bk_nodeman DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bk_dbm DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bk_dbm_grafana DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bk_dbm_dbconfig DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bk_dbm_dbpriv DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bk_dbm_dbpartition DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bk_dbm_dbsimulation DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bk_dbm_dns DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
CREATE DATABASE IF NOT EXISTS bk_dbm_hadb DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
```
