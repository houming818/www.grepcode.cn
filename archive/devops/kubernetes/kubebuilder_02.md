# [Kubebuilder实战] 教程-构建 CronJob


## 前言

### 项目目的

本教程应该带您（几乎）了解 Kubebuilder 的所有复杂性，从简单开始，逐步构建功能非常齐全的东西。

### 参考链接

[项目原链接](https://book.kubebuilder.io/cronjob-tutorial/cronjob-tutorial.html)

[案例源码](https://github.com/kubernetes-sigs/kubebuilder/tree/master/docs/book/src/cronjob-tutorial/testdata)

[参考说明](https://juejin.cn/post/6844903952241131534)

## 开始

### 搭建我们的项目

确保已经完整运行 [`[Kuberbuilder实战] 环境搭建与测试项目`](https://www.grepcode.cn/devops/kubernetes/kubebuilder_01.html) ,才能开始如下过程。

#### 初始化

```shell
# we'll use a domain of tutorial.kubebuilder.local,
# so all API groups will be <group>.tutorial.kubebuilder.local.
$ kubebuilder init --domain tutorial.kubebuilder.local
```

### 项目有什么

[参考链接](https://book.kubebuilder.io/cronjob-tutorial/basic-project.html)

### 建设基础设施

- `go.mod`：与我们的项目匹配的新 Go 模块，具有基本依赖项
- `Makefile`：为构建和部署控制器制定目标
- `PROJECT`：用于搭建新组件的 Kubebuilder 元数据

### 启动配置

### 入口点

`$ vim main.go`

>  Using RBAC Authorization的 [kubernetes 文档](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)

### 简单说明

我们的包从一些基本的导入开始。特别：

- 核心控制器运行时库
- 默认的控制器运行时日志记录，Zap（稍后会详细介绍）

每组控制器都需要一个 Scheme，它提供 Kinds 与其对应的 Go 类型之间的映射。

在编写 API 定义时，我们将更多地讨论 Kinds，因此请记住这一点以备后用。

此时，我们的主要功能相当简单：

- 我们为指标设置了一些基本标志。

- 我们实例化一个 manager，它跟踪运行我们所有的控制器，以及设置共享缓存和客户端到 API 服务器（注意我们将我们的 Scheme 告诉了 manager）。

- 我们运行我们的管理器，它依次运行我们所有的控制器和网络钩子。管理器设置为运行，直到它收到正常关闭信号。这样，当我们在 Kubernetes 上运行时，我们的行为会很好地终止 pod。

虽然我们还没有任何东西可以运行，但请记住该+kubebuilder:scaffold:builder评论在哪里 ——那里很快就会变得有趣。

您的项目范围更改为单个命名空间。在这种情况下，还建议通过将默认的 ClusterRole 和 ClusterRoleBinding 分别替换为 Role 和 RoleBinding 来限制对这个命名空间提供的授权。

### 基本概念

当我们谈论 Kubernetes 中的 API 时，我们经常使用 4 个术语：`组 groups`、`版本 versions`、`种类 kinds`和`资源 resources`。

Kubernetes 中的API `组`只是相关功能的集合,这些版本允许我们随着时间的推移改变 API 的工作方式

每个 API group-version 包含一个或多个 API 类型，我们称之为 Kinds。资源resources只是 API 中 Kind 的使用。

对于 CRD，每个 Kind 将对应一个资源。

### 添加新的API

```shell
$ kubebuilder create api --group batch --version v1 --kind CronJob
```

### 设计API

### 控制器中有什么

控制器的工作是确保对于任何给定对象，全局的实际状态（集群状态和潜在的外部状态，例如为 Kubelet 运行容器或为云提供商运行负载均衡器）与对象中的所需状态相匹配。 这个过程称作 `reconciling`

> It’s a controller’s job to ensure that, for any given object, the actual state of the world (both the cluster state, and potentially external state like running containers for Kubelet or loadbalancers for a cloud provider) matches the desired state in the object

### 实现控制器

梳理清楚控制器需要做的事情(**书写Controller的第一步**)

1. 加载命名的 CronJob

2. 列出所有活动作业，并更新状态

3. 根据历史限制清理旧作业

4. 检查我们是否被暂停（如果我们被暂停，请不要做任何其他事情）

5. 获取下一次预定运行

6. 如果新作业按计划运行，没有超过截止日期，并且没有被我们的并发策略阻止，则运行新作业

7. 当我们看到正在运行的作业（自动完成）或者是下一次计划运行的时间时重新排队。

### 实现默认/验证 webhook

### 运行和部署控制器

#### 部署证书管理器

#### 部署准入 Webhook

### 编写控制器测试
