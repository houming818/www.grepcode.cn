# Ego之HelloWorld

## 参考资料

1. [官网hello-world](https://ego.gocn.vip/frame/quickstart/quickstart.html#helloworld)

## 官网hello world验证

1. 新建 main.go
2. [运行命令行](https://ego.gocn.vip/frame/quickstart/quickstart.html#%E4%BD%BF%E7%94%A8%E5%91%BD%E4%BB%A4%E8%A1%8C%E8%BF%90%E8%A1%8C)

输出:

```text
$ go run main.go --config=config.toml
main.go:4:2: cannot find module providing package github.com/gin-gonic/gin: working directory is not part of a module
main.go:5:2: cannot find module providing package github.com/gotomicro/ego: working directory is not part of a module
main.go:6:2: cannot find module providing package github.com/gotomicro/ego/core/elog: working directory is not part of a module
main.go:7:2: cannot find module providing package github.com/gotomicro/ego/server/egin: working directory is not part of a module
```

## 重写hello world验证

### 获取example文件

[项目地址](https://github.com/gotomicro/ego/tree/master/examples/helloworld)

### init golang module

```text
$go mod init main
$go test
```

output:

```text
go: finding module for package github.com/gotomicro/ego/core/elog
go: finding module for package github.com/gotomicro/ego/server/egin
go: finding module for package github.com/gotomicro/ego
......
go: downloading github.com/go-playground/locales v0.13.0
?       main    [no test files]
```

### 再次尝试启动服务

```text
$go run main.go --config=config.toml
```

output:

![](../../images/helloworldego.jpg)

