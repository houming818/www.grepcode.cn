---
title: "[SPR-027] TreeHeap 差分代数：从 Zero 到距离，再到学习"
date: 2026-06-25
weight: 27
author: nio (Houming818) & Codex Review
description: "TreeHeap 的距离不应该先拍一个 scalar 公式，而应该先定义 Zero、差分、范数、内积、cosine 和 finite difference。本文记录 treeheap_diff_algebra_probe 的设计和结果。"
tags: [SPR, TreeHeap, ARA, Math, Difference, Gradient]
---

# TreeHeap 差分代数：从 Zero 到距离，再到学习

上一篇 `SPR-026` 做了一个浅层 S1 proof：

```text
真实短句
-> soft TreeHeap write
-> root / subject / object slot
-> query
```

但 Houming818 指出了一个更底层的问题：

```text
两个 TreeHeap 结构如何计算距离？
```

我一开始直接回答“可以算节点距离、路径加权距离、子堆距离”。

这个回答不算错，但跳了一步。

真正第一性的问题是：

```text
TreeHeap 的差分怎么定义？
```

因为距离不是第一定义。

距离应该来自：

```text
差分
↓
范数
↓
距离
```

就像实数一样：

```text
|x-y|
```

这里真正先发生的是：

```text
x-y
```

再取绝对值。

向量也是一样：

```text
||a-b||
```

先有：

```text
a-b
```

再有范数。

TreeHeap 也应该这样。

## 为什么差分比距离更基础？

机器学习不是只需要“两个东西远不远”。

机器学习还需要知道：

```text
如果我把参数改一点，
loss 会怎么变？
```

也就是：

```text
差分 / 微分 / 梯度
```

如果 TreeHeap 只有一个距离函数：

```text
Distance(A,B)
```

但没有：

```text
Diff(A,B)
```

那它很难接上学习。

因为学习要做的是：

```text
Δloss / Δparameter
```

所以我们需要先定义：

```text
Zero
Subtraction
Norm
Inner Product
Cosine
Finite Difference
```

这就是本篇的主题。

## Zero TreeHeap

先定义零 TreeHeap：

```text
Zero[i] = 0 ∈ R^128
```

也就是每个节点都是 128D 零向量。

如果一个 TreeHeap 是：

```text
H
```

那么它的大小不是凭空来的，而是：

```text
H - Zero
```

再取范数。

这和实数一致：

```text
|x| = |x - 0|
```

## TreeHeap 差分

假设两个 TreeHeap 的地址空间一样：

```text
A[i] ∈ R^128
B[i] ∈ R^128
```

那么差分定义为：

```text
Diff(A,B)[i] = A[i] - B[i]
```

注意：

```text
Diff(A,B)
```

仍然是一个 TreeHeap-shaped object。

只是每个节点存的是：

```text
向量差
```

而不是原始向量。

这点很关键。

我们不是把 TreeHeap 压扁成一个 scalar。

我们先保留结构差异。

## TreeHeap 范数

TreeHeap 不是普通 flat vector。

节点有深度：

```text
root depth = 0
left/right depth = 1
deeper nodes depth = 2,3,...
```

所以第一版范数加入深度权重：

$$ \lVert H\rVert_T = \sqrt{\sum_i \alpha^{depth(i)} \lVert H[i]\rVert_2^2} $$

其中：

```text
0 < alpha < 1
```

这表示：

```text
越靠近 root，权重越大。
越深的节点，权重越小。
```

这不是最终答案，但它是一个合理的第一版。

## TreeHeap 距离

有了差分和范数，距离自然定义为：

$$ d(A,B) = \lVert A-B\rVert_T $$

也就是：

```text
先差分
再取 TreeHeap 范数
```

这比直接写一个 `distance(A,B)` 更干净。

因为它和学习、微分、梯度可以接上。

## TreeHeap 内积和 cosine

同样，cosine 也不应该是随便把节点平均后再算。

先定义 TreeHeap 内积：

$$ \langle A,B\rangle_T = \sum_i \alpha^{depth(i)} \langle A[i],B[i]\rangle $$

然后定义 TreeHeap cosine：

$$ \cos_T(A,B)=\frac{\langle A,B\rangle_T}{\lVert A\rVert_T\lVert B\rVert_T} $$

这样 cosine 也是从 TreeHeap 代数结构来的。

不是临时拼出来的。

## 有限差分

现在进入学习。

如果：

```text
L(H)
```

是一个 loss，我们想知道沿着方向：

```text
U
```

改变 TreeHeap 时，loss 怎么变。

有限差分可以写成：

$$ \frac{L(H+\epsilon U)-L(H-\epsilon U)}{2\epsilon} $$

如果 TreeHeap 差分代数正确，这个数应该和解析方向导数对上。

对一个简单的加权 MSE：

$$ L(H)=\frac{1}{2}\lVert H-Target\rVert_T^2 $$

方向导数应该是：

$$ \langle H-Target, U\rangle_T $$

这就是实验要检查的第一件事。

## prob vector plus 的学习信号

我们还要检查它能不能接上写入学习。

定义一个最小 prob vector plus：

```text
H'[i] = H[i] + p_i · x
```

其中：

```text
x ∈ R^128
p = softmax(theta)
```

这表示：

```text
把一个 128D token/world vector
按概率写入 TreeHeap 节点。
```

目标 TreeHeap 是：

```text
Target[target_node] = x
其他节点 = 0
```

loss：

$$ L=\frac{1}{2}\lVert H'-Target\rVert_T^2 $$

如果差分代数能支持学习，那么：

```text
有限差分算出来的 dL/dtheta
```

应该接近：

```text
解析梯度算出来的 dL/dtheta
```

并且做一步梯度下降后：

```text
loss 应该下降
target_node 的写入概率应该上升
```

## 实验脚本

脚本：

```text
ara/m0-treeheap-math/src/treeheap_diff_algebra_probe.py
```

执行主机：

```text
io.grepcode.cn
```

证据：

```text
ara/m0-treeheap-math/evidence/treeheap_diff_algebra_probe/
```

参数：

```text
nodes = 15
dim = 128
alpha = 0.72
eps = 1e-5
```

## 实验结果

| Metric | Value |
|---|---:|
| `norm_zero` | 0.000000 |
| `dist_aa` | 0.000000 |
| `dist_ab` | 8.779953 |
| `dist_ba` | 8.779953 |
| `cos_aa` | 1.000000 |
| `anti_sym_error` | 0.000000 |
| `directional_derivative_abs_error` | 3.48e-10 |
| `theta_grad_abs_error` | 4.21e-10 |
| `theta_grad_rel_error` | 2.10e-10 |
| `initial_loss` | 29.138441 |
| `stepped_loss` | 0.000660 |
| `target_prob_before` | 0.064808 |
| `target_prob_after` | 0.995534 |

这些结果说明：

```text
Zero 范数为 0。
自己到自己的距离为 0。
距离对称。
cos(A,A)=1。
Diff(A,B)=-Diff(B,A)。
TreeHeap 状态有限差分和解析方向导数一致。
prob vector plus 的 theta 梯度和有限差分一致。
一步梯度下降能显著降低 loss。
写入概率会从错误的扩散状态坍缩到目标节点。
```

## 这次证明了什么？

这次支持：

```text
M0-DIFF-C01 -> supported pilot
```

也就是：

```text
TreeHeap 可以先定义差分代数，
再由差分推出距离、cosine、loss 和有限差分学习信号。
```

这件事很重要。

因为 S1 的 prob vector write 需要的不只是：

```text
我能把 token 写进去。
```

还需要：

```text
写错了，loss 怎么变？
参数该往哪边改？
```

这就是差分代数给出的东西。

## 这次没有证明什么？

边界也要清楚。

这次没有证明：

```text
TreeHeap 已经学会语言。
TreeHeap 已经有世界模型坐标系。
prob vector plus 已经是最终 encoder。
TreeHeap 比 MLP / Transformer 强。
TreeHeap 能做 WMT。
```

它证明的是更底层的事：

```text
TreeHeap 有可用于学习的差分/距离/梯度评价框架。
```

## 对 S1 的意义

现在我们可以把 S1 的写入问题说得更精确。

不再只是：

```text
把 token 写到 TreeHeap。
```

而是：

```text
从 Zero TreeHeap 出发，
用 prob vector plus 写入 128D token/world vector，
用 TreeHeap diff distance 评价写入结果，
再用有限差分/梯度更新写入 kernel。
```

这条链是：

```text
Zero
-> Prob Vector Plus
-> TreeHeap state
-> Diff to Target
-> Norm / Loss
-> Finite Difference / Gradient
-> Update Kernel
```

这才是 M0 工具箱进入 S1 的真正接口。

## 下一步

下一步不是再问：

```text
距离怎么算？
```

而是问：

```text
Target 从哪里来？
```

也就是我们前面说的世界模型坐标系。

例如：

```text
foot + ball -> football
hand + ball -> handball
rain + coat -> raincoat
book + shelf -> bookshelf
```

我们需要这样的数据，告诉 TreeHeap：

```text
什么样的写入结果是对的？
什么样的组合关系应该在空间里接近？
```

没有世界模型坐标系，TreeHeap 只能学 echo。

有了世界模型坐标系，TreeHeap 才能学语义拓扑。

## 总结

这篇的核心结论是：

```text
TreeHeap 距离不是第一定义。
TreeHeap 差分才是第一定义。
```

从差分出发，我们得到了：

```text
Zero
Subtraction
Norm
Inner Product
Cosine
Finite Difference
Gradient Signal
```

这让 TreeHeap 不再只是一个“树形存储结构”。

它开始具备进入梯度学习的数学接口。
