---
title: "[SPR-039] 参数也是 TreeHeap：让 kernel 自己学会卷积"
date: 2026-06-30
weight: 39
author: nio (Houming818) & Codex Review
description: "SPR-039 计划稿：把 SPR-038 的状态松弛和真正的参数学习分开，设计一个最小 proof，让 parameter TreeHeap 学会局部 subheap 卷积核。"
tags: [SPR, TreeHeap, ARA, Kernel, Gradient, Convolution]
---

# 参数也是 TreeHeap：让 kernel 自己学会卷积

SPR-038 之后，Houming818 提了一个关键修正：

```text
参数本身也应该是 TreeHeap。
```

这个修正很重要。

因为如果我们只说：

```text
H <- H - eta * grad_H L
```

那只是状态松弛。

它说明当前 heap state 可以沿着能量下降方向移动。

但它没有说明模型学会了什么。

真正的参数学习应该是：

```text
Theta <- Theta - eta * grad_Theta L
```

也就是说：

```text
Theta 才是模型参数。
Theta 也可以被组织成 TreeHeap。
```

这篇 SPR-039 是一个计划稿。

它要回答的问题是：

```text
TreeHeap 的 kernel 参数，能不能通过 loss / gradient 学会一个局部卷积规则？
```

## 先把对象分清楚

我们现在至少有五个对象：

| 符号 | 含义 |
|---|---|
| `Theta` | parameter TreeHeap，模型参数的载体 |
| `H` | activation / memory TreeHeap，当前样本的状态 |
| `A` | physical address rule，比如 `left(i)=2i` |
| `K_Theta` | 由参数 `Theta` 定义的 kernel operator |
| `L` | scalar loss，用来产生梯度 |

模型计算可以写成：

```text
H_next = K_Theta(H, A)
L = loss(H_next, target)
```

如果更新的是 `H`：

```text
H <- H - eta * grad_H L
```

这是 SPR-038 的状态松弛。

如果更新的是 `Theta`：

```text
Theta <- Theta - eta * grad_Theta L
```

这才是 SPR-039 要证明的参数学习。

## 最小 TreeHeap 卷积

考虑一棵 7 节点树：

```text
        1
      /   \
     2     3
    / \   / \
   4   5 6   7
```

如果当前 heap 是：

```text
H = [1,2,3,4,5,6,7]
```

我们定义一个局部 kernel：

```text
[root, left, right] = [1, 1, 1]
```

对每个内部节点做卷积：

```text
H'[1] = H[1] + H[2] + H[3] = 1 + 2 + 3 = 6
H'[2] = H[2] + H[4] + H[5] = 2 + 4 + 5 = 11
H'[3] = H[3] + H[6] + H[7] = 3 + 6 + 7 = 16
```

叶子保持不变，就得到：

```text
H' = [6,11,16,4,5,6,7]
```

这就是一个最小的 TreeHeap 卷积任务。

## 关键不是手写 kernel

如果我们手写：

```text
theta = [1,1,1]
```

那只是演绎计算。

它当然能得到：

```text
[6,11,16,4,5,6,7]
```

但这没有证明“学习”。

SPR-039 要做的是：

```text
模型一开始不知道 theta = [1,1,1]
只给它很多输入 heap 和目标 heap
让它通过 loss 反推出 theta
```

也就是：

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

训练后我们希望看到：

```text
theta_root  ~= 1
theta_left  ~= 1
theta_right ~= 1
```

如果这个能成立，才说明：

```text
TreeHeap kernel 参数可以通过梯度学到局部卷积规则。
```

## 为什么这和 Transformer 有关系

Transformer 里的 attention 可以粗略看成：

```text
score(i,j) = Q_i dot K_j
```

它在 flat token 空间里计算 token 和 token 的关系。

TreeHeap kernel 则希望在结构空间里计算：

```text
score / state = K_Theta(root, left, right)
```

也就是：

```text
不是所有 token 对所有 token。
而是当前 subheap 的 root / left / right 先形成局部关系。
```

这就是 TreeHeap 可能存在的归纳偏置：

```text
地址
路径
子结构
局部组合
递归分解
```

Transformer 的强项是全局共现。

TreeHeap 想证明的不是“我和 Transformer 完全不同”，而是：

```text
我也能用梯度学习函数。
但我学习的函数天然带有树地址和局部子结构。
```

## SPR-039 的 Claim

```text
S1-KERNEL-LEARN-C01:
A parameter TreeHeap Theta can learn a local subheap convolution rule
from scalar loss and gradient.
```

中文说就是：

```text
参数堆 Theta 可以通过 loss / gradient，
学会一个局部 TreeHeap 卷积核。
```

## Predict

如果 claim 成立，那么在最小 toy 上：

```text
hidden kernel = [1,1,1]
```

训练后应该得到：

```text
learned Theta ~= [1,1,1]
```

同时：

```text
train MSE 低
test MSE 低
OOD MSE 低
wrong-address baseline 明显更差
```

## 反证条件

这个 claim 很容易被打脸。

如果出现下面情况，就应该拒绝或降级：

```text
Theta 学不回 [1,1,1]
test / OOD error 很高
wrong-address baseline 一样好
flat baseline 不用地址结构也赢了
实验其实只更新了 H，没有更新 Theta
```

尤其最后一条很重要。

SPR-039 必须证明：

```text
移动的是参数 TreeHeap Theta。
```

不是：

```text
移动当前样本的 heap state H。
```

## 为什么这是下一步

SPR-038 证明了：

```text
只要有 scalar energy，H 可以松弛。
```

SPR-039 要证明：

```text
只要有 scalar loss，Theta 可以学习 kernel。
```

这两步合起来，TreeHeap 才开始接近普通机器学习系统：

```text
普通 ML:
  参数通过梯度学习函数

TreeHeap:
  参数堆 Theta 通过梯度学习结构化 kernel
  当前状态 H 可以在能量场里松弛
```

前者是模型学习。

后者是状态调整。

两者都需要，但不能混成一个东西。

## 一句话总结

SPR-039 的核心不是再证明 TreeHeap 可以算。

而是证明：

```text
TreeHeap 的参数本身可以作为一个结构化对象，
通过梯度学会局部 subheap 卷积规则。
```

如果这个 proof 通过，我们才有资格往下一步问：

```text
这个 learned kernel 能不能从 echo 走向 mask restore？
能不能从 toy sum 走向 relation field？
能不能从单 kernel 走向 multi-kernel？
```

这才是 TreeHeap 接近真正学习系统的一步。

> **ARA**: [kernel parameter learning](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/kernel_parameter_learning.md) / [claims](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/claims.md)
