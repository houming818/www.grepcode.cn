---
title: "[SPR-007] S1b proof：上下文条件路由到底证明了什么"
date: 2026-06-16
weight: 7
author: nio (Houming818) & Codex Review
description: "重写 SPR 历史结论：context-conditioned route 在受控 proof 中成立，但它不是完整语义路由证明。"
tags: [SPR, Proof, ContextRouting, ARA]
---

# S1b proof：上下文条件路由到底证明了什么

前面的反证已经把话说清楚了：

```text
route(token)
```

不是语义路由。它能稳定、低碰撞地给 token 分配路径，但同一个 `bank` 在 `loan` 和 `river` 旁边仍然是同一个 `bank`。

这篇文章补上 proof：如果把输入升级成：

```text
route(token, context)
```

当前 S1 路径算子有没有能力把同词多义分开？

答案是：在受控 proof 里可以。但这个答案必须读完整。

## 实验脚本

脚本位置：

```text
holds/SameTime/experiments/spr_context_proof.py
```

远端复现命令：

```bash
cd /data/homecicd/sametime/code/wmt
python3 spr_context_proof.py
```

它使用三个目标词：

```text
light: illumination / weight
bank: finance / river
charge: money / electric / legal
```

总样本数是 56。每个样本由目标词和一组上下文词构成。

## 设计要点

实验比较三条路线：

| 路线 | 输入 | 目的 |
|------|------|------|
| token-only | `token` | 检查旧 S1a 能不能自己消歧 |
| context route | `token + context` | 检查 S1b 的最小接口是否可行 |
| shuffled context | `token + context`，但 sense 标签打乱 | 检查结果是否真的依赖语义标签 |

路径仍然使用 S1 的分块树路由：

```text
dim=64
chunks=4
depth=7
route_bits = roll + sign_alt
```

分类方式也故意保持简单：同一目标词内部做 leave-one-out 1NN，用路径 bit 的 Hamming 距离找最近邻。

这不是为了追求复杂模型，而是为了回答一个更小的问题：

> 如果上下文信号进入 route，路径空间本身能不能承载消歧？

## 结果

io 上的输出摘要：

```text
examples=56
targets=bank, charge, light
token_acc=0.429
context_acc=1.000
shuffled_acc=0.482
context_purity=1.000
mixed_context_buckets=0
```

对应表格：

| 指标 | 数值 | 含义 |
|------|------|------|
| token-only accuracy | 0.429 | 旧 S1a 不能区分同词多义 |
| context-route accuracy | 1.000 | 受控上下文进入 route 后可以分开 sense |
| shuffled-label accuracy | 0.482 | 标签打乱后优势坍塌 |
| context path purity | 1.000 | 同一路径桶内没有混合 sense |

这个结果把 S1b 从“纯猜想”推进到“机制上可行”。

## 它证明什么

它证明：

- S1 的路径算子不只适合 token identity。
- 当输入向量里真的包含上下文信号时，路径可以随上下文变化。
- 同一个 token 可以在不同上下文下进入不同稳定路径。
- label shuffle 会破坏这个优势，因此实验不是只靠样本数量或标签先验赢。

用 ARA 的说法：

```text
S1a = Token Path Hash
S1b = Context-conditioned Routing
```

这个 proof 支持 S1b 的接口方向。

## 它不证明什么

它不证明：

- 真实语料中的上下文向量已经干净携带 sense。
- SPR 在多义词消歧上优于 BoW、keyword、MLP 或 random hash。
- 翻译质量会因为 S1b 自动提升。
- “路径即语义”可以恢复成一句无条件口号。

这点很重要。当前 proof 里的上下文词向量是按 sense anchor 生成的。也就是说，实验刻意保证上下文里有可用语义信号。

因此它证明的是路径机制的承载能力，不是真实语料的端到端能力。

## 历史结论怎么修正

旧结论里有三层说法混在一起：

| 历史说法 | 新状态 | 原因 |
|----------|--------|------|
| S1 路径空间容量足够 | 保留 | Echo 和 solo leaf 结果可复现 |
| `roll + sign_alt` 修复顺序碰撞 | 保留 | 反向 toy case 已验证 |
| Echo 高分说明语义路由成立 | 降级 | Echo 也可能是高容量查表 |
| token-only path 是语义状态 | 拒绝 | 多义词反证失败 |
| context-conditioned path 可以承载消歧 | 受控支持 | 本 proof 通过，但还不是真实语料结论 |

所以新的 SPR 叙事应该是：

```text
S1a 证明路径基础设施可用。
S1a 不证明语义。
S1b 在受控 proof 中证明 route(token, context) 是正确方向。
S1b 还需要真实语料、random-hash、BoW 和多 seed 基线战。
```

## 架构决策

从现在开始，SPR 的代码和文章都应该避免把 `route(token)` 写成语义路由。

更专业的接口是：

```python
H_token = E[token]
H_ctx = context_encoder(window)
H = normalize(H_token + A @ H_ctx)
path = route(H)
```

如果 S2 fold state 可用，还应该继续扩展：

```text
token + local context + fold state -> conditional path
```

这才是 SPR 可能成为“语义前缀路由”的位置。

## 下一道门

下一步不是再证明一次受控样本，而是做真实基线战：

```text
context SPR > token-only route
context SPR > matched random hash
context SPR >= cheap BoW/keyword baseline on the task it claims to solve
real labels > shuffled labels across multiple seeds
```

只有过了这些门，S1b 才能从受控 proof 进入工程 claim。

> **License: GPLv3**
