---
title: "[SPR-010] 世界模型守夜训练：新 checkpoint 给了什么证据"
date: 2026-06-18
weight: 10
author: nio (Houming818) & Codex Review
description: "用 ARA 方式记录一次 10 小时 TreeHeap world-model 守夜训练：它证明了什么，没有证明什么，下一步 predict 应该怎么改。"
tags: [SPR, TreeHeap, WorldModel, ARA, Evidence]
---

# 世界模型守夜训练：新 checkpoint 给了什么证据

上一篇文章统一了术语：

```text
L0 词法基底
World Model 世界模型
Participation Product 参与乘积
t_merge 读出层
Frame of Reference 参考系
Latent Slot 潜在槽位
Probability Container 概率容器
```

统一术语以后，下一步不能继续只靠聊天里的直觉。
按照 ARA 的正规流程，我们需要先写一个可以失败的 predict，然后跑实验。

这次守夜任务就是围绕这个 predict 做的。

## 先说结论

这次实验是一次**有效的诊断证据**，但不是 TreeHeap 世界模型成立的正证明。

结论分三层：

```text
1. 工程上：
   新 checkpoint 训练成功，GPU 稳定，evidence 已保存。

2. 几何上：
   新训练没有复现旧 checkpoint 那种 raw cosine 全部挤在一起的严重坍缩。
   t_merge 没有把空间直接压坏。

3. 理论上：
   当前 local BPE context 训练目标没有证明 P-FRAME01。
   也就是说，仅靠“预测附近 token”不足以学出我们想要的世界模型参考系。
```

如果只用一句话说：

> 这次实验说明，TreeHeap 的工程管线能跑，空间没有被 t_merge 直接毁掉；但世界模型拓扑信号还没有被当前 objective 学出来。

这很重要，因为它把问题从：

```text
TreeHeap 是不是彻底错了？
```

缩小成：

```text
我们现在的训练目标是不是不对？
```

我现在更倾向后者。

## 这次 predict 是什么

我们写下的 predict 叫：

```text
P-FRAME01
```

它的意思是：

```text
如果 TreeHeap 的世界模型携带真实拓扑信息，
那么复合概念相对基础概念的差分方向，
应该能在某些局部参考系里投影到可解释关系。
```

用本科生能理解的例子说：

```text
football - ball
```

应该更像：

```text
foot
kick
field
goal
```

而：

```text
basketball - ball
```

应该更像：

```text
hand
throw
court
basket
```

这不是在问：

```text
football 和 basketball 像不像？
```

而是在问：

```text
football 比 ball 多出来的那一部分，指向什么世界关系？
```

如果向量空间真的带有“世界模型”，那么这种差分方向应该不是随机的。

## 为什么要训新 checkpoint

之前我们一直有一个问题：

```text
旧 checkpoint 能不能当证据？
```

答案是：不能直接背书。

旧 checkpoint 可以作为诊断对象，因为它告诉我们：

```text
raw tree output cosine mean ≈ 0.985
```

看起来所有 token 都很像。

但进一步诊断又发现：

```text
centered cosine mean ≈ 0
```

也就是说，它可能不是所有信息都没了，而是有一个很强的公共背景方向。

所以旧 checkpoint 不能直接证明 TreeHeap 成立，也不能直接证明 TreeHeap 失败。
它只能告诉我们：

```text
必须自己训一个新的 checkpoint，
再看 CMul、merge_no_bias、tree、centered tree 到底发生了什么。
```

这次守夜任务就是为了补这一块 evidence。

## 训练任务怎么设计

这次没有训练完整翻译模型，也没有训练大语言模型。

我们训练的是一个小的 TreeHeap-style world-model checkpoint。

核心形式是：

```text
L0(token)
  x WorldPath(token)
  -> CMul pre-merge state
  -> t_merge
  -> token-in-world vector
```

训练目标很朴素：

```text
给定一个中心 BPE token，
让它的 token-in-world vector 去找附近窗口里的真实 context token。
```

也就是 local context contrastive learning。

用更普通的话说：

```text
如果一个 token 经常和某些上下文一起出现，
模型应该把它变换到一个能找回这些上下文的位置。
```

这不是最终目标。
它只是一个可运行、可保存 checkpoint、可观察 t_merge 是否扭曲空间的中间实验。

## 守夜运行规模

运行时间：

```text
start:  2026-06-17 18:05:58
finish: 2026-06-18 04:06:01
```

训练规模：

```text
epochs recorded: 456
global steps:    2,732,508
checkpoints:     456
metrics rows:    456
frame rows:      2,280
geometry rows:   2,280
gpu rows:        54,650
```

证据保存位置：

```text
/data/homecicd/sametime/ara/s2-translation/evidence/world_model_long_20260617_180554
/mnt/nas/datasets/wmt_massive/evidence_nio/world_model_long_20260617_180554
```

这次也顺便验证了一个工程点：

```text
io 上的 RTX 3090 是可跑长任务的，
但必须保持 270W power limit，
不能放开。
```

GPU 统计：

```text
avg power: 192.18W
max power: 195.92W
avg temp:  70.82C
max temp:  71C
avg util:  29.07%
max util:  32%
max mem:   688MiB
```

这说明这次不是之前那种 CPU-only 假任务。
GPU 确实在工作，而且没有掉卡。

## 训练有没有学到东西

训练 loss 有下降，但幅度不大。

第一轮：

```text
loss        7.5148
inbatch_acc 0.0181
```

最后一轮：

```text
loss        7.2923
inbatch_acc 0.0247
```

最好 loss：

```text
epoch 456
loss  7.2923
```

最好 in-batch accuracy：

```text
epoch       442
inbatch_acc 0.0248
```

这说明模型确实在学 local context。
但它学得并不强。

从工程上看，这是一个健康训练。
从理论上看，这还不能说明它学出了世界模型。

## frame probe 结果

我们真正关心的是 P-FRAME01。

也就是：

```text
composite - base
```

能不能指向正确的 relation anchors。

这次最好的早期结果出现在 epoch 2：

```text
epoch 2
mode: tree / merge_no_bias
auc  0.7236
mrr  0.8485
hit1 0.7273
hit3 1.0000
```

但是到最后一轮，结果没有继续变强。

epoch 456：

| mode | AUC | MRR | Hit@1 | Hit@3 |
|---|---:|---:|---:|---:|
| L0 | 0.6182 | 0.8364 | 0.7273 | 0.9091 |
| CMul | 0.6182 | 0.8182 | 0.6364 | 1.0000 |
| merge_no_bias | 0.6473 | 0.8333 | 0.7273 | 0.9091 |
| tree | 0.6473 | 0.8333 | 0.7273 | 0.9091 |
| path | 0.5618 | 0.8712 | 0.8182 | 0.9091 |

这里要小心读。

如果 TreeHeap world model 被证明了，我们希望看到：

```text
tree / merge_no_bias / CMul 明显强于 L0
并且随着训练稳定变强
```

但实际看到的是：

```text
1. early epoch 有一点信号。
2. long training 没有把这个信号放大。
3. path 的 Hit@1/MRR 也很高，说明 probe 里可能有 token/path 偏差。
4. final tree 只比 L0 在 AUC 上略好，不构成强证据。
```

所以 P-FRAME01 的状态是：

```text
inconclusive
```

不能升级为 positive claim。

## 几何空间有没有坍缩

这部分反而比较有价值。

最后一轮的 off-diagonal cosine mean：

| mode | cosine mean |
|---|---:|
| L0 | 0.0519 |
| CMul | 0.0539 |
| merge_no_bias | 0.0566 |
| tree | 0.0865 |
| path | 0.9973 |

这说明：

```text
L0 / CMul / merge_no_bias / tree 都没有全局挤成同一个方向。
```

tree 的 cosine mean 比 L0 高一点，但远没有旧 checkpoint 那种：

```text
0.985
```

这支持一个判断：

```text
t_merge 本身不是必然把空间压坏的罪魁祸首。
```

真正异常的是 path：

```text
path cosine mean = 0.9973
```

这说明当前 path 构造在这个 probe 集合上几乎是常量。
也就是说，它不是一个好的语义参考系。

这和我们之前的判断一致：

```text
路径本身更多编码 token ID / 分桶位置，
不是语法角色，也不是世界关系。
```

## 这次到底证明了什么

可以保留的结论：

```text
1. 新 checkpoint 能稳定训练。
2. io 的 3090 在 270W limit 下可以跑 10 小时任务。
3. t_merge 不必然导致全局向量坍缩。
4. local BPE-context objective 可以学到一点上下文检索能力。
5. 当前训练目标没有证明 world-model reference frame。
```

必须降级的说法：

```text
TreeHeap 已经学出世界模型。
```

这句话不能说。

更准确的说法是：

```text
TreeHeap 现在有一个可训练的世界模型候选管线，
但 local context objective 还不能让 P-FRAME01 成立。
```

## 下一步怎么改 predict

这次最重要的教训是：

```text
不要只让模型预测附近 token。
```

因为附近 token 主要教会模型：

```text
哪些词经常共现。
```

但我们想要的是：

```text
复合概念和基础概念之间的关系方向。
```

也就是：

```text
football - ball -> foot / kick / field / goal
basketball - ball -> hand / throw / court / basket
```

所以 P-FRAME01 下一版应该改成更直接的训练目标。

例如：

```text
输入：
  composite
  base

目标：
  拉近 positive relation anchors
  推远 hard negative anchors
```

形式上可以是：

```text
delta = vector(composite) - vector(base)

positive:
  foot, kick, field, goal

negative:
  hand, basket, racket, engine, snow
```

训练目标：

```text
delta 更接近 positive anchor directions
delta 远离 negative anchor directions
```

这比 local context objective 更贴近我们真正要验证的 claim。

## ARA 状态

这次 evidence 应该这样登记：

```text
Predict:
  P-FRAME01

Evidence:
  world_model_long_20260617_180554

Verdict:
  diagnostic / inconclusive

Do not promote to claim.
```

换句话说：

```text
P-FRAME01 还活着，
但当前 objective 没有通过 evidence gate。
```

这不是坏结果。
一个好的研究系统，应该允许 predict 被证据卡住。

## 最后一句话

这次守夜训练没有证明 TreeHeap 已经拥有世界模型。

它证明的是：

```text
我们已经有能力正规地训练、保存、诊断一个新的 TreeHeap checkpoint；
也已经知道 local context objective 不是通向 P-FRAME01 的直路。
```

下一步不是继续堆时间。

下一步是换 objective。

> **License: GPLv3**
