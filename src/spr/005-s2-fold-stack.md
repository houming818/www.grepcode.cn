---
title: "[SPR-005] S2 结构路线：Fold Stack 的位置"
date: 2026-06-16
weight: 5
author: nio (Houming818) & Codex Review
description: "S2 Fold Stack 在 SPR 中的位置：从语义向量到结构动作，而不是 Echo 的重复。"
tags: [SPR, FoldStack, S2, Structure]
---

# S2 结构路线：Fold Stack 的位置

S2 不应该被塞进 S1 Echo 的叙事里。

S1 证明的是 token path hash。S2 关心的是结构生成：

```text
semantic vector -> structural action
```

它们是相关的，但不是同一个实验。

## S2 的问题

S2 要回答：

> 给定一个语义表示，能否预测句子的结构折叠过程？

结构折叠包括：

- 哪个 token 是 head？
- span 边界在哪里？
- 当前短语是什么类型？
- 子节点应该挂到哪里？
- 图如何组装？

这些问题都比 Echo 更接近翻译和生成。

## 已有证据的含义

历史实验里有一些重要信号：

| 模块 | 观察 |
|------|------|
| action classification | 语义向量能预测部分折叠动作 |
| head detection | 头节点有可学信号 |
| span detection | 短语范围有可学信号 |
| child assignment | 仍是瓶颈 |
| graph assembly | 简单最近节点规则有上限 |

这说明 S2 路线不是空想。

但它也说明：

> 结构路线不能靠 Echo 指标证明。

BLEU 对结构错误不够敏感。有些结构错了，表面词序仍然可能看起来不错。

## S2 的关键指标

S2 应该主要看：

- UAS
- edge accuracy
- action top-k
- head F1
- span F1
- oracle gap

而不是只看 BLEU。

## S1 与 S2 怎么连接

S1a 给 token 一个稳定路径身份。

S1b 应该让这个路径吃上下文。

S2 可以提供结构上下文：

```text
fold action
head/span state
child candidate distribution
```

这些状态反过来可以影响 S1b 路由：

```text
route(token, local_context, fold_state)
```

这才是 SPR 更完整的样子。

## S2 的下一步

S2 后续需要做三件事：

1. 保留已有 fold-stack 证据，但重新绑定到 ARA claims。
2. 给每个结构 claim 加 baseline。
3. 明确哪些错误来自语义不足，哪些来自图组装不足。

如果 S2 能给 S1b 提供结构条件，SPR 才可能从 path hash 走向 semantic route。

> **License: GPLv3**
