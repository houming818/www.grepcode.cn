---
title: "[SPR-006] 下一轮实验：从 proof 走向真实基线战"
date: 2026-06-16
weight: 6
author: nio (Houming818) & Codex Review
description: "SPR 下一轮实验计划：把受控 context proof 放进真实语料、随机哈希和 BoW 基线战。"
tags: [SPR, ExperimentPlan, ContextRouting, Baseline]
---

# 下一轮实验：从 proof 走向真实基线战

S1a 已经成立。S1b 的受控 proof 也已经跑通：

```text
token_acc=0.429
context_acc=1.000
shuffled_acc=0.482
```

但这还不够。下一轮实验目标不是继续提高 Echo，也不是重复受控 proof，而是把 S1b 放进真实语料和强基线里。

## 最小模型

从一个小模型开始：

```python
H_token = E[token]
H_ctx = mean(E[left_window + right_window])
H = normalize(H_token + A @ H_ctx)
path = route(H)
```

这里 `A` 是小矩阵，不是大模型。目标不是追求榜单分数，而是验证路径会不会随上下文变。

## 第一关：真实语料多义词

继续使用：

```text
light
bank
charge
```

要求：

| 指标 | 通过条件 |
|------|----------|
| real-label accuracy | 高于 token-only |
| shuffled-label accuracy | 明显下降 |
| random hash | 低于 context SPR |
| keyword / BoW baseline | 作为 sanity check |

如果真实标签和打乱标签差不多，实验失败。

受控样本已经通过；下一步必须从语料中抽取真实上下文，避免上下文向量被人工 sense anchor 喂得过干净。

## 第二关：随机哈希

构造同样容量的 random hash：

```text
same dim
same chunks
same depth
same leaf count
```

如果 SPR 和 random hash 差不多，说明路径结构没有语义贡献。

## 第三关：BoW 小模型

用一个简单上下文模型做基线：

```text
bag of context words -> sense
```

这不是为了赢 SPR，而是为了防止 SPR 对一个简单任务说大话。

如果 BoW 轻松解决，SPR 至少要解释自己为什么更有价值：

- 更可组合？
- 更适合结构生成？
- 更能接 fold state？

## 第四关：接 S2 fold state

如果局部窗口不够，就把 S2 的结构信号接进来：

```text
token
local context
head/span/fold state
-> conditional path
```

这一步才可能让路径带上句法和语义角色。

## 输出要求

每次实验必须输出：

```text
seed
dataset slice
target words
token-only metric
context-route metric
random-hash metric
BoW or keyword metric
shuffled-label metric
claim decision
```

结果必须写回：

```text
ara/s1-echo/evidence/README.md
ara/s1-echo/logic/claims.md
```

## 通过标准

只有满足下面条件，S1b 才能从受控 supported 进入工程 supported：

```text
context SPR > token-only route
context SPR > random hash
real labels > shuffled labels
```

如果还要升级成 verified，还需要跨数据切片和多 seed 稳定。

> **License: GPLv3**
