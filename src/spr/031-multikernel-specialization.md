---
title: "[SPR-031] Multi-Kernel 会自然分工吗：一次 WMT 扰动任务的混合结果"
date: 2026-06-26
weight: 31
author: nio (Houming818) & Codex Review
description: "这次实验测试 TreeHeap kernel bank 是否会像 Transformer multi-head 一样，在结构扰动任务下形成不同功能。结果是：分化信号出现了，但任务能力还没过关。"
tags: [SPR, TreeHeap, ARA, S1, WMT, Kernel, MultiHead]
---

# Multi-Kernel 会自然分工吗：一次 WMT 扰动任务的混合结果

这篇记录一个比较关键、但不能夸大的结果。

我们想验证的问题是：

```text
TreeHeap 的多个 kernel，会不会像 Transformer 的 multi-head 一样，
在训练中自然分化成不同功能？
```

结论先说：

```text
有分化信号，但还不是成功证明。
```

更准确地说：

```text
不同结构任务确实选择了不同 kernel。
删除某些 kernel 会明显伤害对应任务。
但整体任务准确率仍然低，multi-kernel 对 single-kernel 的提升还不够。
```

所以 ARA 结论是：

```text
S1-MK-C01 -> open / mixed pilot
```

## 为什么要做这个实验？

Transformer 的 multi-head attention 并不是手工规定：

```text
head_1 = 主语
head_2 = 宾语
head_3 = 长距离依存
```

而是多个 head 具有不同参数、不同初始化、不同梯度路径。
训练任务给它们压力，它们可能分化，也可能冗余。

TreeHeap 也应该这样看。

我们不应该手工说：

```text
K0 = echo kernel
K1 = mask kernel
K2 = mirror kernel
```

而应该给它一个 kernel bank：

```text
K0, K1, K2, K3
```

然后观察训练以后：

```text
不同任务是否自然偏向不同 kernel？
删除某个 kernel 是否会让某类任务明显变差？
```

## 实验数据

数据是真实 WMT17 英文侧文本：

```text
/mnt/nas/datasets/wmt17/train.zh-en
```

切词使用：

```text
/mnt/nas/datasets/wmt17/sp_bpe.model
```

样本设置：

```text
samples = 4000
train/test/ood = 3200/400/400
token length = 4..8
```

注意，这还不是翻译任务。

它是：

```text
真实语料 token
+ 人工结构扰动任务
```

这样做的原因是：我们现在要测 kernel 分化，不是 BLEU。
如果直接做翻译，错误来源太多，无法判断 kernel 是否真的在分工。

## 五个结构任务

这次不是普通 echo，而是五种任务：

| Task | 含义 |
|---|---|
| `echo` | 原样重建序列 |
| `mask_restore` | mask 一个 token 后重建原序列 |
| `left_query` | 读取左子堆 |
| `right_query` | 读取右子堆 |
| `mirror` | 输出反转序列 |

这些任务分别给 kernel 不同压力。

`echo` 要求保存地址和顺序。

`mask_restore` 要求利用上下文，不只是照抄。

`left_query` / `right_query` 要求模型知道左右子结构。

`mirror` 要求模型学习一种翻转/共轭操作。

## 模型结构

TreeHeap 模型大致是：

```text
token id
-> leaf embedding
-> 写入 complete binary heap leaves
-> internal node = kernel(left_child, right_child)
-> task query 产生 gate
-> gate 选择/混合多个 kernel
-> decoder 输出目标 token
```

single-kernel 只有一个 compose kernel：

```text
K
```

multi-kernel 有四个：

```text
K0, K1, K2, K3
```

每个内部节点都可以由多个 kernel 生成候选结果，再由 gate 混合：

```text
h_parent = sum_k gate_k(task) * K_k(h_left, h_right)
```

这就是 TreeHeap 版 multi-head 的最小类比。

## 怎么判断是否分化？

看两件事。

第一，看 gate。

如果所有任务都选同一个 kernel：

```text
echo -> K0
mask -> K0
left -> K0
right -> K0
mirror -> K0
```

那就是没有分化。

如果不同任务选不同 kernel：

```text
left -> K0
right -> K3
mirror -> K2
```

这就是分化信号。

第二，看 ablation。

也就是删除某个 kernel：

```text
drop K3
```

如果删除后 `right_query` 大幅下降，而其他任务不怎么变，那说明：

```text
K3 确实承担了 right_query 功能。
```

这比只看 gate 更可靠。

## Run A：完整词表版本

第一版使用较大的词表：

```text
vocab limit including PAD/MASK = 2049
epochs = 28
```

结果：

| Model | Params | OOD mean exact |
|---|---:|---:|
| `single_kernel_treeheap` | 4,641,545 | 0.0495 |
| `multi_kernel_treeheap` | 4,938,764 | 0.0600 |

multi-kernel 稍微更好：

```text
0.0600 - 0.0495 = 0.0105
```

但这个提升很小。

分化信号：

```text
echo         -> K2
mask_restore -> K1
left_query   -> K3
right_query  -> K3
mirror       -> K0
```

四个 kernel 都被使用了。

最大 ablation drop：

```text
0.1100
```

说明删除某个 kernel 后，某类任务确实会掉。

但是整体 exact 太低，所以不能算成功。

## Run B：常用 token 版本

第二版把词表压到更常用的 token：

```text
vocab limit including PAD/MASK = 513
epochs = 60
```

结果：

| Model | Params | OOD mean exact |
|---|---:|---:|
| `single_kernel_treeheap` | 1,286,921 | 0.1275 |
| `multi_kernel_treeheap` | 1,584,140 | 0.1420 |

multi-kernel 仍然更好：

```text
0.1420 - 0.1275 = 0.0145
```

但仍然只是小幅提升。

各任务 OOD exact：

| Task | Single | Multi |
|---|---:|---:|
| `echo` | 0.0300 | 0.0375 |
| `mask_restore` | 0.0050 | 0.0025 |
| `left_query` | 0.1475 | 0.1775 |
| `right_query` | 0.4525 | 0.4925 |
| `mirror` | 0.0025 | 0.0000 |

这里最有价值的是 subheap query。

`left_query` 和 `right_query` 都提升了。

分化信号更清楚：

```text
echo         -> K0
mask_restore -> K1
left_query   -> K0
right_query  -> K3
mirror       -> K2
```

删除 kernel 的影响也更清楚：

```text
drop K0:
  left_query exact drop = 0.1775

drop K3:
  right_query exact drop = 0.3050
```

这说明：

```text
K0 对 left_query 很重要。
K3 对 right_query 很重要。
```

这是目前最像“kernel 分工”的证据。

## 为什么仍然不是 supported？

因为 ARA 不能只看好看的部分。

这次 pass gate 是：

```text
multi OOD mean exact - single OOD mean exact >= 0.05
multi OOD mean exact >= 0.65
至少两个 task argmax kernel 被使用
max ablation exact drop >= 0.10
```

实际结果：

```text
multi 提升: 0.0105 / 0.0145
multi OOD mean exact: 0.0600 / 0.1420
unique kernels: 4
max ablation drop: 0.1100 / 0.3050
```

所以：

```text
分化指标过了。
能力指标没过。
```

因此结论只能是：

```text
open / mixed pilot
```

## 这次真正学到了什么？

第一，结构扰动确实会推动 kernel 分化。

尤其是：

```text
left_query
right_query
mirror
```

这些任务给出了不同梯度压力。

第二，现在的 root bottleneck 设计不够好。

这次模型让一个 root/subheap state 去读出整个序列。
这对 echo、mask、mirror 很难。

用一句话说：

```text
kernel 有分化迹象，但 decoder/readout 结构拖了后腿。
```

第三，echo 绝对准确不是 multi-kernel 分化的充分条件。

`SPR-030` 的 echo 做得很好，是因为它从 leaf state 读回 token。

这次为了测 subheap/mirror/mask，把读出压到 root/subheap state。
这暴露了一个新问题：

```text
TreeHeap 需要 path-conditioned read kernel，
不能只靠一个 root vector 承担所有读出。
```

## 下一步

下一步不要盲目加 kernel 数量。

应该改读出方式：

```text
selected node
+ target path query
-> read kernel
-> token
```

也就是说，读出时也要做卷积/路径查询，而不是：

```text
root vector -> 一次性吐出全序列
```

下一版实验应该围绕：

```text
path-conditioned read kernel
subheap query
mask restore
mirror
matched flat MLP baseline
small Transformer baseline
kernel dropout
```

还要测试：

```text
没有显式 task label 时，kernel 是否仍然分化。
```

因为这次 gate 使用了 task query。
这合理，但还不够自然。

## 总结

`SPR-031` 没有证明 TreeHeap multi-kernel 已经成功。

它证明的是更细的一点：

```text
结构扰动任务确实能诱导 kernel bank 出现任务相关分化。
```

但同时也暴露：

```text
当前读出结构太粗糙。
完整任务能力还不足。
```

这就是这次最重要的进展：

```text
我们不再只问“能不能 echo”，
而开始问“kernel 是否真的分工，以及为什么分工后还不够强”。
```

下一步应该围绕：

```text
path-conditioned read kernel
```

继续推进。
