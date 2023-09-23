# beego使用笔记

## 新建项目

## 0.安装

```shell
$go get github.com/beego/beego/v2
$go get -u github.com/beego/bee/v2
```

## 1.bee new projectname

```shell
$bee new microapi
```

## 2.初始化配置文件

```ini
appname = microapi
httpport = 30001
runmode = prod

sqlconn = "****:****@tcp(****)/****?charset=utf8mb4&loc=Local"

sessionon = true
sessionprovider = mysql
sessionproviderconfig = "****:****@tcp(****)/****?charset=utf8mb4&loc=Local"
```

## 3.初始化session数据库

```sql
CREATE TABLE `session` (
    `session_key` char(64) NOT NULL,
    `session_data` blob,
    `session_expiry` int(11) unsigned NOT NULL,
    PRIMARY KEY (`session_key`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
```

## 4.Main中加载mysql驱动

```go
package main

import (
        _ "microapi/routers"

        beego "github.com/beego/beego/v2/server/web"
        _ "github.com/beego/beego/v2/server/web/session/mysql"
        _ "github.com/go-sql-driver/mysql"
)

func main() {
        beego.Run()
}
```

## 5.新建一个Controller

```golang
package controllers

import (
        beego "github.com/beego/beego/v2/server/web"
)

type UserController struct {
        beego.Controller
}

func (c *UserController) Get() {
        c.Data["Website"] = "beego.me"
        c.Data["Email"] = "astaxie@gmail.com"
        c.TplName = "index.tpl"
}
```
