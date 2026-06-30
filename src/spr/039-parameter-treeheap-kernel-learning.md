---
title: "[SPR-039] 参数也是 TreeHeap：kernel 自己学会了卷积"
date: 2026-07-01
weight: 39
author: nio (Houming818) & Codex Review
description: "SPR-039 proof：把 SPR-038 的状态松弛和真正的参数学习分开，证明 parameter TreeHeap Theta 可以通过梯度学会局部 subheap 卷积核。"
tags: [SPR, TreeHeap, ARA, Kernel, Gradient, Convolution]
---

# 参数也是 TreeHeap：kernel 自己学会了卷积

SPR-038 之后，Houming818 提了一个关键修正：

```text
参数本身也应该是 TreeHeap。
```

这个修正很重要。

SPR-038 做的是：

```text
H <- H - eta * grad_H L
```

也就是更新当前样本的 heap state。

SPR-039 要证明的是另一件事：

```text
Theta <- Theta - eta * grad_Theta L
```

也就是更新 kernel 的参数 TreeHeap。

这两件事必须分开。

## 对象定义

这次我们严格区分：

| 符号 | 含义 |
|---|---|
| `Theta` | parameter TreeHeap，模型参数的载体 |
| `H` | activation / memory TreeHeap，当前样本状态 |
| `A` | physical address rule，比如 `left(i)=2i` |
| `K_Theta` | 由 `Theta` 定义的局部 kernel operator |
| `L` | scalar loss，用来产生梯度 |

计算过程是：

```text
H_next = K_Theta(H, A)
L = loss(H_next, target)
Theta <- Theta - eta * grad_Theta L
```

这才是参数学习。

## 最小 TreeHeap 卷积任务

我们使用一棵 7 节点树：

```text
        1
      /   \
     2     3
    / \   / \
   4   5 6   7
```

输入例子：

```text
H = [1,2,3,4,5,6,7]
```

隐藏 kernel 是：

```text
[root, left, right] = [1, 1, 1]
```

所以内部节点的目标是：

```text
H'[1] = H[1] + H[2] + H[3] = 6
H'[2] = H[2] + H[4] + H[5] = 11
H'[3] = H[3] + H[6] + H[7] = 16
```

叶子保持不变：

```text
H' = [6,11,16,4,5,6,7]
```

关键点是：

```text
模型一开始不知道 [1,1,1]。
```

它只有参数：

```text
Theta = [theta_root, theta_left, theta_right]
```

模型计算：

```text
Y[i] = theta_root * H[i]
     + theta_left * H[left(i)]
     + theta_right * H[right(i)]
```

loss：

```text
L = mean_squared_error(Y, target)
```

如果训练后：

```text
Theta ~= [1,1,1]
```

就说明 kernel 参数真的学到了这个局部卷积规则。

## 实验结果

实验在 `io.grepcode.cn` 上执行。

证据目录：

```text
ara/s1-echo/evidence/s1_kernel_parameter_learning_probe/
```

结果：

| 指标 | 数值 |
|---|---:|
| pilot pass | true |
| learned theta | `[0.9999999999999998, 0.9999999999999998, 1.0000000000000004]` |
| theta L2 error | `5.44e-16` |
| theta delta L2 | `1.15777` |
| TreeHeap test MSE | `8.78e-31` |
| TreeHeap OOD MSE | `8.93e-30` |
| wrong-address test MSE | `5.92848` |
| flat-global test MSE | `3.56010` |

这说明：

```text
Theta 确实移动了。
Theta 学回了隐藏 kernel [1,1,1]。
正确地址结构下 test / OOD 误差接近 0。
错误地址结构明显失败。
不看 left/right subheap 的 matched-size flat baseline 也失败。
```

## 为什么 wrong-address 很重要

如果只是让模型学一个线性函数，它当然可能会过拟合。

所以这次放了 wrong-address baseline。

正确 kernel 看的是：

```text
node 1 -> [1,2,3]
node 2 -> [2,4,5]
node 3 -> [3,6,7]
```

wrong-address 看的是错误局部结构。

结果：

```text
TreeHeap test MSE       ~= 0
wrong-address test MSE  = 5.92848
```

这说明收益不是来自“随便三个数做线性回归”，而是来自：

```text
正确的 TreeHeap address / subheap 结构。
```

## 和 SPR-038 的区别

SPR-038：

```text
更新 H
不更新 Theta
证明 state relaxation
```

SPR-039：

```text
更新 Theta
不靠移动当前 H 来作弊
证明 kernel parameter learning
```

所以 SPR-039 补上了 SPR-038 留下的缺口。

现在我们可以说：

```text
TreeHeap 不只是状态能被梯度松弛。
TreeHeap 的 kernel 参数也能被梯度训练。
```

## 和 Transformer 的关系

Transformer 的 attention 可以粗略看成：

```text
score(i,j) = Q_i dot K_j
```

它在 flat token 图上学习关系。

TreeHeap kernel 的形式是：

```text
state = K_Theta(root, left, right)
```

它在局部 subheap 上学习关系。

这次 proof 证明了最小版本：

```text
K_Theta 可以通过梯度学到一个局部结构算子。
```

这不是说 TreeHeap 已经打败 Transformer。

更准确地说：

```text
TreeHeap 和普通 ML 一样，可以通过 loss / gradient 学习函数；
但它学习的函数天然绑定 address / path / subheap 结构。
```

## Claim 状态

```text
S1-KERNEL-LEARN-C01:
A parameter TreeHeap Theta can learn a local subheap convolution rule
from scalar loss and gradient.

status: supported pilot
```

## 还没有证明什么

这次没有证明：

```text
语言理解
WMT 翻译
真实 relation field
multi-kernel specialization
TreeHeap 胜过所有更大的 flat model
```

尤其最后一点要诚实：

```text
一个更大的 flat linear model 当然可能拟合这个 toy。
```

这次 proof 的重点不是“所有 flat 都输”。

重点是：

```text
在 TreeHeap 的 address / subheap 结构里，
共享 kernel 参数 Theta 可以被梯度学出来。
```

这是一个必要地基。

## 下一步

SPR-039 之后，下一步应该扩展三件事：

```text
1. scalar kernel -> vector / matrix kernel
2. clean sum target -> noisy restore / mask restore
3. single kernel -> multi-kernel specialization
```

如果这些继续成立，TreeHeap 才能从：

```text
能学一个 toy 卷积核
```

走向：

```text
能学真实数据里的结构 kernel
```

## 一句话总结

SPR-039 的结论是：

```text
参数 TreeHeap Theta 可以通过 scalar loss 和 gradient，
学会一个局部 subheap 卷积核。
```

这一步把 SPR-038 的状态松弛，推进到了真正的参数学习。

> **ARA**: [kernel parameter learning](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/kernel_parameter_learning.md) / [evidence](https://github.com/houming818/sametime/tree/main/ara/s1-echo/evidence/s1_kernel_parameter_learning_probe) / [claims](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/claims.md)
