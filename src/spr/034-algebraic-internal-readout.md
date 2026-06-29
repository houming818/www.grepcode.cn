---
title: "[SPR-034] 从 checksum 退一步：先读懂 TreeHeap 内部节点的代数属性"
date: 2026-06-29
weight: 34
author: nio (Houming818) & Codex Review
description: "SPR-034 把 SPR-032 的内部节点 checksum 失败拆开：如果 read kernel 已经能走到 internal node，那么应该先读取 length、first、last、prefix 这种 TreeHeap 自然属性，而不是任意 checksum。实验显示 routed internal readout 明显强于 root bottleneck，但 residue/mod 仍然是硬点。"
tags: [SPR, TreeHeap, ARA, S1, Read Kernel, Algebraic Readout]
---

# 从 checksum 退一步：先读懂 TreeHeap 内部节点的代数属性

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
internal node 的 checksum 读得很差。
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
我们是不是应该先读 TreeHeap 自然拥有的代数属性，
而不是强行预测一个任意 checksum bucket？
```

这篇就是这个实验。

## 什么叫“代数属性”

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
| `residue` | 对这个子树做一个取模 checksum |

前五个很自然。

它们类似十进制数字里的：

```text
百位是什么？
十位是什么？
个位是什么？
长度是多少？
```

`residue` 更难。
它不是直接读某个位置，而是要求模型把整段子树做一种模运算摘要。
所以我预期它会比 `length / first / last / prefix` 更难。

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
输出这个节点覆盖子树的 length / first / last / residue / prefix0 / prefix1。
```

这里的关键对比是：

```text
root bottleneck
vs
routed internal node state
```

如果 TreeHeap 的地址和子结构真的有用，那么走到目标节点之后再读，应该比让 root 一口气背下所有信息更容易。

## 主实验：64 个 residue bucket

先看 internal node 的 OOD 结果。

| Model | Length | First | Last | Residue | Prefix0 | Prefix1 | Mean | Exact all |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `root_query_decoder` | 0.8388 | 0.5543 | 0.2387 | 0.0847 | 0.5543 | 0.3756 | 0.4411 | 0.0516 |
| `routed_state_decoder` | 0.9886 | 0.9277 | 0.8725 | 0.3675 | 0.9267 | 0.8725 | 0.8259 | 0.3571 |
| `algebraic_oracle` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

这个表说明两件事。

第一，走到目标节点之后，读自然属性明显更容易。

```text
internal mean:
root   = 0.4411
routed = 0.8259
gain   = +0.3849
```

第二，`residue` 仍然很差。

```text
routed residue = 0.3675
```

也就是说：

```text
TreeHeap node state 对 length / first / last / prefix 很友好，
但对取模 checksum 还不够友好。
```

这和预期一致。
因为 `first`、`last`、`prefix` 是地址/路径读法。
`residue` 更像一个整段摘要，需要更专门的有限域或 mod kernel。

## 诊断实验：把 residue 从 64 桶降到 16 桶

为了确认是不是 residue 太细，我又跑了一个诊断实验。

唯一变化是：

```text
residue_buckets = 16
```

结果：

| Model | Length | First | Last | Residue | Prefix0 | Prefix1 | Mean | Exact all |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `root_query_decoder` | 0.8527 | 0.5624 | 0.2303 | 0.1087 | 0.5637 | 0.3675 | 0.4476 | 0.0380 |
| `routed_state_decoder` | 0.9919 | 0.9355 | 0.9011 | 0.5203 | 0.9367 | 0.8849 | 0.8617 | 0.4755 |
| `algebraic_oracle` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

这次 residue 从：

```text
0.3675 -> 0.5203
```

有提升，但仍然没有解决。

所以结论更清楚了：

```text
residue 不是完全没信号，
但当前 kernel 不擅长稳定学习这种模摘要。
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
supported / mixed pilot
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
last    0.87 到 0.90
prefix0 接近 0.93
prefix1 0.87 到 0.88
```

这说明 TreeHeap 的地址、路径、子结构不是摆设。
当 query 已经落到具体子树，读这个子树自己的自然属性，比从 root 里硬猜所有东西更容易。

## 这没有证明什么

它没有证明翻译。

它没有证明语义 phrase meaning。

它没有证明 route 可以完全无监督学出来。

它没有证明长句法树。

它也没有证明 TreeHeap 已经胜过 Transformer 或 pointer network。

这次证明的只是一个更底层的点：

```text
TreeHeap internal node 可以成为一个可读的局部结构对象。
但要读什么，必须符合 TreeHeap 的代数结构。
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

第一，做 residue-aware kernel。

现在的 `residue` 弱，说明普通 MLP readout 没有自动学好模运算。
可以给 TreeHeap 增加有限域槽位，或者设计专门的 mod kernel。

第二，加 baseline。

需要比较：

```text
flat MLP
pointer network
small Transformer read baseline
```

如果这些 baseline 也能同样好，那么 TreeHeap 的优势就不成立。

第三，把 SPR-032 和 SPR-034 接起来。

这次 `routed_state_decoder` 假设目标节点已经选中。
下一步应该让：

```text
probabilistic route distribution
->
algebraic readout
```

连成一个端到端过程。

## 总结

SPR-034 的一句话结论是：

```text
不要先让 internal node 预测任意 checksum。
先让它读 TreeHeap 自然的代数属性。
```

实验支持这个判断。

`length / first / last / prefix` 已经表现出很强的 routed read 优势。
`residue / mod` 仍然是开放问题。

所以 S1 现在不是停在“internal node 读不懂”。
更准确地说是：

```text
internal node 能读，
但 decoder 必须尊重 TreeHeap 的地址、路径和子结构代数。
```

这就是从 SPR-032 到 SPR-034 的推进。
