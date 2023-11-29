---
title: ITSM开发环境搭建
link_title: blueking_itsm_01
categories:
  - 01 蓝鲸
tags: 
  - DevOps
  - 蓝鲸
  - blueking
  - ITSM
  - 二次开发
date: 2023-11-28 17:00:00
---

环境说明：

```bash
$ kubectl get nodes -o wide
NAME   STATUS   ROLES                         AGE     VERSION   INTERNAL-IP     EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION      CONTAINER-RUNTIME
fe     Ready    worker                        6d22h   v1.20.4   192.168.1.106   <none>        Ubuntu 20.04.4 LTS   5.4.0-166-generic   containerd://1.6.24
ne     Ready    control-plane,master,worker   6d22h   v1.20.4   192.168.1.103   <none>        Ubuntu 20.04.4 LTS   5.15.0-88-generic   containerd://1.6.24
```

|域名|端口|用途|
| - | - | - |
|dev-web.ftjd.org| 8004 | 提供web服务，浏览器输入dev-web.ftjd.org:8004可以访问开发的ITSM|
|dev-api.ftjd.org| 8005 | 提供ITSM的API服务，在dev的webpack包中配置该地址|

开发环境和开发代码位于ne（192.168.1.103）上。可以直接连通到K8S内部svc和pod。


前置操作：

> 1. 安装蓝鲸7.1及环境配置
> 2. 在Saas中安装ITSM，用于初始化ITSM依赖中间件和数据库

环境准备：

- 配置后端MySQL服务Redis服务RabbitMQ服务

```bash

$ kubectl get svc |grep -P 'bk-mysql-mysql|bk-redis-master|bk-rabbitmq'

bk-mysql-mysql                               ClusterIP   10.233.58.89    <none>        3306/TCP                                                                          6d4h
bk-rabbitmq                                  ClusterIP   10.233.20.81    <none>        5672/TCP,4369/TCP,25672/TCP,15672/TCP                                             6d4h
bk-rabbitmq-headless                         ClusterIP   None            <none>        4369/TCP,5672/TCP,25672/TCP,15672/TCP                                             6d4h
bk-redis-master                              ClusterIP   10.233.59.161   <none>        6379/TCP                                                                          6d4h

# 配置好hosts，这样开发代码就能访问中间件和数据库了。
@ne$ vim /etc/hosts
10.233.58.89 bk-mysql-mysql.blueking.svc.cluster.local
10.233.20.81 bk-rabbitmq.blueking.svc.cluster.local
10.233.59.161 bk-redis-master.blueking.svc.cluster.local
```

- 安装环境

    [参考官方文档](https://github.com/TencentBlueKing/bk-itsm/blob/master/docs/install/dev_deploy.md)

  - 安装 python 和包
  ```
  apt install libev-dev libjpeg-dev zlib1g-dev libevent-dev python3-all-dev
  pip install -r requirements.txt
  pip uninstall typing_extensions
  pip install typing_extensions
  pip install blueapps
  # 如果有包安装问题，一个个解决
  ```

  - 配置环境变量
  
  ```bash
  # 新建一个dev.env
  
  $ kubectl -n bkapp-bk0us0itsm-prod exec -it bkapp-bk0us0itsm-prod--web-7559ccd4d4-2rt76 bash

  # 获取环境变量
  > env | grep -i BK

  # 输出配置为dev.env
  ```

  - 打包并收集前端静态资源

    > 注意：node版本是14.21.3
    >
    > 需要安装python2

```bash
# 1）安装依赖包
# 进入 frontend/pc/，执行以下命令安装

cnpm install node-sass --legacy-peer-deps
cnpm install --legacy-peer-deps

# 如果安装失败，手动清理npm缓存
cnpm cache clean --force

# 2) 变更 frontend/pc/build/webpack.dev.conf.js

// 本地代理地址
const HOST = 'ftjd.org'
const ORIGIN = `http://${HOST}`
const SET_URL = ''


# 2）本地打包 在 frontend/desktop/ 目录下，继续执行以下命令打包前端静态资源

cnpm run dev

> itsm@1.0.0 dev /data/cn.grepcode/blueking/bk-itsm/frontend/pc
> cross-env webpack-dev-server --progress --config ./build/webpack.dev.conf.js

Happy[happy-babel-js]: Version: 5.0.1. Threads: 24 (shared pool)
ℹ ｢wds｣: Project is running at http://dev.ftjd.org:8004/
ℹ ｢wds｣: webpack output is served from /
ℹ ｢wds｣: Content not from webpack is served from /data/cn.grepcode/blueking/bk-itsm/static
Happy[happy-babel-js]: All set; signaling webpack to proceed.

```

  - 启动后端服务

```bash
python manage.py runserver 0.0.0.0:8005
```

最终效果图

![最终效果图](/images/blueking_itsm_01_01.png)