---
title: "[SPR-040] TreeHeap kernel 的 mirror 手性翻转：几何翻转如何变成代数置换"
date: 2026-07-01
weight: 40
author: nio (Houming818) & Codex Review
description: "SPR-040 proof：证明 TreeHeap 局部卷积在左右 mirror 下可以由堆地址置换和 kernel 槽位置换实现，并且 mirrored kernel 可以从数据中学回。"
tags: [SPR, TreeHeap, ARA, Kernel, Convolution, Mirror]
---

# TreeHeap kernel 的 mirror 手性翻转：几何翻转如何变成代数置换

先统一术语。

之前草稿里用了“共轭”这个词。这个词容易让人想到复数共轭、矩阵共轭、群表示里的 conjugation。SPR-040 现在不再这样叫。

这里讨论的是：

```text
mirror / chiral flip / 左右镜像翻转
```

也就是把一棵 TreeHeap 的 left 和 right 对换。

这篇文章要证明一件很具体的事：

```text
几何上的左右翻转，
可以在代数层面变成两个置换：

1. 堆地址置换
2. kernel 槽位置换
```

这不是语言理解 proof，也不是 WMT proof。它是 TreeHeap kernel 工具箱里的一个基础 proof。

## 为什么要证明 mirror

SPR-039 证明了：

```text
参数 TreeHeap Theta 可以通过梯度学习一个局部卷积 kernel。
```

例如在 7 节点堆上：

```text
        1
      /   \
     2     3
    / \   / \
   4   5 6   7
```

一个最小 kernel 可以写成：

```text
theta = [theta_root, theta_left, theta_right]
```

它在某个内部节点 `i` 上做：

```text
K_theta(H)[i]
  = theta_root  * H[i]
  + theta_left  * H[left(i)]
  + theta_right * H[right(i)]
```

如果 `theta = [1,1,1]`，它就是局部求和。

但 Houming818 提醒了一个更关键的问题：

```text
TreeHeap kernel 不能只会求和。
它应该能表达结构操作。
```

比如，左右镜像翻转。

如果 TreeHeap 真的是结构化空间，那么：

```text
树翻了，
算子也应该按结构翻。
```

这就是 SPR-040。

## mirror 在堆地址上的定义

仍然看这棵 7 节点完全二叉堆：

```text
        1
      /   \
     2     3
    / \   / \
   4   5 6   7
```

左右 mirror 后：

```text
        1
      /   \
     3     2
    / \   / \
   7   6 5   4
```

所以地址映射是：

```text
M(1) = 1
M(2) = 3
M(3) = 2
M(4) = 7
M(5) = 6
M(6) = 5
M(7) = 4
```

如果用数组表示：

```text
H = [1,2,3,4,5,6,7]
M(H) = [1,3,2,7,6,5,4]
```

这不是随便重排。

它是一个保持树结构的左右镜像。

代数上可以写成：

```text
H' = P_m H
```

其中 `P_m` 是堆地址的置换矩阵。对于 7 节点堆，它对应：

```text
P_m = (0, 2, 1, 6, 5, 4, 3)
```

这里用的是 zero-based index。

## mirror 在 kernel 槽位上的定义

局部 kernel 是：

```text
theta = [root, left, right]
```

如果树左右翻转，left 和 right 的意义也要交换。

所以 kernel 也要 mirror：

```text
P_lr(theta) = [root, right, left]
```

写成矩阵：

```text
P_lr =
[[1,0,0],
 [0,0,1],
 [0,1,0]]
```

这就是这篇 proof 的重点。

不是只翻树。

而是：

```text
翻树地址 P_m
同时翻 kernel 槽位 P_lr
```

## Claim

SPR-040 的 claim 是：

```text
S1-KERNEL-MIRROR-C01:

TreeHeap local convolution is equivariant under mirror / chiral flip:

P_m K_theta(H) = K_{P_lr theta}(P_m H)
```

中文说：

```text
先卷积，再 mirror
等价于
先 mirror，再用 mirror 后的 kernel 卷积。
```

这就是“几何操作由代数操作实现”。

## 一个具体例子

输入：

```text
H = [1,2,3,4,5,6,7]
theta = [0.5, 1.25, -0.75]
```

这个 kernel 是故意选成非对称的。

因为如果用 `[1,1,1]`，left 和 right 权重一样，翻不翻都一样，证明没有力量。

root 节点的卷积：

```text
K_theta(H)[1]
  = 0.5*1 + 1.25*2 - 0.75*3
  = 0.75
```

node 2：

```text
K_theta(H)[2]
  = 0.5*2 + 1.25*4 - 0.75*5
  = 2.25
```

node 3：

```text
K_theta(H)[3]
  = 0.5*3 + 1.25*6 - 0.75*7
  = 3.75
```

内部节点结果是：

```text
[0.75, 2.25, 3.75]
```

mirror 后，node 2 和 node 3 的结构位置交换。

如果我们先 mirror 输入：

```text
P_m H = [1,3,2,7,6,5,4]
```

就必须同时使用 mirrored kernel：

```text
P_lr theta = [0.5, -0.75, 1.25]
```

这时两条路径会得到同一个结果：

```text
P_m K_theta(H)
=
K_{P_lr theta}(P_m H)
```

## Proof 分两部分

### Proof A：演绎等式检查

这部分不训练。

直接检查：

```text
left  = P_m K_theta(H)
right = K_{P_lr theta}(P_m H)
```

然后算：

```text
max_abs(left - right)
```

如果这个误差接近 0，就说明代数等式成立。

### Proof B：归纳学习检查

这部分训练。

我们构造 mirrored data：

```text
input  = P_m H
target = internal_nodes(P_m K_theta(H))
```

然后让一个三槽位参数：

```text
Theta = [theta_root, theta_left, theta_right]
```

通过 MSE loss 和梯度下降学习。

如果数据真的携带 mirror 规律，那么它应该学出：

```text
Theta ~= P_lr theta = [0.5, -0.75, 1.25]
```

这一步说明的不只是“公式手写成立”，还说明这个 mirrored kernel 可以从数据里被学回。

## 实验结果

脚本：

```text
ara/s1-echo/src/s1_mirror_kernel_symmetry_probe.py
```

证据：

```text
ara/s1-echo/evidence/s1_mirror_kernel_symmetry_probe/
```

主机：

```text
io.grepcode.cn
```

结果：

| 指标 | 数值 |
|---|---:|
| pilot_pass | `true` |
| flipped-kernel test max error | `8.88e-16` |
| flipped-kernel OOD max error | `3.55e-15` |
| unflipped-kernel mean error | `6.4372` |
| learned mirrored theta | `[0.5000000000000002, -0.7499999999999998, 1.2499999999999996]` |
| theta-mirror L2 error | `5.44e-16` |
| learned test MSE | `1.01e-30` |
| learned OOD MSE | `9.76e-30` |

解释：

```text
用 mirrored kernel 时，误差是机器精度。
不用 mirrored kernel 时，误差明显变大。
从 mirrored data 训练时，参数能学回 [root,right,left]。
```

所以：

```text
S1-KERNEL-MIRROR-C01 -> supported pilot
```

## 这说明了什么

SPR-040 支持一个很重要的方向：

```text
TreeHeap 的几何操作，可以下降到代数操作。
```

具体到这篇：

```text
几何 mirror
-->
堆地址置换 P_m
+ kernel 槽位置换 P_lr
```

这让 TreeHeap kernel 不只是“局部求和器”。

它开始像一个结构化算子系统：

```text
卷积
写入
读取
mirror
路径移动
子堆组合
子堆分解
```

这些都可以成为后续 encoder/decoder 的基本工具。

## 还没有证明什么

这次没有证明：

```text
语言理解
WMT 翻译
真实语义 mirror
任意群等变
TreeHeap 胜过所有 flat model
```

它只证明：

```text
TreeHeap 的 root/left/right 局部卷积，
在 mirror 操作下有正确的代数置换形式。
```

## 下一步

接下来可以沿着几个方向扩展：

```text
1. scalar kernel -> vector / matrix kernel
2. depth-1 kernel -> recursive depth-k kernel
3. mirror -> path permutation / subtree move / slot transform
4. single kernel -> multi-kernel bank
5. toy heap -> short real corpus TreeHeap echo
```

如果这些继续成立，TreeHeap 的 kernel 就不是一组临时写出来的函数，而是一个可以逐步扩展的结构化代数工具箱。

一句话总结：

```text
SPR-040 证明：
TreeHeap 的左右 mirror 可以用代数置换实现；
树地址要翻，kernel 的 left/right 槽位也要翻；
这个规则既能手算成立，也能从 mirrored data 里被梯度学回。
```

> ARA: [mirror kernel symmetry](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/mirror_kernel_symmetry.md) / [evidence](https://github.com/houming818/sametime/tree/main/ara/s1-echo/evidence/s1_mirror_kernel_symmetry_probe) / [claims](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/claims.md)
