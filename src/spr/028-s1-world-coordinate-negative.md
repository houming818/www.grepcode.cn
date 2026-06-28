---
title: "[SPR-028] 世界模型坐标系第一试：Frozen Embedding 不是胜利，是一把尺"
date: 2026-06-25
weight: 28
author: nio (Houming818) & Codex Review
description: "用冻结的 all-MiniLM-L6-v2 embedding 作为外部世界坐标尺，测试 TreeHeap prob vector plus 在复合词任务上能否靠近目标概念。结果是负面的：vector_add 明显更强。"
tags: [SPR, TreeHeap, ARA, S1, WorldModel, Experiment]
---

# 世界模型坐标系第一试：Frozen Embedding 不是胜利，是一把尺

`SPR-027` 之后，我们有了 TreeHeap 的差分代数：

```text
Zero
Diff
Norm
Cosine
Finite Difference
Gradient Signal
```

这说明 TreeHeap 已经可以定义：

```text
写入结果和目标之间的距离
```

但马上出现下一个问题：

```text
目标从哪里来？
```

也就是我们说的：

```text
世界模型坐标系
```

如果没有世界模型坐标系，TreeHeap 只能学 echo。

如果有一个坐标系，它才知道：

```text
foot + ball 应该靠近 football
hand + ball 应该靠近 handball
rain + coat 应该靠近 raincoat
```

## 这次用什么坐标系？

这次采用 Houming818 选的 A 方案：

```text
用现成 embedding。
```

具体是：

```text
sentence-transformers/all-MiniLM-L6-v2
```

在 io 上使用的是本地缓存：

```text
/home/nio/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/1110a243fdf4706b3f48f1d95db1a4f5529b4d41
```

所以这次没有用 `proxychains4`。

如果后面要加载新模型或新语料，且本地没有缓存，就应该在 io 上用：

```text
proxychains4
```

并把下载命令记录到 evidence。

## 防蒸馏边界

这里必须说清楚：

```text
冻结 embedding 不是 TreeHeap 自己学出的世界模型。
```

它只是一个外部坐标尺。

我们用它来问：

```text
TreeHeap 写入后的向量，能不能靠近这个坐标尺里的目标点？
```

这不是说：

```text
TreeHeap 已经拥有 all-MiniLM 的知识。
```

更不是说：

```text
TreeHeap 蒸馏了一个大模型。
```

本实验只验证：

```text
TreeHeap encoder 能否在一个冻结坐标系里学习组合映射。
```

## 实验任务

任务是复合词组合：

```text
left + right -> target
```

例子：

```text
foot + ball -> football
basket + ball -> basketball
hand + ball -> handball
rain + coat -> raincoat
book + shelf -> bookshelf
flash + light -> flashlight
```

数据规模：

| Split | Count |
|---|---:|
| train | 20 |
| test | 11 |
| OOD | 6 |
| targets | 37 |

embedding 原始维度：

```text
384D
```

固定随机正交投影到：

```text
128D
```

这样和 TreeHeap 的 128D 方向一致。

## 三个模型

### vector_add

最简单：

```text
y = normalize(left + right)
```

没有训练参数。

### concat_mlp

普通 MLP：

```text
[left, right, left*right, abs(left-right)] -> target
```

它有训练参数，会拟合训练集。

### treeheap_prob_vector_plus

TreeHeap 版本：

```text
H0 = Zero
H1 = ProbVectorPlus(H0, left)
H2 = ProbVectorPlus(H1, right)
y  = Read(H2)
```

其中写入是：

```text
H'[i] = H[i] + p_i · update(x)
```

也就是：

```text
用概率路由把 128D word vector 写入 TreeHeap 节点。
```

## 结果

结果如下：

| Model | Train cosine | Test cosine | OOD cosine | Test top1 | OOD top1 |
|---|---:|---:|---:|---:|---:|
| vector_add | 0.7117 | 0.7256 | 0.7198 | 0.909 | 0.833 |
| concat_mlp | 1.0000 | 0.6269 | 0.5766 | 0.000 | 0.000 |
| treeheap_prob_vector_plus | 0.9999 | 0.5051 | 0.3919 | 0.000 | 0.000 |

这个结果非常明确：

```text
TreeHeap 没赢。
```

更准确地说：

```text
当前 TreeHeap prob vector plus 过拟合训练集。
```

训练集上接近 1.0：

```text
train cosine = 0.9999
```

但 OOD 很差：

```text
OOD cosine = 0.3919
OOD top1 = 0.0
```

反而最简单的：

```text
vector_add
```

表现最好：

```text
OOD cosine = 0.7198
OOD top1 = 0.833
```

## Claim 状态

所以这次结论是：

```text
S1-WM-C01 -> rejected pilot
```

这个 rejected 很重要。

它说明我们不能说：

```text
只要把 TreeHeap 接到 embedding 坐标系，就自然有世界模型。
```

事实正好相反：

```text
当前 unconstrained TreeHeap reader 太自由，
会记住训练集，
但没有学到可泛化的复合词结构。
```

## 为什么 vector_add 会这么强？

因为 frozen embedding 里已经包含大量语言共现和语义关系。

对很多复合词来说：

```text
left + right
```

本身就已经靠近：

```text
target compound
```

例如：

```text
rain + coat
```

在 embedding 空间里天然接近：

```text
raincoat
```

这说明：

```text
外部 embedding 坐标系已经有强世界知识。
```

TreeHeap 如果只是用一个大 reader 去拟合它，很容易变成小数据过拟合。

这不是 TreeHeap 的优势区。

## 这对下一步意味着什么？

下一步不要简单增加参数。

也不要把 reader 做得更大。

因为这会更像：

```text
小 MLP 记训练集。
```

下一步应该限制 TreeHeap，让结构真的参与计算。

例如：

```text
1. 共享 family slot
   ball / coat / book / light 这些右侧词应该形成可复用子结构。

2. route entropy / collapse control
   防止所有词都写到同一个节点。

3. subheap reuse
   foot+ball, basket+ball, hand+ball 应该共享 ball 子堆。

4. copy/read pointer constraint
   readout 不应该完全自由生成，而应该读取 TreeHeap 中的组合状态。

5. 更强 baseline
   vector_add 必须作为第一 baseline。
```

也就是说，下一版不是：

```text
TreeHeap + 更大 MLP。
```

而是：

```text
TreeHeap + 更强结构约束。
```

## 这次仍然有价值吗？

有。

因为它告诉我们三件事。

第一：

```text
冻结 embedding 可以作为世界模型坐标尺。
```

第二：

```text
vector_add 是一个很强的 compound baseline。
```

第三：

```text
当前 TreeHeap prob vector plus 还没有把结构优势用出来。
```

这比一个虚假的正结果更有用。

它把下一步的任务变清楚了：

```text
不是证明 TreeHeap 能拟合训练集。
而是证明 TreeHeap 能利用地址、路径、子结构复用，
在 OOD compound 上超过 vector_add。
```

## 总结

这篇的结论是负面的：

```text
S1-WM-C01 rejected pilot。
```

但路线更清楚了：

```text
M0 给了差分和学习接口。
Frozen embedding 给了外部坐标尺。
当前 TreeHeap encoder 没有泛化。
下一步必须加入结构约束和 subheap reuse。
```

我们没有输给问题。

我们只是终于看清了问题站在哪里。
