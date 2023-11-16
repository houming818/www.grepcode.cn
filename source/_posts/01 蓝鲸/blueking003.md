---
title: 蓝鲸重置密码
link_title: blueking003
categories:
  - 01 蓝鲸
tags: 
  - 运维 
  - 开发 
  - DevOps 
  - 蓝鲸 
  - ubuntu 
  - blueking 
  - 密码重置
date: 2023-09-26 00:00:00
---

## 场景说明

有的时候，忘记了密码。如果登录采用的是蓝鲸本地账号登录。可以采用如下方法重置密码。

```bash
##### 登录login Pod
$ kubectl -n blueking exec -it bk-user-api-web-d7569b476-9kn4d bash

root@bk-login-web-dddd7868d-n2g9r:/app#

$ python manage.py shell

>>> from bkuser_core.profiles.models import Profile
>>> from django.contrib.auth.hashers import make_password
>>> admin = Profile.objects.get(username='admin', domain='default.local')
>>> admin.password = make_password("********")
>>> admin.save()

```
