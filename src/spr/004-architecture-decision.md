---
title: "[SPR-004] 架构决策：把 SPR 拆成三层"
date: 2026-06-16
weight: 4
author: nio (Houming818) & Codex Review
description: "SPR 的新架构划分：S1a Token Path Hash、S1b Context Routing、S2 Fold Stack。"
tags: [SPR, Architecture, Decision]
---

# 架构决策：把 SPR 拆成三层

旧叙事把 SPR 写成一条直线：

```text
路径 -> 语义 -> 翻译
```

重做实验后，这条线太粗了。它应该拆成三层。

## S1a：Token Path Hash

输入：

```text
token embedding
```

输出：

```text
stable path / combined leaf
```

能力：

- 高容量。
- 低碰撞。
- 顺序哈希可修复。
- 可复现。

限制：

- 不看上下文。
- 不区分多义。
- 不应该被叫作语义路由。

S1a 是地基。

## S1b：Context-conditioned Routing

输入应该升级为：

```text
token + context
```

可能的最小形式：

```python
H_token = E[token]
H_ctx = mean(E[context_window])
H = normalize(H_token + A @ H_ctx)
path = route(H)
```

这时同一个 token 才可能在不同上下文里走不同路径。

受控 proof 已经验证了这个最小接口的方向：

```text
token-only acc = 0.429
context-route acc = 1.000
shuffled-label acc = 0.482
```

这说明路径算子能承载上下文消歧，但前提是 context vector 真的带有 sense signal。它还不是完整语料结论。

S1b 的验收标准不是 BLEU，而是：

```text
real labels > shuffled labels
context route > token-only route
context route > random hash
```

## S2：Fold Stack / Structure Routing

S2 不是 Echo 的延长线，而是结构路线。

它的问题是：

> 语义向量能否预测结构动作？

S2 关心：

- head detection
- span detection
- fold action classification
- child assignment
- graph assembly

这里的关键指标不是单纯 BLEU，而是结构质量，例如 UAS。

## 新接口

更合理的 SPR 管线是：

```text
L0 token identity
  -> S1a token path hash
  -> S1b context-conditioned path
  -> S2 fold action / structure state
```

或者反过来让 S2 给 S1b 提供结构条件：

```text
token + local context + fold state -> conditional path
```

这样路径才有机会成为“语义前缀”。

## 决策

从现在开始：

1. S1a 只称为 Token Path Hash。
2. 不再把 Echo 结果写成语义证明。
3. S1b 必须通过多义词和 shuffle 反证。
4. S2 单独维护结构证据链。

这让 SPR 更保守，也更专业：S1b 现在可以被称为受控支持，不能被称为真实语料已验证。

> **License: GPLv3**
