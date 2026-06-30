---
title: "[SPR-038] 梯度不只改参数：TreeHeap 的状态松弛 proof"
date: 2026-06-30
weight: 38
author: nio (Houming818) & Codex Review
description: "SPR-038 验证 Houming818 的 heap state gradient 假设：梯度不一定只更新 kernel 参数，也可以直接更新 TreeHeap 的 arr[i] 状态，让 heap 沿能量下降方向进入更平衡的结构。"
tags: [SPR, TreeHeap, ARA, Gradient, Energy, Relaxation]
---

# 梯度不只改参数：TreeHeap 的状态松弛 proof

SPR-037 里，我们讨论了“可控流形”。

当时的实验是：

```text
手动调整 relation_weight / order_weight
观察 fold 质量是否从乱态变好
```

这个 proof 通过了。

但是你马上指出了一个更深的问题：

```text
既然是流形，肯定要考虑梯度信息如何产生。
不然怎么学习？
```

然后你提出了一个很关键的想法：

```text
梯度不一定只是改参数。
它也可能调整 heap 的平衡性。
```

这篇 SPR-038 就是直接跑这个 proof。

## 先说结论

这次 proof 支持一个窄 claim：

```text
TreeHeap 可以存在 heap state gradient。
```

也就是说：

```text
不更新 kernel 参数 theta，
只更新当前 heap state H，
也可以让 heap 沿能量下降方向进入更低能量状态。
```

实验结果：

| 指标 | 数值 |
|---|---:|
| scalar energy ratio | 2.47e-31 |
| scalar left delta | +1.0000 |
| scalar right delta | -1.0000 |
| mean vector energy ratio | 1.24e-13 |
| max vector energy ratio | 3.69e-13 |
| mean centroid error drop | 3.0393 |
| pass rate | 1.0000 |
| pilot pass | true |

这个结果说明：

```text
状态梯度这条机制是成立的。
```

但它还不说明：

```text
TreeHeap 已经理解语言
TreeHeap 已经能翻译
状态松弛已经能自动学世界模型
```

这次只是机制 proof。

## Houming818 的假设

这次 proof 的核心假设来自 Houming818：

```text
梯度信息可能不是简单的参数变更，
而是一种 heap 平衡性调整。
```

你给的例子是：

```text
[2.0, 1.0, 3.0]
```

如果梯度来了，它不一定是去修改某个外部参数。

它可能直接调整当前 heap：

```text
[2.0, 1.0, 3.0]
-> [2.0, 1.5, 2.5]
-> [2.0, 1.8, 2.2]
```

这个过程不是：

```text
改函数
```

而是：

```text
调状态
```

这很像物理里的系统松弛：

```text
当前状态能量高，
于是系统沿能量下降方向移动。
```

## 两种学习路径

普通神经网络更常见的是参数梯度：

```text
theta <- theta - eta * grad_theta L
```

也就是：

```text
函数参数变了。
```

TreeHeap 可以有另一条路径：

```text
H <- H - eta * grad_H E(H)
```

这里：

```text
H = 当前 TreeHeap state
E(H) = 当前 heap 的能量
```

也就是说：

```text
函数不变。
地址规则不变。
kernel 系数不变。
只有 arr[i] 的状态在移动。
```

这就是 heap state relaxation。

## 为什么这有意义

之前我们经常问：

```text
目标 heap 怎么可导？
```

但这个思路把问题换了一下：

```text
目标 heap 不一定要可导。
当前 heap 的能量函数可导就行。
```

例如我们可以定义：

```text
E_balance(H)       左右是否平衡
E_parent_child(H)  父子是否一致
E_relation(H, W)   heap 是否贴合关系场
E_entropy(P)       概率容器是否过早坍缩
```

总能量：

```text
E_total(H)
  = E_balance(H)
  + E_parent_child(H)
  + E_relation(H, W)
  + E_entropy(P)
```

然后做：

```text
H <- H - eta * grad_H E_total(H)
```

这样，梯度来自当前状态的能量。

不是来自一个必须可导的目标树。

## Proof 1：最小 scalar heap

第一个 proof 就是你给的例子的数学化。

初始状态：

```text
root  = 2.0
left  = 1.0
right = 3.0
```

能量函数：

```text
E = (left - right)^2
  + (root - (left + right) / 2)^2
```

第一项要求：

```text
left 和 right 平衡
```

第二项要求：

```text
root 接近左右孩子的平均值
```

训练时：

```text
不更新 theta
只更新 root / left / right
```

结果：

```text
initial: [2.0, 1.0, 3.0], energy = 4.0
final:   [2.0, 2.0, 2.0], energy = 9.86e-31
```

也就是说：

```text
left  增加了 1.0
right 减少了 1.0
```

这正好对应你说的：

```text
[2.0, 1.0, 3.0]
-> [2.0, 1.5, 2.5]
-> [2.0, 2.0, 2.0]
```

## Proof 2：7 节点 vector TreeHeap

第二个 proof 稍微更像 TreeHeap。

结构是：

```text
        1
      /   \
     2     3
    / \   / \
   4   5 6   7
```

其中：

```text
4,5,6,7 是固定叶子向量
1,2,3 是可更新的 internal heap state
```

注意：

```text
叶子不动
kernel 参数不动
地址规则不动
只更新 arr[1], arr[2], arr[3]
```

能量有两部分。

第一部分是父子一致性：

```text
arr[parent] 应该接近 mean(left_child, right_child)
```

第二部分是关系锚点一致性：

```text
arr[node] 应该接近固定 relation anchor
```

这两个东西组成当前 heap 的能量。

然后只对 `arr[i]` 做梯度下降。

## vector proof 结果

随机初始化 32 次。

结果：

```text
mean_vector_energy_ratio = 1.24e-13
max_vector_energy_ratio  = 3.69e-13
mean_centroid_error_drop = 3.0393
pass_rate                = 1.0
```

这说明：

```text
所有 32 次随机初始化都收敛了。
```

其中一次 trace：

```text
energy: 52.88 -> 37.70 -> 27.48 -> 11.88 -> 3.72 -> 0.20 -> 0.0022 -> 7.19e-12
centroid_error: 3.3872 -> 2.9325 -> 2.5580 -> 1.7572 -> 1.0210 -> 0.2565 -> 0.0278 -> 0.0000016
```

这就是很典型的状态松弛曲线。

## 这次 claim

这次 claim 是：

```text
S1-RELAX-C01:
A differentiable energy over the current TreeHeap state can generate gradients
that relax arr[i] toward a lower-energy equilibrium while kernel parameters
and address rules remain fixed.
```

状态：

```text
supported pilot
```

它证明的是：

```text
TreeHeap 不只有参数梯度路径。
它也可以有状态梯度路径。
```

也就是：

```text
改函数是一种学习。
调 heap 状态也是一种学习。
```

## 这没有证明什么

它没有证明：

```text
翻译
语言理解
无监督世界模型
真实 relation field
TreeHeap 胜过 Transformer
```

它也没有证明：

```text
所有语言目标都能写成漂亮的能量函数。
```

所以这次不能夸大。

它只是证明：

```text
只要能定义当前 heap 的可导能量，
梯度就可以直接作用在 heap state 上。
```

## 对路线的影响

这个结果很重要。

之前我们大致有：

```text
kernel 参数学习
```

现在多了一条：

```text
heap state relaxation
```

于是 TreeHeap 的学习可以分成：

```text
1. 学 kernel
   让算子更会写、读、合并、坍缩

2. 调 H
   让当前 heap 自己进入低能量结构
```

这比普通“把所有东西都塞进参数矩阵”更有 TreeHeap 自己的味道。

更像：

```text
kernel 定义力场
heap state 在力场里松弛
probability container 决定何时坍缩
```

## 下一步

下一步不能只停留在平衡 toy。

应该把三件事接起来：

```text
真实或弱真实 relation field
heap state relaxation
stop / left / right 概率坍缩
```

最小实验可以是：

```text
输入真实短句
构造弱 relation field
初始化一个 noisy TreeHeap
只用 energy relaxation 调 arr[i]
再用 read kernel 查询 block
看 block F1 是否提升
```

如果这个通过，就说明：

```text
状态松弛不仅能平衡数值，
还能帮助真实短句结构变稳定。
```

那时候，TreeHeap 的可控流形就不只是手动调参地图，而更像一个可学习动力系统。

## 一句话总结

SPR-038 的结论是：

```text
梯度不一定只改参数。
TreeHeap 的 arr[i] 本身也可以被梯度推动，
沿当前能量函数进入更稳定的结构状态。
```

这条路还很早。

但它给 TreeHeap 增加了一个重要可能：

```text
不是只学习函数，
而是让结构自己松弛。
```

> **ARA**: [heap-state relaxation](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/heap_state_relaxation.md) / [claims](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/claims.md) / [experiment script](https://github.com/houming818/sametime/blob/main/ara/s1-echo/src/s1_heap_state_relaxation_probe.py) / [evidence](https://github.com/houming818/sametime/tree/main/ara/s1-echo/evidence/s1_heap_state_relaxation_probe)
