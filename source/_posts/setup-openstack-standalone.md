---
title: openstack-最小环境搭建记录
link_title: openstack_standalone_setup
date: 2017-09-18 14:08:56
tags:
---
[TOC]

> 参考资料
>
> [官方链接: 如何搭建最小化openstack开发环境](https://docs.openstack.org/install-guide/openstack-services.html#minimal-deployment)
> 

# 配置环境
```bash
$ sudo apt-get install python-openstackclient
```

# 安装认证服务 Identity service
> [官方链接](https://docs.openstack.org/liberty/install-guide-ubuntu/keystone-install.html)

## 1 数据库配置

### 1.1 安装MySQL [参考:在ubuntu 16.04安装MySQL-Server](https://www.digitalocean.com/community/tutorials/how-to-install-mysql-on-ubuntu-16-04)
```bash
$ apt-get install mysql-server
```

### 1.2 配置MySQL
#### 1.2.1 权限配置
```bash
$ mysql -u root -p
mysql> GRANT ALL PRIVILEGES ON keystone.* TO 'keystone'@'localhost' IDENTIFIED BY 'KEYSTONE_DBPASS';
mysql> GRANT ALL PRIVILEGES ON keystone.* TO 'keystone'@'%' IDENTIFIED BY 'KEYSTONE_DBPASS';
```
#### 1.2.2 新建数据库实例
```bash
mysql> CREATE DATABASE keystone;
```

> 保存 KEYSTONE_DBPASS 备用

## 2 安装Keystone service
### 2.1 从源安装
```bash
$ echo "manual" > /etc/init/keystone.override
$ apt-get install keystone apache2 libapache2-mod-wsgi memcached python-memcache
```
### 2.2 设置配置文件 /etc/keystone/keystone.conf
```
#生成个随机密码作为 ADMIN_TOKEN
[DEFAULT]
admin_token = ADMIN_TOKEN
verbose = True
[database]
connection = mysql+pymysql://keystone:KEYSTONE_DBPASS@127.0.0.1:3306/keystone
[memcache]
servers = localhost:11211
[token]
provider = uuid
driver = memcache
[revoke]
driver = sql
```
配置结果
```
$ grep -P '^[^#].+' /etc/keystone/keystone.conf
[DEFAULT]
admin_token = ADMIN_TOKEN
verbose = true
log_dir = /var/log/keystone
[assignment]
[auth]
[cache]
[catalog]
[cors]
[cors.subdomain]
[credential]
[database]
connection = mysql+pymysql://keystone:KEYSTONE_DBPASS@127.0.0.1:3306/keystone
[domain_config]
[endpoint_filter]
[endpoint_policy]
[eventlet_server]
[eventlet_server_ssl]
[federation]
[fernet_tokens]
[identity]
[identity_mapping]
[kvs]
[ldap]
[matchmaker_redis]
[memcache]
servers = localhost:11211
[oauth1]
[os_inherit]
[oslo_messaging_amqp]
[oslo_messaging_notifications]
[oslo_messaging_rabbit]
[oslo_middleware]
[oslo_policy]
[paste_deploy]
[policy]
[resource]
[revoke]
driver = sql
[role]
[saml]
[shadow_users]
[signing]
[ssl]
[token]
provider = uuid
driver = memcache
[tokenless_auth]
[trust]
[extra_headers]
Distribution = Ubuntu
```

### 2.3 初始化数据库

```bash
$ /bin/sh -c "keystone-manage db_sync" keystone
```

> **!!! 错误与异常**
> ```
> Option "verbose" from group "DEFAULT" is deprecated for removal.  Its value may be silently ignored in the future.
> ```
> 参考链接中的Database配置为controller.需要改为127.0.0.1+端口

## 3 安装配置Apache HTTP Server

### 3.1 编辑 /etc/apache2/apache2.conf

```
ServerName controller
```
配置结果
```
$ grep -P '^[^#]' /etc/apache2/apache2.conf
Mutex file:${APACHE_LOCK_DIR} default
PidFile ${APACHE_PID_FILE}
Timeout 300
KeepAlive On
MaxKeepAliveRequests 100
KeepAliveTimeout 5
User ${APACHE_RUN_USER}
Group ${APACHE_RUN_GROUP}
HostnameLookups Off
ErrorLog ${APACHE_LOG_DIR}/error.log
LogLevel warn
IncludeOptional mods-enabled/*.load
IncludeOptional mods-enabled/*.conf
Include ports.conf
<Directory />
        Options FollowSymLinks
        AllowOverride None
        Require all denied
</Directory>
<Directory /usr/share>
        AllowOverride None
        Require all granted
</Directory>
<Directory /var/www/>
        Options Indexes FollowSymLinks
        AllowOverride None
        Require all granted
</Directory>
AccessFileName .htaccess
<FilesMatch "^\.ht">
        Require all denied
</FilesMatch>
LogFormat "%v:%p %h %l %u %t \"%r\" %>s %O \"%{Referer}i\" \"%{User-Agent}i\"" vhost_combined
LogFormat "%h %l %u %t \"%r\" %>s %O \"%{Referer}i\" \"%{User-Agent}i\"" combined
LogFormat "%h %l %u %t \"%r\" %>s %O" common
LogFormat "%{Referer}i -> %U" referer
LogFormat "%{User-agent}i" agent
IncludeOptional conf-enabled/*.conf
IncludeOptional sites-enabled/*.conf
ServerName controller
```

### 3.2 编辑 /etc/apache2/sites-available/wsgi-keystone.conf

```
Listen 5000
Listen 35357

<VirtualHost *:5000>
    WSGIDaemonProcess keystone-public processes=5 threads=1 user=keystone group=keystone display-name=%{GROUP}
    WSGIProcessGroup keystone-public
    WSGIScriptAlias / /usr/bin/keystone-wsgi-public
    WSGIApplicationGroup %{GLOBAL}
    WSGIPassAuthorization On
    <IfVersion >= 2.4>
      ErrorLogFormat "%{cu}t %M"
    </IfVersion>
    ErrorLog /var/log/apache2/keystone.log
    CustomLog /var/log/apache2/keystone_access.log combined

    <Directory /usr/bin>
        <IfVersion >= 2.4>
            Require all granted
        </IfVersion>
        <IfVersion < 2.4>
            Order allow,deny
            Allow from all
        </IfVersion>
    </Directory>
</VirtualHost>

<VirtualHost *:35357>
    WSGIDaemonProcess keystone-admin processes=5 threads=1 user=keystone group=keystone display-name=%{GROUP}
    WSGIProcessGroup keystone-admin
    WSGIScriptAlias / /usr/bin/keystone-wsgi-admin
    WSGIApplicationGroup %{GLOBAL}
    WSGIPassAuthorization On
    <IfVersion >= 2.4>
      ErrorLogFormat "%{cu}t %M"
    </IfVersion>
    ErrorLog /var/log/apache2/keystone.log
    CustomLog /var/log/apache2/keystone_access.log combined

    <Directory /usr/bin>
        <IfVersion >= 2.4>
            Require all granted
        </IfVersion>
        <IfVersion < 2.4>
            Order allow,deny
            Allow from all
        </IfVersion>
    </Directory>
</VirtualHost>
```

### 3.3 通过软连接启用wsgi服务

```bash
$ ln -s /etc/apache2/sites-available/wsgi-keystone.conf /etc/apache2/sites-enabled
```
## 4 启动服务

```bash
$ service apache2 restart
```

## 5 新建服务entity和api endpoint

```bash
$ read -s ADMIN_TOKEN; export OS_TOKEN=$ADMIN_TOKEN
$ export OS_URL=http://127.0.0.1:35357/v3
$ export OS_IDENTITY_API_VERSION=3
$ openstack service create --name keystone --description "OpenStack Identity" identity
+-------------+----------------------------------+
| Field       | Value                            |
+-------------+----------------------------------+
| description | OpenStack Identity               |
| enabled     | True                             |
| id          | 6a49f3baf5a54e00a2ec80ff1a93ef7f |
| name        | keystone                         |
| type        | identity                         |
+-------------+----------------------------------+
$ openstack endpoint create --region RegionOne identity public http://127.0.0.1:5000/v2.0
+--------------+----------------------------------+
| Field        | Value                            |
+--------------+----------------------------------+
| enabled      | True                             |
| id           | a29f21ed744a4422b368db6c5272004c |
| interface    | public                           |
| region       | RegionOne                        |
| region_id    | RegionOne                        |
| service_id   | 6a49f3baf5a54e00a2ec80ff1a93ef7f |
| service_name | keystone                         |
| service_type | identity                         |
| url          | http://127.0.0.1:5000/v2.0       |
+--------------+----------------------------------+
$ openstack endpoint create --region RegionOne identity internal http://127.0.0.1:5000/v2.0
+--------------+----------------------------------+
| Field        | Value                            |
+--------------+----------------------------------+
| enabled      | True                             |
| id           | 9376897e4ded4fdd9e6d557d29313bc9 |
| interface    | internal                         |
| region       | RegionOne                        |
| region_id    | RegionOne                        |
| service_id   | 6a49f3baf5a54e00a2ec80ff1a93ef7f |
| service_name | keystone                         |
| service_type | identity                         |
| url          | http://127.0.0.1:5000/v2.0       |
+--------------+----------------------------------+
$ openstack endpoint create --region RegionOne identity admin http://127.0.0.1:35357/v2.0
+--------------+----------------------------------+
| Field        | Value                            |
+--------------+----------------------------------+
| enabled      | True                             |
| id           | cbdff53a744644f48a9859f8b14b3d1d |
| interface    | admin                            |
| region       | RegionOne                        |
| region_id    | RegionOne                        |
| service_id   | 6a49f3baf5a54e00a2ec80ff1a93ef7f |
| service_name | keystone                         |
| service_type | identity                         |
| url          | http://127.0.0.1:35357/v2.0      |
+--------------+----------------------------------+
```

## 6 新建项目(project),用户(user),角色(role)

> [原文链接](https://docs.openstack.org/liberty/install-guide-ubuntu/keystone-users.html)

### 6.1 新建管理项目

```bash
$ export DOMAIN=grepcode.cn
$ openstack domain create $DOMAIN
+-------------+----------------------------------+
| Field       | Value                            |
+-------------+----------------------------------+
| description |                                  |
| enabled     | True                             |
| id          | 54c57ce57f7c4182b32764e17d332097 |
| name        | grepcode.cn                      |
+-------------+----------------------------------+
$ openstack project create --domain $DOMAIN --description "Admin Project" admin
+-------------+----------------------------------+
| Field       | Value                            |
+-------------+----------------------------------+
| description | Admin Project                    |
| domain_id   | 54c57ce57f7c4182b32764e17d332097 |
| enabled     | True                             |
| id          | fe97e8c8fcdd4100b0e9c0ca4a9be60d |
| is_domain   | False                            |
| name        | admin                            |
| parent_id   | 54c57ce57f7c4182b32764e17d332097 |
+-------------+----------------------------------+
$ openstack user create --domain $DOMAIN --password-prompt admin
User Password:
Repeat User Password:
+-----------+----------------------------------+
| Field     | Value                            |
+-----------+----------------------------------+
| domain_id | 54c57ce57f7c4182b32764e17d332097 |
| enabled   | True                             |
| id        | 6ed74fe811604851979f8736d24afce6 |
| name      | admin                            |
+-----------+----------------------------------+
$ openstack role create admin
+-----------+----------------------------------+
| Field     | Value                            |
+-----------+----------------------------------+
| domain_id | None                             |
| id        | e43201e85312466ca3fde5cff187eb6f |
| name      | admin                            |
+-----------+----------------------------------+
$ openstack role add --project admin --user admin admin
```

### 6.2 新建Service项目

> This guide uses a service project that contains a unique user for each service that you add to your environment. Create the `service` project
> 
> 译: 手册中所使用的每一个服务项目都包含一个单独唯一的用户.新建服务.

```
$ openstack project create --domain $DOMAIN --description "Service Project" service
+-------------+----------------------------------+
| Field       | Value                            |
+-------------+----------------------------------+
| description | Service Project                  |
| domain_id   | 54c57ce57f7c4182b32764e17d332097 |
| enabled     | True                             |
| id          | bb4ec1805e4f43188313e5642fbe6099 |
| is_domain   | False                            |
| name        | service                          |
| parent_id   | 54c57ce57f7c4182b32764e17d332097 |
+-------------+----------------------------------+
```

### 6.3 新建demo项目

```bash
$ openstack project create --domain $DOMAIN --description "Main Project" main
+-------------+----------------------------------+
| Field       | Value                            |
+-------------+----------------------------------+
| description | Main Project                     |
| domain_id   | 54c57ce57f7c4182b32764e17d332097 |
| enabled     | True                             |
| id          | b147698bd84f46309a3e500efeef7ec7 |
| is_domain   | False                            |
| name        | main                             |
| parent_id   | 54c57ce57f7c4182b32764e17d332097 |
+-------------+----------------------------------+
$ openstack user create --domain $DOMAIN --password-prompt stduolc
User Password:
Repeat User Password:
+-----------+----------------------------------+
| Field     | Value                            |
+-----------+----------------------------------+
| domain_id | 54c57ce57f7c4182b32764e17d332097 |
| enabled   | True                             |
| id        | 0f599ddbc7224449b058408379a73eff |
| name      | stduolc                          |
+-----------+----------------------------------+
$ openstack role create user
+-----------+----------------------------------+
| Field     | Value                            |
+-----------+----------------------------------+
| domain_id | None                             |
| id        | 7a7bc93c5f444deab89b460f0ea1fee1 |
| name      | user                             |
+-----------+----------------------------------+
$ openstack role add --project main --user stduolc user #增加stduolc用户到main项目的user角色
```

### 6.4 验证

#### 6.4.1 关闭临时验证机制

> Edit the `/etc/keystone/keystone-paste.ini` file and remove `admin_token_auth` from the `[pipeline:public_api]`, `[pipeline:admin_api]`, and `[pipeline:api_v3]` sections.
>
> 译: 编辑`/etc/keystone/keystone-paste.ini`,把`admin_token_auth`从`[pipeline:public_api]`, `[pipeline:admin_api]`和`[pipeline:api_v3]`三个段落里面删掉.

#### 6.4.2 重置之前的环境变量

```bash
unset OS_TOKEN OS_URL 
```

#### 6.4.3 以admin用户生成授权token

```
$ openstack --os-auth-url http://127.0.0.1:35357/v3 --os-project-domain-name $DOMAIN --os-user-domain-name $DOMAIN --os-project-name admin --os-username admin --os-auth-type password token issue
Password:
+------------+----------------------------------+
| Field      | Value                            |
+------------+----------------------------------+
| expires    | 2017-09-17T11:09:57.000000Z      |
| id         | ******************************** |
| project_id | fe97e8c8fcdd4100b0e9c0ca4a9be60d |
| user_id    | 6ed74fe811604851979f8736d24afce6 |
+------------+----------------------------------+
```

#### 6.4.4 以普通用户生成授权token

```
$ openstack --os-auth-url http://127.0.0.1:5000/v3 --os-project-domain-name $DOMAIN --os-user-domain-name $DOMAIN --os-project-name main --os-username stduolc --os-auth-type password token issue
+------------+----------------------------------+
| Field      | Value                            |
+------------+----------------------------------+
| expires    | 2017-09-17T11:14:21.000000Z      |
| id         | ******************************** |
| project_id | b147698bd84f46309a3e500efeef7ec7 |
| user_id    | 0f599ddbc7224449b058408379a73eff |
+------------+----------------------------------+
```

## 7 环境变量初始化脚本

### 7.1 管理员环境变量

```bash
export OS_PROJECT_DOMAIN_NAME=grepcode.cn
export OS_USER_DOMAIN_NAME=grepcode.cn
export OS_PROJECT_NAME=admin
export OS_TENANT_NAME=admin
export OS_USERNAME=admin
export OS_PASSWORD=********
export OS_AUTH_URL=http://127.0.0.1:35357/v3
export OS_IDENTITY_API_VERSION=3
```

### 7.2 普通用户环境变量

```bash
export OS_PROJECT_DOMAIN_NAME=grepcode.cn
export OS_USER_DOMAIN_NAME=grepcode.cn
export OS_PROJECT_NAME=main
export OS_TENANT_NAME=main
export OS_USERNAME=stduolc
export OS_PASSWORD=********
export OS_AUTH_URL=http://127.0.0.1:5000/v3
export OS_IDENTITY_API_VERSION=3
```

### 7.3 测试
```
$ openstack token issue
+------------+----------------------------------+
| Field      | Value                            |
+------------+----------------------------------+
| expires    | 2017-09-17T11:55:47.000000Z      |
| id         | ******************************** |
| project_id | b147698bd84f46309a3e500efeef7ec7 |
| user_id    | 0f599ddbc7224449b058408379a73eff |
+------------+----------------------------------+
```

### 7.4 重置环境变量

```
unset OS_PROJECT_DOMAIN_NAME
unset OS_USER_DOMAIN_NAME
unset OS_PROJECT_NAME
unset OS_TENANT_NAME
unset OS_USERNAME
unset OS_PASSWORD
unset OS_AUTH_URL
unset OS_IDENTITY_API_VERSION
```


# 安装镜像服务 Image service
> [参考链接](https://docs.openstack.org/liberty/install-guide-ubuntu/glance.html)

## 1 Image service服务介绍

服务包含以下部分
- glance-api **说明**
- glance-registry **说明**
- Database **说明**
- Storage repository for image files **说明**

## 2 安装与配置

### 2.1 准备工作

#### 2.1.1 新建数据库

- 登录
```
$ mysql -u root -p
```
- 新建数据库 
```
mysql> CREATE DATABASE glance;
```
- 授权
```
mysql> GRANT ALL PRIVILEGES ON glance.* TO 'glance'@'localhost' IDENTIFIED BY 'GLANCE_DBPASS';
mysql> GRANT ALL PRIVILEGES ON glance.* TO 'glance'@'%' IDENTIFIED BY 'GLANCE_DBPASS';
```

#### 2.1.2 初始化环境变量

```
export OS_PROJECT_DOMAIN_NAME=grepcode.cn
export OS_USER_DOMAIN_NAME=grepcode.cn
export OS_PROJECT_NAME=admin
export OS_TENANT_NAME=admin
export OS_USERNAME=admin
export OS_PASSWORD=*******
export OS_AUTH_URL=http://127.0.0.1:35357/v3
export OS_IDENTITY_API_VERSION=3
```

#### 2.1.3 建立服务认证信息.

- 新建glance用户
```
$ openstack user create --domain $DOMAIN --password-prompt glance
User Password:
Repeat User Password:
+-----------+----------------------------------+
| Field     | Value                            |
+-----------+----------------------------------+
| domain_id | 54c57ce57f7c4182b32764e17d332097 |
| enabled   | True                             |
| id        | 52c9c09d48c54e4cabdc1a291f14bbe2 |
| name      | glance                           |
+-----------+----------------------------------+
```

- 将glance用户设置为admin角色
```
openstack role add --project service --user glance admin
```

- 增加glance服务实例
```
$ openstack service create --name glance --description "OpenStack Image service" image
+-------------+----------------------------------+
| Field       | Value                            |
+-------------+----------------------------------+
| description | OpenStack Image service          |
| enabled     | True                             |
| id          | 4d39d12e921047728473f38e228a13b0 |
| name        | glance                           |
| type        | image                            |
+-------------+----------------------------------+
```

#### 2.1.4 新建Image Service Api的endpoint

```
$ openstack endpoint create --region RegionOne image public http://127.0.0.1:9292
+--------------+----------------------------------+
| Field        | Value                            |
+--------------+----------------------------------+
| enabled      | True                             |
| id           | c849c004ae1c4170a97cc9a911c9b88f |
| interface    | public                           |
| region       | RegionOne                        |
| region_id    | RegionOne                        |
| service_id   | 4d39d12e921047728473f38e228a13b0 |
| service_name | glance                           |
| service_type | image                            |
| url          | http://127.0.0.1:9292            |
+--------------+----------------------------------+
$ openstack endpoint create --region RegionOne image internal http://127.0.0.1:9292
+--------------+----------------------------------+
| Field        | Value                            |
+--------------+----------------------------------+
| enabled      | True                             |
| id           | 1f28629dc5234ebe89bd1fc5d2da08d7 |
| interface    | internal                         |
| region       | RegionOne                        |
| region_id    | RegionOne                        |
| service_id   | 4d39d12e921047728473f38e228a13b0 |
| service_name | glance                           |
| service_type | image                            |
| url          | http://127.0.0.1:9292            |
+--------------+----------------------------------+
$ openstack endpoint create --region RegionOne image admin http://127.0.0.1:9292
+--------------+----------------------------------+
| Field        | Value                            |
+--------------+----------------------------------+
| enabled      | True                             |
| id           | 9bfb11f1120e48e78cff20a4a91eaf7b |
| interface    | admin                            |
| region       | RegionOne                        |
| region_id    | RegionOne                        |
| service_id   | 4d39d12e921047728473f38e228a13b0 |
| service_name | glance                           |
| service_type | image                            |
| url          | http://127.0.0.1:9292            |
+--------------+----------------------------------+
```

### 2.3 安装与配置组件

#### 2.3.1 包安装

```
apt-get install glance python-glanceclient
```

#### 2.3.2 编辑配置文件 `/etc/glance/glance-api.conf`

```bash
$ grep -P '^[^#].+' /etc/glance/glance-api.conf
[DEFAULT]
notification_driver = noop
verbose = True
[cors]
[cors.subdomain]
[database]
backend = sqlalchemy
connection = mysql+pymysql://glance:********@127.0.0.1:3306/glance
[glance_store]
default_store = file
filesystem_store_datadir = /home/glance/images/
[image_format]
disk_formats = ami,ari,aki,vhd,vmdk,raw,qcow2,vdi,iso,root-tar
[keystone_authtoken]
auth_uri = http://127.0.0.1:5000
auth_uri = http://127.0.0.1:35357
auth_plugin = password
project_domain_name = grepcode.cn
user_domain_name = grepcode.cn
project_name = service
username = glance
password = ********
[matchmaker_redis]
[oslo_concurrency]
[oslo_messaging_amqp]
[oslo_messaging_notifications]
[oslo_messaging_rabbit]
[oslo_policy]
[paste_deploy]
flavor = keystone
[profiler]
[store_type_location_strategy]
[task]
[taskflow_executor]
```

#### 2.3.3 编辑配置文件 `/etc/glance/glance-registry.conf`

```
[DEFAULT]
notification_driver = noop
verbose = True
bind_port = 9292
[database]
backend = sqlalchemy
connection = mysql+pymysql://glance:********@127.0.0.1:3306/glance
[glance_store]
[keystone_authtoken]
auth_uri = http://127.0.0.1:5000
auth_url = http://127.0.0.1:35357
auth_type = password
project_domain_name = grepcode.cn
user_domain_name = grepcode.cn
project_name = service
username = glance
password = ********
[matchmaker_redis]
[oslo_messaging_amqp]
[oslo_messaging_notifications]
[oslo_messaging_rabbit]
[oslo_policy]
[paste_deploy]
flavor = keystone
[profiler]
```

#### 2.3.4 初始化数据库

```
$ /bin/sh -c "glance-manage db_sync" glance
```

### 2.4 收尾工作

重启服务
```
$ service glance-registry restart
$ service glance-api restart
```

## 3 验证

### 3.1 增加环境变量
```
export OS_PROJECT_DOMAIN_NAME=grepcode.cn
export OS_USER_DOMAIN_NAME=grepcode.cn
export OS_PROJECT_NAME=admin
export OS_TENANT_NAME=admin
export OS_USERNAME=admin
export OS_PASSWORD=********
export OS_AUTH_URL=http://127.0.0.1:35357/v3
export OS_IDENTITY_API_VERSION=3
export OS_IMAGE_API_VERSION=2
```

### 3.2 下载镜像
```
$ wget http://download.cirros-cloud.net/0.3.4/cirros-0.3.4-x86_64-disk.img
```

### 3.3 创建镜像
```
$ glance image-create --name "cirros" --file cirros-0.3.4-x86_64-disk.img --disk-format qcow2 --container-format bare --visibility public --progress
[=============================>] 100%
+------------------+--------------------------------------+
| Property         | Value                                |
+------------------+--------------------------------------+
| checksum         | ee1eca47dc88f4879d8a229cc70a07c6     |
| container_format | bare                                 |
| created_at       | 2017-09-18T05:44:03Z                 |
| disk_format      | qcow2                                |
| id               | a95b08df-1a39-4c33-a055-659db12be79b |
| min_disk         | 0                                    |
| min_ram          | 0                                    |
| name             | cirros                               |
| owner            | fe97e8c8fcdd4100b0e9c0ca4a9be60d     |
| protected        | False                                |
| size             | 13287936                             |
| status           | active                               |
| tags             | []                                   |
| updated_at       | 2017-09-18T05:44:04Z                 |
| virtual_size     | None                                 |
| visibility       | public                               |
+------------------+--------------------------------------+
```

## 4 错误与异常

> 建议:部署时将日志文件级别改为INFO

### 4.1 glance-registry配置错误

*错误信息:*
```
2017-09-17 20:40:09.782 20640 WARNING keystonemiddleware.auth_token [-] Using the in-process token cache is deprecated as of the 4.2.0 release and may be removed in the 5.0.0 release or the 'O' development cycle. The in-process cache causes inconsistent results and high memory usage. When the feature is removed the auth_token middleware will not cache tokens by default which mayresult in performance issues. It is recommended to use  memcache for the auth_token token cache by setting the memcached_servers option.
```

> 解决方案
>
> 在配置文件中增加如下配置信息:
> ```
> [keystone_authtoken]
> ...
> memcached_servers = 127.0.0.1:11211
> ```
> [参考链接](https://bugs.launchpad.net/openstack-chef/+bug/1661753)

### 4.2 glance-api配置错误

*错误信息:*
```
2017-09-17 21:03:52.561 23129 ERROR glance MissingRequiredOptions: Auth plugin requires parameters which were not given: auth_url
```
> 解决方案
> 将配置`/etc/glance/glance-api.conf`中`auth_uri`改为`auth_url` 

*错误信息:*
```
2017-09-17 21:04:14.570 23214 WARNING keystonemiddleware.auth_token [-] Configuring auth_uri to point to the public identity endpoint is required; clients may not be able to authenticate against an admin endpoint
```
> 未遇到问题,待解决

*错误信息:*
```
2017-09-17 21:04:14.547 23214 WARNING oslo_config.cfg [-] Option "notification_driver" from group "DEFAULT" is deprecated. Use option "driver" from group "oslo_messaging_notifications".
```
> 未遇到问题,待解决

# 安装计算服务 Compute service

# 安装网络服务 Networking service

# 安装控制面板 Dashboard 

# 安装块存储服务 Block Storage service
