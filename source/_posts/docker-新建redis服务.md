---
title: docker-新建redis服务
link_title: docker_new_redis
categories: "docker"
description: "docker,redis,新建"
date: 2018-10-27 16:12:35
tags: ["docker", "redis", "新建"]
---

# 1 新建docker容器，增加Redis服务
## 1.1 拉取必须镜像
$ docker pull redis:5.0.0
## 1.2 新建Redis实例
启动实例：
$ docker run --name=std-redis -p 6379:6379 -d redis:5.0.0
安装工具：
$ sudo apt-get install redis-tools

## 1.3 连接Redis服务
测试连接服务：
$ redis-cli -h 127.0.0.1 -p 6379
```
redis> ping
PONG
```

## 1.4 控制容器
停止：
$ docker stop std-redis
启动：
$ docker start std-redis
or
$ docker restart std-redis
删除:
$ docker rm std-redis

