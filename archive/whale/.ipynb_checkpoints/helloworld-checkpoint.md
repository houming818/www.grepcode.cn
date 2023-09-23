[蓝鲸]最小化学习环境搭建
========


## 参考链接

[环境准备](https://bk.tencent.com/docs/document/6.0/127/7543?r=1)

[单点安装过程](https://bk.tencent.com/docs/document/6.0/127/7551)

## 配置说明

|主机名|主机IP|配置|操作系统|
|---|---|---|---|
|o16| 192.168.1.16 | 2c4g40g | CentOS-7 |
|o17| 192.168.1.17 | 2c4g40g | CentOS-7 |
|o18| 192.168.1.18 | 2c4g40g | CentOS-7 |
|跳板机| 略 | 略 | 略 |


## 快速配置

1.从官网下载基础套餐，并解压到 /data/ 下。实际版本请以蓝鲸官网下载为准。

```shell
$ tar xf bkce_basic_suite-6.0.3.tgz -C /data

#获取机器的 MAC 地址后，下载[证书文件](https://bk.tencent.com/download_ssl/)，解压到 src/cert 目录下
$ install -d -m 755 /data/src/cert
$ tar xf ssl_certificates.tar.gz -C /data/src/cert

#解压各个产品软件包
$ cd /data/src/; for f in *gz;do tar xf $f; done

#拷贝 rpm 软件包
$ cp -a /data/src/yum /opt
```

2.修改 bk_install 脚本

```shell
# 在 job 处添加以下内容
$ vim /data/install/bk_install
$ sed -i '/JAVA_OPTS/c JAVA_OPTS="-Xms128m -Xmx128m"' /etc/sysconfig/bk-job-*
```

![](../../images/change_job.png)

3.install.config 这个文件安装脚本会自动生成，无需自行配置。

## 快速搭建

1.如果部署全部组件，请执行：

```shell
$ cd /data/install
$ export SSH_CONNECTION="192.168.1.123 8804 192.168.1.16 22"
$ ./install_minibk -y 
```

2.安装过程中遇到失败的情况，请先定位排查解决后，再重新运行失败时的安装指令。执行完部署后，执行降低内存消耗脚本。以确保环境的稳定

```
# 临时修复：执行 tweak 操作后 open_paas uWsgi 参数中 cheaper > workers 的问题
# 感谢[广州六子](https://bk.tencent.com/s-mart/personal/1283/)的反馈
sed -i '/^cheaper/d' /data/bkce/etc/uwsgi-*.ini 

# 执行降低内存消耗脚本
bash bin/single_host_low_memory_config.sh tweak all
```

