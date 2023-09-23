---
title: 搭建蓝鲸
link_title: blueking002
categories:
  - 01 蓝鲸计划
tags: 运维 开发 DevOps 蓝鲸 ubuntu blueking 搭建
date: 2023-09-23 00:00:00
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

总结：

```bash

#### 准备工作 ####

$ mkdir -p ~/bin/                      
$ curl -sSf https://bkopen-1252002024.file.myqcloud.com/ce7/7.1-stable/bkdl-7.1-stable.sh -o ~/bin/bkdl-7.1-stable.sh
$ chmod +x ~/bin/bkdl-7.1-stable.sh
$ ~/bin/bkdl-7.1-stable.sh -r latest tools

$ ls $HOME/bkce7.1-install/
bin
# 检查下，看看安装目录是不是有文件

$ vim ~/.bashrc
export PATH=$HOME/bkce7.1-install/bin/:$PATH
$ source ~/.bashrc
$ which helm
/root/bkce7.1-install/bin/helm
# 确认PATH配置正确

/root/bkce7.1-install
$ tar xf ./bin/helm-plugin-diff.tgz -C ~/
# 解压helm插件

$ helm plugin list
NAME    VERSION DESCRIPTION                           
diff    3.1.3   Preview helm upgrade changes as a diff
# 查看helm插件安装是否成功

$ kubectl config set-context --current --namespace=blueking
# 配置默认命名空间

$ node_ips=$(kubectl get nodes -o jsonpath='{.items[*].status.addresses[?(@.type=="InternalIP")].address}')
$ test -f /root/.ssh/id_rsa || ssh-keygen -N '' -t rsa -f /root/.ssh/id_rsa  
# 如果不存在rsa key则创建一个。
# 开始给发现的ip添加ssh key，期间需要你输入各节点的密码。
$ for ip in $node_ips; do
  ssh-copy-id "$ip" || { echo "failed on $ip."; break; }  # 如果执行失败，则退出
done

/usr/bin/ssh-copy-id: INFO: Source of key(s) to be installed: "/root/.ssh/id_rsa.pub"
The authenticity of host '192.168.1.*3 (192.168.1.*3)' cant be established.
ECDSA key fingerprint is SHA256:**GTPw.
Are you sure you want to continue connecting (yes/no/[fingerprint])? yes
/usr/bin/ssh-copy-id: INFO: attempting to log in with the new key(s), to filter out any that are already installed

/usr/bin/ssh-copy-id: WARNING: All keys were skipped because they already exist on the remote system.
(if you think this is a mistake, you may want to use -f option)


#### 开始部署基础套餐 ####

$ ~/bin/bkdl-7.1-stable.sh -ur latest base demo nm_gse_full saas scripts

```
