---
title: "[SPR-029] 不再借外部向量：从本地共现语料训练坐标，再测 TreeHeap Kernel"
date: 2026-06-25
weight: 29
author: nio (Houming818) & Codex Review
description: "SPR-028 输给 vector_add，并不能 defeat TreeHeap，因为 frozen embedding 本来就是向量拓扑源。本文改用本地 SGNS 共现语料训练坐标，并测试结构化 TreeHeap kernel。"
tags: [SPR, TreeHeap, ARA, S1, WorldModel, Kernel]
---

# 不再借外部向量：从本地共现语料训练坐标，再测 TreeHeap Kernel

`SPR-028` 的结果是负面的：

```text
frozen all-MiniLM embedding 坐标系下，
vector_add 明显强于 TreeHeap prob vector plus。
```

但 Houming818 指出一个关键问题：

```text
这还不能 defeat TreeHeap。
```

原因是：

```text
蒸馏源的数据本来就是 vector。
```

也就是说，`all-MiniLM-L6-v2` 已经把大量世界知识压进向量空间。

在这种空间里：

```text
left + right
```

天然可能靠近：

```text
compound target
```

所以 `vector_add` 赢，不奇怪。

这更像是在测试：

```text
TreeHeap 能不能追上一个已经很强的向量空间。
```

而不是测试：

```text
TreeHeap 能不能从语料共现中建立自己的坐标。
```

## 新方案：从语料共现训练小 embedding

这次改成 C 方案：

```text
从本地小语料训练 embedding。
```

不使用预训练 embedding。

不使用外部模型坐标。

不使用 `all-MiniLM`。

坐标系来自我们自己的小语料：

```text
football means foot ball
football uses foot and ball
foot ball forms football
football belongs to ball
...
```

也就是：

```text
语料共现
-> SGNS / SkipGram negative sampling
-> 小型 128D embedding 坐标
```

这更接近我们真正关心的问题：

```text
数据中的共现信息，如何进入 TreeHeap？
```

## 实验脚本

脚本：

```text
ara/s1-echo/src/s1_corpus_embedding_kernel_probe.py
```

执行主机：

```text
io.grepcode.cn
```

证据：

```text
ara/s1-echo/evidence/s1_corpus_embedding_kernel_probe/
```

坐标来源：

```text
local SGNS corpus embedding
external_model = false
vocab_size = 85
corpus_sentences = 888
skipgram_pairs = 10448
```

这次不需要 `proxychains4`。

因为没有下载外部模型或语料。

## 为什么 kernel 设计重要？

上一版 TreeHeap 的问题之一是：

```text
reader 太自由。
```

它可以像一个普通 MLP 一样记训练集。

这不是真正的 TreeHeap 写入。

这次改成结构化 kernel：

```text
left token  -> left child
right token -> right child
root        -> compose kernel(left_child, right_child)
```

也就是：

```text
H[left]  = WriteLeft(left_vector)
H[right] = WriteRight(right_vector)
H[root]  = Compose(H[left], H[right])
```

TreeHeap 结构强制参与计算。

不是把所有节点摊平给一个大 reader。

## 对比模型

三个模型：

| Model | 含义 |
|---|---|
| `vector_add` | 直接 `normalize(left + right)` |
| `concat_mlp` | 普通 MLP，看 `[left, right, left*right, abs(left-right)]` |
| `structured_treeheap_kernel` | 左写入、右写入、root compose kernel |

## 结果

| Model | Train cosine | Test cosine | OOD cosine | OOD top1 |
|---|---:|---:|---:|---:|
| vector_add | 0.5705 | 0.5965 | 0.5785 | 0.000 |
| concat_mlp | 0.9994 | 0.6957 | 0.7321 | 0.167 |
| structured_treeheap_kernel | 0.9999 | 0.6801 | 0.7126 | 0.000 |

这次结果比 `SPR-028` 明显不同。

在本地共现坐标系里：

```text
vector_add 不再天然统治。
```

TreeHeap kernel 的 OOD cosine：

```text
0.7126
```

高于 vector_add：

```text
0.5785
```

并且接近 concat MLP：

```text
0.7321
```

所以这次 claim 是：

```text
S1-WM-C02 -> supported pilot, narrow scope
```

## 为什么说 narrow scope？

因为 OOD top1 还没解决。

TreeHeap 的 OOD top1：

```text
0.000
```

concat MLP：

```text
0.167
```

也就是说，TreeHeap 的输出向量在平均 cosine 上更接近目标，但最近邻检索还没有稳定命中目标词。

这说明：

```text
坐标接近性有进展。
离散概念坍缩还没完成。
```

这个区别很重要。

在 TreeHeap 语言里可以说：

```text
概率场靠近了目标区域，
但还没有稳定坍缩到目标点。
```

## 这证明了什么？

这次支持三件事。

第一：

```text
用本地语料共现训练坐标是可行的。
```

第二：

```text
kernel 设计会显著影响 TreeHeap 写入。
```

从自由 reader 改为：

```text
left child / right child / root compose
```

之后，TreeHeap 不再像 `SPR-028` 那样崩掉。

第三：

```text
TreeHeap 在本地共现坐标上可以超过 vector_add 的 OOD cosine。
```

这说明不能用 `SPR-028` 直接否定 TreeHeap。

## 这没有证明什么？

边界也要说清楚。

这次没有证明：

```text
TreeHeap 已经有完整世界模型。
TreeHeap 已经能翻译。
TreeHeap 击败 Transformer。
TreeHeap 在 top1 检索上胜出。
```

它只是证明：

```text
当坐标系来自本地共现语料，
并且 TreeHeap kernel 被结构化约束后，
TreeHeap 可以在 OOD cosine 上超过 vector_add。
```

这是一个小但重要的进展。

## 下一步

下一步不能只看 cosine。

要开始要求：

```text
top1
MRR
margin loss
multi-seed
corpus variants
```

尤其要加入：

```text
nearest-neighbor margin loss
```

否则模型可能只是“靠近目标区域”，但没有“坍缩到目标点”。

下一版 kernel 应该加入：

```text
family slots
subheap reuse
route collapse regularization
explicit right-side shared kernel
```

例如：

```text
ball family:
  football
  basketball
  baseball
  handball
  snowball
```

这些应该共享：

```text
ball 子堆
```

这才是 TreeHeap 可能超过普通 MLP 的地方。

## 总结

`SPR-028` 告诉我们：

```text
不能拿预训练向量空间里的 vector_add 输赢来直接判断 TreeHeap。
```

`SPR-029` 告诉我们：

```text
从本地语料共现训练坐标后，
结构化 TreeHeap kernel 可以超过 vector_add 的 OOD cosine。
```

但下一关还在那里：

```text
从靠近目标区域，
到稳定坍缩目标概念。
```

这就是下一轮 S1-WM 要打的点。
