---
title: "[SPR-038] 梯度到底改什么：TreeHeap 状态松弛的边界"
date: 2026-06-30
weight: 38
author: nio (Houming818) & Codex Review
description: "SPR-038 修订版：区分参数 TreeHeap、激活 TreeHeap、物理地址、语义地址和 kernel；说明本实验只证明状态松弛，不证明 kernel 参数学习。"
tags: [SPR, TreeHeap, ARA, Gradient, Energy, Relaxation]
---

# 梯度到底改什么：TreeHeap 状态松弛的边界

这篇是 SPR-038 的修订版。

原版里有一个说法不够严谨：

```text
函数不变。
地址规则不变。
kernel 系数不变。
只有 arr[i] 的状态在移动。
```

Houming818 指出这里混淆了几层东西。

这个批评是对的。

TreeHeap 里至少要区分五个对象：

```text
Theta  = parameter TreeHeap，也就是模型参数
H      = activation / memory TreeHeap，也就是当前样本上的状态
A      = physical address rule，比如 left(i)=2i, right(i)=2i+1
K_Theta = kernel operator，由参数 Theta 定义的局部卷积算子
L      = scalar loss / energy，用来产生梯度
```

类比线性回归：

```text
y = w*x + b
```

普通机器学习里，`w` 和 `b` 是参数。

放到 TreeHeap 口径里，`w` 和 `b` 可以不是两个孤立标量，而是一个很小的参数堆：

```text
Theta = {
  w,
  b
}
```

所以“参数就是一个 TreeHeap”是合理的。

更一般地：

```text
H_next = K_Theta(H, A)
L = loss(H_next)
```

如果训练模型参数，就是：

```text
Theta <- Theta - eta * grad_Theta L
```

如果调整当前 heap 状态，就是：

```text
H <- H - eta * grad_H L
```

这两件事不是一回事。

## 物理地址和语义地址

原文说“地址规则不变”，也需要修正。

严格说，不变的是物理寻址规则：

```text
left(i)  = 2i
right(i) = 2i + 1
```

也就是数组位置和父子索引关系没有变。

但是 `arr[i]` 的向量状态一旦变了，它在语义空间里的位置当然也变了。

所以应该写成：

```text
物理地址 A 不变。
语义状态 H[i] 可变。
语义地址 / 向量位置会随 H[i] 改变。
```

这点很重要。

否则会误以为 SPR-038 证明了“地址不变还学习了结构”。

它没有。

它只证明：

```text
在固定物理地址规则下，当前 heap state 可以被一个 scalar energy 推动，向低能量状态移动。
```

## SPR-038 到底证明了什么

SPR-038 的 claim 是：

```text
S1-RELAX-C01:
A differentiable energy over the current TreeHeap state can generate gradients
that relax arr[i] toward a lower-energy equilibrium while kernel parameters
and address rules remain fixed.
```

修订后，这句话要更精确地理解为：

```text
Theta 不更新。
K_Theta 不更新。
物理地址规则 A 不更新。
当前样本的 heap state H 更新。
```

也就是：

```text
这不是参数学习。
这是状态松弛。
```

它更像一个物理系统：

```text
给定能量函数 E(H)，
当前状态 H 沿着 -grad_H E(H) 移动。
```

## Proof 1：标量能量只说明 loss 能产生梯度

第一个 toy 是：

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

梯度下降后：

```text
[2.0, 1.0, 3.0]
-> [2.0, 2.0, 2.0]
```

实验结果：

```text
initial energy = 4.0
final energy   = 9.86e-31
energy ratio   = 2.47e-31
```

这个 proof 的意义很窄：

```text
只要有 scalar loss / energy，
就能对当前 H 求梯度，
并让 H 沿低能量方向移动。
```

它不说明 kernel 结构已经学习了。

它也不说明参数 TreeHeap `Theta` 已经被训练。

## Proof 2：7 节点 TreeHeap 状态松弛

第二个 toy 使用 7 节点树：

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
1,2,3 是可更新 internal heap state
```

注意：

```text
更新的是 H[1], H[2], H[3]
不是更新 Theta
```

能量有两部分：

```text
E_consistency:
  parent 应该接近 children 的局部组合

E_relation:
  internal node 应该接近固定 relation anchor
```

总能量：

```text
E_total(H) = E_consistency(H) + E_relation(H)
```

32 次随机初始化结果：

| 指标 | 数值 |
|---|---:|
| scalar energy ratio | 2.47e-31 |
| mean vector energy ratio | 1.24e-13 |
| max vector energy ratio | 3.69e-13 |
| mean centroid error drop | 3.0393 |
| pass rate | 1.0000 |
| pilot pass | true |

这说明：

```text
在这个 toy 能量场里，
TreeHeap state H 可以稳定收敛。
```

但仍然要强调：

```text
这不是 kernel 参数学习。
```

## kernel 卷积到底应该是什么

Houming818 给了一个更贴切的例子。

还是这棵树：

```text
        1
      /   \
     2     3
    / \   / \
   4   5 6   7
```

如果 kernel 是：

```text
[root, left, right] = [1, 1, 1]
```

对每个内部节点做局部卷积：

```text
H'[1] = 1*H[1] + 1*H[2] + 1*H[3] = 1 + 2 + 3 = 6
H'[2] = 1*H[2] + 1*H[4] + 1*H[5] = 2 + 4 + 5 = 11
H'[3] = 1*H[3] + 1*H[6] + 1*H[7] = 3 + 6 + 7 = 16
```

叶子暂时保持不变，则得到：

```text
[6, 11, 16, 4, 5, 6, 7]
```

这个例子比 SPR-038 更接近 TreeHeap kernel 的核心。

因为 kernel 不是抽象地“调状态”，而是在做：

```text
观察一个局部 subheap
计算一个新 state
把局部结构信息写回当前节点
```

也就是：

```text
S_i = [H[i], H[left(i)], H[right(i)]]
H'[i] = K_Theta(S_i)
```

如果 kernel 是线性的：

```text
H'[i] = theta_root * H[i]
      + theta_left * H[left(i)]
      + theta_right * H[right(i)]
```

那么 `[1,1,1]` 就是一个最简单的 TreeHeap 卷积核。

## 和 Transformer 的关系

Transformer 里常见的核心相似度是：

```text
score(i,j) = Q_i dot K_j
```

它是在 flat token 空间上做全连接关系计算。

TreeHeap kernel 可以看成：

```text
score / state = K_Theta(root, left, right)
```

也就是在局部子堆上做结构化关系计算。

所以更合理的类比不是：

```text
TreeHeap 已经替代 Transformer
```

而是：

```text
Transformer 在 flat all-to-all token 图上学习共现关系。
TreeHeap 希望在 address/path/subheap 结构上学习局部卷积关系。
```

如果 `K_Theta` 学到的是类似 `[1,1,1]`、`[0.2,0.5,0.3]`、镜像 kernel、stop/left/right kernel 这样的结构算子，那么 TreeHeap 才真正有自己的归纳偏置。

## 修订后的结论

SPR-038 支持的结论是：

```text
TreeHeap 的当前状态 H 可以在 scalar energy 下做梯度松弛。
```

SPR-038 不支持的结论是：

```text
TreeHeap kernel 参数 Theta 已经能通过梯度学会卷积结构。
```

所以 SPR-038 的位置应该是：

```text
状态梯度 proof
不是参数学习 proof
```

下一步 SPR-039 应该转向：

```text
parameter TreeHeap / kernel Theta learning proof
```

最小实验就是：

```text
输入 H = [1,2,3,4,5,6,7]
目标 H' = [6,11,16,4,5,6,7]

模型不知道 kernel = [1,1,1]
只通过 loss 学 theta_root, theta_left, theta_right
```

如果训练后得到：

```text
Theta ~= [1,1,1]
```

那才说明：

```text
TreeHeap kernel 的参数可以通过 loss / gradient 学到局部卷积规则。
```

这会成为 SPR-039 的核心。

> **ARA**: [heap-state relaxation](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/heap_state_relaxation.md) / [claims](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/claims.md) / [evidence](https://github.com/houming818/sametime/tree/main/ara/s1-echo/evidence/s1_heap_state_relaxation_probe)
