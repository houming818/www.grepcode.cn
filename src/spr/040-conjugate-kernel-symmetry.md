---
title: "[SPR-040] TreeHeap kernel 的共轭翻转：mirror 后 kernel 也要翻"
date: 2026-07-01
weight: 40
author: nio (Houming818) & Codex Review
description: "SPR-040 proof：证明 TreeHeap 局部卷积不仅能求和，还满足 mirror conjugation；翻转树以后，kernel 的 left/right 权重也必须翻转。"
tags: [SPR, TreeHeap, ARA, Kernel, Convolution, Symmetry]
---

# TreeHeap kernel 的共轭翻转：mirror 后 kernel 也要翻

SPR-039 证明了一个最小事实：

```text
参数 TreeHeap Theta 可以通过梯度学会局部 subheap 卷积核。
```

当时的 kernel 是最简单的：

```text
[root, left, right] = [1, 1, 1]
```

这个确实有用，但也有一个问题：

```text
它太像普通求和了。
```

Houming818 问了一个更关键的问题：

```text
如果 TreeHeap 真的有结构卷积，
能不能证明共轭对称翻转？
```

也就是说：

```text
树 mirror 以后，
kernel 是不是也应该 mirror？
```

这篇 SPR-040 就是这个 proof。

## 什么是 mirror

还是这棵 7 节点 TreeHeap：

```text
        1
      /   \
     2     3
    / \   / \
   4   5 6   7
```

mirror 操作 `M` 是左右对称翻转：

```text
M(1) = 1
M(2) = 3
M(3) = 2
M(4) = 7
M(5) = 6
M(6) = 5
M(7) = 4
```

所以：

```text
H = [1,2,3,4,5,6,7]
M(H) = [1,3,2,7,6,5,4]
```

这不是随机打乱。

它是保持树结构的左右镜像。

## 什么是 kernel 共轭

局部 kernel 写成：

```text
theta = [theta_root, theta_left, theta_right]
```

如果树左右翻转，那么 left 和 right 的意义也交换。

所以共轭 kernel 应该是：

```text
conj(theta) = [theta_root, theta_right, theta_left]
```

例如这次实验用的是非对称 kernel：

```text
theta = [0.5, 1.25, -0.75]
```

它的共轭翻转是：

```text
conj(theta) = [0.5, -0.75, 1.25]
```

注意这里 left/right 不一样。

如果 left/right 本来相等，比如 `[1,1,1]`，那翻不翻都一样，证明就没有力量。

所以这次必须用非对称 kernel。

## 要证明的等式

TreeHeap 局部卷积：

```text
K_theta(H)[i]
  = theta_root  * H[i]
  + theta_left  * H[left(i)]
  + theta_right * H[right(i)]
```

我们要证明：

```text
M(K_theta(H)) = K_conj(theta)(M(H))
```

中文说就是：

```text
先卷积再翻转
等于
先翻转树，再用翻转后的 kernel 卷积
```

这就是共轭对称。

## 一个具体例子

输入：

```text
H = [1,2,3,4,5,6,7]
theta = [0.5, 1.25, -0.75]
```

对 root 节点：

```text
K_theta(H)[1]
  = 0.5*1 + 1.25*2 - 0.75*3
  = 0.75
```

对 node 2：

```text
K_theta(H)[2]
  = 0.5*2 + 1.25*4 - 0.75*5
  = 2.25
```

对 node 3：

```text
K_theta(H)[3]
  = 0.5*3 + 1.25*6 - 0.75*7
  = 3.75
```

所以卷积后内部节点是：

```text
[0.75, 2.25, 3.75]
```

再 mirror，node 2 和 node 3 会交换。

如果我们先 mirror 输入：

```text
M(H) = [1,3,2,7,6,5,4]
```

再用共轭 kernel：

```text
conj(theta) = [0.5, -0.75, 1.25]
```

得到的结果应该完全对应。

这就是实验要测的东西。

## 实验一：演绎等式检查

第一部分不是训练。

它直接检查：

```text
M(K_theta(H)) == K_conj(theta)(M(H))
```

在随机 test / OOD heaps 上测误差。

结果：

| 指标 | 数值 |
|---|---:|
| flipped-kernel test max error | `8.88e-16` |
| flipped-kernel OOD max error | `3.55e-15` |
| unflipped-kernel mean error | `6.4372` |

解释：

```text
用 conj(theta) 时，误差是机器精度。
不用 conj(theta) 时，误差很大。
```

这说明共轭翻转不是平凡成立的。

它依赖：

```text
树 mirror
kernel left/right 也 mirror
```

## 实验二：从 mirrored data 学回共轭 kernel

第二部分是学习。

训练数据是 mirrored data。

目标是让模型从数据中学出：

```text
conj(theta) = [0.5, -0.75, 1.25]
```

结果：

| 指标 | 数值 |
|---|---:|
| learned mirrored theta | `[0.5000000000000002, -0.7499999999999998, 1.2499999999999996]` |
| theta-conj L2 error | `5.44e-16` |
| learned test MSE | `1.01e-30` |
| learned OOD MSE | `9.76e-30` |

这说明：

```text
不只是手写公式成立。
参数 Theta 也能从 mirrored data 学回共轭 kernel。
```

## Claim 状态

```text
S1-KERNEL-CONJ-C01:
TreeHeap local convolution is equivariant under mirror conjugation:
M(K_theta(H)) = K_conj(theta)(M(H)).

status: supported pilot
```

证据目录：

```text
ara/s1-echo/evidence/s1_conjugate_kernel_symmetry_probe/
```

脚本：

```text
ara/s1-echo/src/s1_conjugate_kernel_symmetry_probe.py
```

## 这说明了什么

SPR-039 证明：

```text
TreeHeap kernel 可以学会局部卷积。
```

SPR-040 继续证明：

```text
TreeHeap kernel 不只是简单平移求和。
它还可以服从结构变换下的共轭规律。
```

这很重要。

因为如果 TreeHeap 只是一个数组，那么 mirror 只是重排。

但如果 TreeHeap 是结构化空间，那么 mirror 应该要求：

```text
数据结构变换
算子也随之变换
```

这就是共轭。

## 还没有证明什么

这次没有证明：

```text
语言理解
WMT 翻译
任意群等变
真实语义镜像
TreeHeap 胜过所有 flat model
```

它只证明一个局部代数事实：

```text
TreeHeap 的 root/left/right kernel
在 mirror 操作下有正确的共轭形式。
```

## 下一步

下一步可以扩展：

```text
1. scalar kernel -> vector / matrix kernel
2. depth-2 tree -> deeper recursive TreeHeap
3. mirror conjugation -> rotate / path permutation / slot conjugation
4. single kernel -> multi-kernel bank 的对称变换
```

如果这些继续成立，TreeHeap 的 kernel 就不只是“能算”。

它会开始接近一个结构化算子系统：

```text
结构变换
算子共轭
参数学习
局部卷积
```

## 一句话总结

SPR-040 的结论是：

```text
TreeHeap 局部卷积满足 mirror conjugation：
树翻转时，kernel 的 left/right 权重也必须翻转；
这个共轭 kernel 既能手算成立，也能从 mirrored data 中学出来。
```

> **ARA**: [conjugate kernel symmetry](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/conjugate_kernel_symmetry.md) / [evidence](https://github.com/houming818/sametime/tree/main/ara/s1-echo/evidence/s1_conjugate_kernel_symmetry_probe) / [claims](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/claims.md)
