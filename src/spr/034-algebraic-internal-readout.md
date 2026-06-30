---
title: "[SPR-034] 从 checksum 退一步：先读 TreeHeap 内部节点的自然属性"
date: 2026-06-29
weight: 34
author: nio (Houming818) & Codex Review
description: "SPR-034 把 SPR-032 的内部节点 checksum 失败拆开：如果 read kernel 已经能走到 internal node，那么应该先读取 length、first、last、prefix 这种 TreeHeap 自然属性，而不是任意 checksum。实验显示 routed internal readout 明显强于 root bottleneck。residue 只保留为旁路诊断，不作为本 claim 的判断条件。"
tags: [SPR, TreeHeap, ARA, S1, Read Kernel, Algebraic Readout]
---

# 从 checksum 退一步：先读 TreeHeap 内部节点的自然属性

SPR-032 做了一件很关键的事：

```text
从 arr[1] 出发，
用 stop / left / right 递归地走到目标节点。
```

结果是好的，也是不完整的。

好的部分是：

```text
路径坍缩基本成立。
叶子节点读取几乎解决。
```

不完整的部分是：

```text
internal node 的 arbitrary checksum 读得很差。
```

当时容易得出一个过强结论：

```text
internal node state 没有学到东西。
```

SPR-033 修正了这个理解。
internal state 不一定没信息，它可能像 hash 或 latent vector 一样，需要正确的 decoder 才能读懂。

所以 SPR-034 问的是一个更小、更准确的问题：

```text
如果 read kernel 已经走到了 internal node，
我们是不是应该先读 TreeHeap 自然拥有的结构属性，
而不是强行预测一个任意 checksum bucket？
```

这篇就是这个实验。

## 什么叫自然属性

假设一句短句被写入一棵 TreeHeap。

例如：

```text
[the, cat, eats, fish]
```

叶子节点保存 token。
内部节点覆盖一段子树。

比如某个 internal node 覆盖：

```text
[cat, eats]
```

那么这个节点天然有一些可以问的问题：

| 属性 | 问的是什么 |
|---|---|
| `length` | 这个子树里有几个非空 token |
| `first` | 这个子树第一个 token 是什么 |
| `last` | 这个子树最后一个 token 是什么 |
| `prefix0` | 第一个有序槽位是什么 |
| `prefix1` | 第二个有序槽位是什么 |

这些问题很自然。

它们类似十进制数字里的：

```text
百位是什么？
十位是什么？
个位是什么？
长度是多少？
```

也类似数组或树里的：

```text
这个子区间多长？
第一个元素是谁？
最后一个元素是谁？
前两个有序槽位是什么？
```

我在脚本里还保留了一个 `residue` 诊断项。
但这里需要说清楚：它不是 SPR-034 的核心 claim。

你提出 residue，是为了讨论一维有序数组折叠成树时，是否会出现某种模周期或循环结构。
这个想法更接近后续“线性顺序如何折叠成树”的数学问题，不应该压到本次 S1 readout proof 上。
所以在本文里，`residue` 只作为旁路数据记录，不参与通过/失败判断。

## 实验设计

这次仍然不是翻译任务。
它是 S1 阶段的 readout proof。

数据来自真实 WMT17 英文侧，并用 SentencePiece 切成 BPE token。

```text
host = io.grepcode.cn
samples = 5000
train/test/ood = 4000/500/500
sentence length = 4..8
vocab limit = 513
device = cuda
```

实验比较三个读法。

| 模型 | 含义 |
|---|---|
| `root_query_decoder` | 只看整棵树的 root state，再加 query node id，直接猜答案 |
| `routed_state_decoder` | 假设 SPR-032 的 read kernel 已经走到目标节点，只看目标 node state 来读答案 |
| `algebraic_oracle` | 按 TreeHeap 地址直接计算答案，0 参数，作为数学上界 |

这三个模型回答同样的问题：

```text
给定一棵 TreeHeap 和一个 query node，
输出这个节点覆盖子树的 length / first / last / prefix0 / prefix1。
```

这里的关键对比是：

```text
root bottleneck
vs
routed internal node state
```

如果 TreeHeap 的地址和子结构真的有用，那么走到目标节点之后再读，应该比让 root 一口气背下所有信息更容易。

## 主实验：自然属性 readout

先看 internal node 的 OOD 结果。

| Model | Length | First | Last | Prefix0 | Prefix1 |
|---|---:|---:|---:|---:|---:|
| `root_query_decoder` | 0.8388 | 0.5543 | 0.2387 | 0.5543 | 0.3756 |
| `routed_state_decoder` | 0.9886 | 0.9277 | 0.8725 | 0.9267 | 0.8725 |
| `algebraic_oracle` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

这个表说明一件很清楚的事：

```text
走到目标节点之后，
读自然结构属性明显更容易。
```

逐项看：

```text
length:  0.8388 -> 0.9886
first:   0.5543 -> 0.9277
last:    0.2387 -> 0.8725
prefix0: 0.5543 -> 0.9267
prefix1: 0.3756 -> 0.8725
```

也就是说：

```text
TreeHeap node state 对 length / first / last / prefix 很友好。
```

这和预期一致。
因为 `first`、`last`、`prefix` 本质上是地址/路径读法。
它们直接使用了 TreeHeap 的有序叶子、路径和子树覆盖关系。

## 旁路诊断：residue 不作为本次 claim

实验里还记录了 `residue`。
这是一个旁路诊断，不是 SPR-034 的主线。

我跑了两个版本：

```text
residue_buckets = 64
residue_buckets = 16
```

结果显示：

```text
64 buckets: routed residue = 0.3675
16 buckets: routed residue = 0.5203
```

这个结果可以先放着。

```text
residue 可能和“线性顺序如何折叠成树”的模周期问题有关，
但它不决定 SPR-034 是否成立。
```

换句话说，SPR-034 不是在证明 TreeHeap 的模运算。
SPR-034 只证明一件更稳的事：

```text
到达 internal node 后，
自然子树属性比 arbitrary checksum 更适合作为第一批 readout 目标。
```

## 这证明了什么

我把这次 claim 定为：

```text
S1-READ-C02:
After a read kernel reaches an internal node,
the first readout targets should be algebraically natural subheap attributes,
not arbitrary checksum labels.
```

状态是：

```text
supported pilot
```

支持的部分：

```text
routed internal node state
明显强于 root bottleneck。
```

尤其是：

```text
length  接近 0.99
first   接近 0.93
last    0.87
prefix0 接近 0.93
prefix1 0.87
```

这说明 TreeHeap 的地址、路径、子结构不是摆设。
当 query 已经落到具体子树，读这个子树自己的自然属性，比从 root 里硬猜所有东西更容易。

## 这没有证明什么

它没有证明翻译。

它没有证明语义 phrase meaning。

它没有证明 route 可以完全无监督学出来。

它没有证明长句法树。

它也没有证明 TreeHeap 已经胜过 Transformer 或 pointer network。

它也没有证明 residue/mod 这条线。

这次证明的只是一个更底层的点：

```text
TreeHeap internal node 可以成为一个可读的局部结构对象。
但要读什么，必须符合 TreeHeap 的地址、路径和子结构。
```

## 为什么这对 S1 重要

之前我们容易把 S1 理解成：

```text
把所有信息压到 root，
然后从 root 直接 decoder。
```

这个路线很像把一整棵树拍扁成一个向量。

SPR-032 和 SPR-034 共同说明，TreeHeap 更自然的 read 方式应该是：

```text
1. 从 arr[1] 出发。
2. 用 stop / left / right 走到目标节点。
3. 在目标节点读局部子树属性。
4. 如果信息不足，保留概率容器，不要过早坍缩。
```

这更像树上的卷积读法。

kernel 不是一次性看全局，而是在结构上移动、停下、读取。

## 下一步

SPR-035 我建议做三件事。

第一，加 baseline。

需要比较：

```text
flat MLP
pointer network
small Transformer read baseline
```

如果这些 baseline 也能同样好，那么 TreeHeap 的优势就不成立。

第二，把 SPR-032 和 SPR-034 接起来。

这次 `routed_state_decoder` 假设目标节点已经选中。
下一步应该让：

```text
probabilistic route distribution
->
natural algebraic readout
```

连成一个端到端过程。

第三，另开一条“线性顺序折叠成树”的数学实验。

这里可以再讨论 residue。
但那应该是另一个 claim：

```text
一维有序数组 -> TreeHeap
是否需要模周期 / folding kernel / cyclic address 来解释。
```

它不应该污染 SPR-034 的自然读出结论。

## 总结

SPR-034 的一句话结论是：

```text
不要先让 internal node 预测任意 checksum。
先让它读 TreeHeap 自然的结构属性。
```

实验支持这个判断。

`length / first / last / prefix` 已经表现出很强的 routed read 优势。
`residue / mod` 只是旁路诊断，后面可以另开数学折叠实验。

所以 S1 现在不是停在“internal node 读不懂”。
更准确地说是：

```text
internal node 能读，
但 decoder 必须尊重 TreeHeap 的地址、路径和子结构。
```

这就是从 SPR-032 到 SPR-034 的推进。

> **ARA**: [claims](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/claims.md) / [experiments](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/experiments.md) / [evidence](https://github.com/houming818/sametime/tree/main/ara/s1-echo/evidence/)
