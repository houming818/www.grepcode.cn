---
title: "[SPR-001] 问题定义：为什么要研究路径路由"
date: 2026-06-16
weight: 1
author: nio (Houming818) & Codex Review
description: "SPR 的问题定义：路径路由要解决什么问题，以及它不应该被误解成什么。"
tags: [SPR, Problem, ARA]
---

# 问题定义：为什么要研究路径路由

SPR 的原始动机不是“再造一个 Transformer”。它更像是在问一个底层问题：

> 语言模型里的某些搜索和输出，是否必须通过稠密矩阵完成？

Transformer 的强项是通用、并行、可训练。但它也有代价：大量关系被压在矩阵乘法和 softmax 里。我们能看到结果，却不容易看到结构。

SPR 试图换一个表示方式：

```text
vector score -> path decision
dense matrix -> recursive route
token id -> route state
```

## SPR 想替代什么

最初的目标是输出层或结构搜索的一部分。

传统输出层可以写成：

```text
hidden -> Linear(d, V) -> softmax -> token
```

这是一种“所有 token 一起打分”的方式。SPR 想试试另一种：

```text
hidden -> recursive decisions -> path -> candidate token/state
```

如果路径结构有效，它可能带来三个好处：

1. **参数结构更清楚**：路径上的每个节点对应一次判断。
2. **搜索空间可压缩**：不用每次都扫完整词表或完整图。
3. **结构可解释**：错误可以定位到路径分叉，而不只是一个 logits 排名。

## SPR 不应该被误解成什么

SPR 不是简单的 hash trick。

如果它只是：

```text
token -> fixed bucket
```

那它最多是高容量 token hash。

真正的 SPR 应该是：

```text
token + context + structure -> conditional path
```

也就是说，同一个词在不同上下文里可以走向不同状态。

例如：

```text
bank approved the loan -> finance state
river bank             -> river-side state
```

如果做不到这一点，就不能说“路径即语义”。

## ARA 方式怎么约束 SPR

这次重写采用 ARA 风格。每个 claim 都要回答三件事：

| 问题 | 说明 |
|------|------|
| Claim 是什么？ | 不写模糊胜利，只写可检验句子 |
| Evidence 是什么？ | 脚本、命令、指标、数据切片 |
| Falsification 是什么？ | 什么结果会推翻这个 claim |

例如：

```text
Claim: S1 token path hash has enough capacity for WMT14 word echo.
Evidence: solo=41311/41429, BLEU-4=99.99.
Falsification: same seed/slice 下 solo rate < 95%.
```

再例如：

```text
Claim: token-only path encodes contextual semantics.
Evidence: currently failed.
Falsification: same-token polysemy real labels do not beat shuffled labels.
```

## 本专题的核心问题

SPR 现在被拆成三个问题：

1. 路径作为 hash 是否可靠？
2. 路径能否被上下文条件化？
3. 路径能否服务结构生成？

第一问已经有较强证据。第二问当前失败。第三问属于 S2，需要单独看 Fold Stack 证据链。

这就是本专题后续文章的主线。

> **License: GPLv3**
