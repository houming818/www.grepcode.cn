beego之配置开发环境
========


## 开发环境说明

```
OS:      ubuntu-18.04
Editor:    vim
go version: go1.16.4 linux/amd64
```

- go安装请参考 [参考资料一](https://golang.org/doc/install)
- vim配置vimrc参考 [参考资料二](https://www.grepcode.cn/stdrc/vimrc.txt)


## 代码初始化

### 下载github上beego代码

1.先fork代码

略

2.然后git clone

```shell
$ git clone git@github.com:stdhi/beego.git
```

3.配置upstream源为github上的官方源码

```shell
$ git remote add upstream https://github.com/beego/beego.git
```

### 新建测试项目

1.测试项目初始化

```shell
$ go get github.com/beego/bee/v2
$ bee new hellobee
$ cd hellobee/
$ go get .
```

2.配置beego源码路径

```shell
$ vim go.mod
```

```golang
module hellobee

go 1.16

replace github.com/beego/beego/v2 => /data/workspace/beego

require github.com/beego/beego/v2 v2.0.1

require github.com/smartystreets/goconvey v1.6.4
```

```shell
$ bee run
```

![image.png](../../images/beego_initdev_01.png)

3.验证beego的代码已经生效
变更beego源码

./beego/server/web/server.go

```golang

func NewHttpSever() *HttpServer {
    log.Println("SETUP OK!")
    return NewHttpServerWithCfg(BConfig)              
} 
```

![image.png](../../images/beego_initdev_02.png)

<div class="alert alert-block alert-info">
    可以开始开发调试beego了！！！
</div>
