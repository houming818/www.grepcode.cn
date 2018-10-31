---
title: docker-新建mysql服务
link_title: docker_new_mysql
categories: "docker"
description: "docker,mysql,新建"
date: 2018-10-27 16:16:15
tags: ["docker", "mysql", "新建"]
---


# 1 新建docker容器，增加mysql 5.7服务
## 1.1 拉取必须镜像
```
$ docker pull mysql/mysql-server:5.7
```
## 1.2 新建MySQL实例
启动实例：
```
$ docker run --name=std-mysql -p 3306:3306 -d mysql/mysql-server:5.7
```
查看日志：
```
$ docker logs std-mysql
```
获取默认密码：
```
$ docker logs std-mysql 2>&1 | grep GENERATED
```

## 1.3 连接MySQL服务
连接服务：
```
$ docker exec -it std-mysql mysql -uroot -p
```
变更密码：
```
mysql> SET PASSWORD = PASSWORD('******');
```
or
```
mysql> ALTER USER 'root'@'localhost' IDENTIFIED BY 'newpassword';
```
授权：
```
mysql> CREATE USER root@'%' IDENTIFIED BY '******'';
mysql> GRANT ALL ON *.* TO 'root'@'%';
mysql> flush privileges;
```

## 1.4 控制容器
停止：
$ docker stop std-mysql
启动：
$ docker start std-mysql
or
$ docker restart std-mysql
删除:
$ docker rm std-mysql
