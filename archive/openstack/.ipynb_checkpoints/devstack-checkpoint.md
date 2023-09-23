[OpenStack实战] Devstack搭建
========


## 环境

<div class="alert alert-block alert-danger" >
    
操作系统： ubuntu-18.04

python:   3.6.9
    
devstack:  stable/ussuri

注意： ubuntu-16.04和ubuntu-20.04没有安装成功
</div>



## 准备工作

1.准备系统用户及权限

```shell
$ sudo useradd -s /bin/bash -d /opt/stack -m stack
$ echo "stack ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/stack
$ sudo su - stack

```

2.下载代码

```shell
stack$ git clone https://opendev.org/openstack/devstack
stack$ cd devstack
stack$ git checkout -b ussuri origin/stable/ussuri
```



## 开始配置

1.编写配置文件

```shell
stack$ cp samples/local.conf ./
```

```
stack$ vim ./local.conf

# 编辑conf文件，添加如下行，HOST_IP填写本机真实IP
# --------
ADMIN_PASSWORD=********
DATABASE_PASSWORD=$ADMIN_PASSWORD
RABBIT_PASSWORD=$ADMIN_PASSWORD
SERVICE_PASSWORD=$ADMIN_PASSWORD

HOST_IP=10.0.2.15

PYTHON3_VERSION=3
```

2.新建必须文件

```shell
stack$ mkdir -p /opt/stack/logs/
```


## 开始执行

1.直接运行

```shell
stack$ ./stack.sh
```

2.执行结果

```
=========================
DevStack Component Timing
 (times are in seconds)  
=========================
run_process           74
test_with_retry        6
apt-get-update         5
osc                  243
wait_for_service      41
git_timed            423
dbsync                87
pip_install          1325
apt-get              798
-------------------------
Unaccounted time     1724
=========================
Total runtime        4726



This is your host IP address: 10.0.2.15
This is your host IPv6 address: ::1
Horizon is now available at http://10.0.2.15/dashboard
Keystone is serving at http://10.0.2.15/identity/
The default users are: admin and demo
The password: ********

WARNING: 
Using lib/neutron-legacy is deprecated, and it will be removed in the future


Services are running under systemd unit files.
For more information see: 
https://docs.openstack.org/devstack/latest/systemd.html

DevStack Version: ussuri
Change: 4f9c1e084c8d762c873549e8fc9524d6ee24f1c1 Make stackviz tasks not to fail jobs 2021-04-08 20:18:30 -0500
OS Version: Ubuntu 18.04 bionic
```
