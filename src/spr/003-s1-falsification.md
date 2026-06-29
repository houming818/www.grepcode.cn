---
title: "[SPR-003] S1 反证：token-only 路由不是语义路由"
date: 2026-06-16
weight: 3
author: nio (Houming818) & Codex Review
description: "用多义词实验反证当前 S1 token-only 路由的语义 claim。"
tags: [SPR, Falsification, Polysemy, ARA]
---

# S1 反证：token-only 路由不是语义路由

S1 的 Echo 结果很好，但 ARA 要求我们继续问：

> 什么实验会推翻“路径即语义”？

最直接的反证是同词多义。

如果一个路径系统真的编码语义，那么同一个词在不同上下文里应该能进入不同状态。

## 实验设计

选择三个多义词：

```text
light
bank
charge
```

构造 42 条受控句子：

```text
light: 光 / 轻
bank: 银行 / 河岸
charge: 费用 / 充电 / 指控
```

比较两类方法：

1. S1 token-only route。
2. keyword baseline。

然后打乱标签，检查模型是否真的依赖语义。

## 结果

```text
token_only_real_acc = 0.4286
token_only_shuffled_acc = 0.4286
keyword_real_acc = 1.0000
keyword_shuffled_acc = 0.4524
```

表格：

| 方法 | 真实标签 | 打乱标签 |
|------|----------|----------|
| S1 token-only route | 0.43 | 0.43 |
| keyword baseline | 1.00 | 0.45 |

## 解释

S1 token-only route 的输入是：

```text
route(token)
```

所以 `bank` 永远是同一个 token。它不看旁边是 `loan` 还是 `river`。

这意味着：

```text
bank approved the loan
river bank
```

在当前 S1 里没有上下文分流。

打乱标签后准确率不变，说明 S1 token-only route 没有吃到语义信号。

## 这个失败说明什么

它不推翻 S1a。

S1a 的 claim 是：

> token 可以被稳定映射到低碰撞路径。

这个 claim 仍然成立。

它推翻的是更强的说法：

> token-only path 天然就是语义。

这个说法不成立。

## ARA 状态

| Claim | 状态 |
|-------|------|
| 路径容量足够 | confirmed |
| 顺序碰撞可修复 | confirmed |
| Echo 可近乎满分 | supported |
| token-only path 能做上下文语义消歧 | rejected |
| context-conditioned path 能否做语义消歧 | open |

## 下一步

要恢复“语义路由”这个名字，路径函数必须升级：

```text
route(token)
```

变成：

```text
route(token, context)
```

否则 SPR 只是一个漂亮的路径哈希。

> **License: GPLv3**
