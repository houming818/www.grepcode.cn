---
title: "[SPR-021] C05：TreeHeap 不能只是披着树皮的 MLP"
date: 2026-06-23
weight: 21
author: nio (Houming818) & Codex Review
description: "把 C05 改成结构 proof：如果公式里没有路径、前缀、子堆和递归 plus，它就只是 flat soft memory。"
tags: [SPR, TreeHeap, ARA, C05, Experiment]
---

# C05：TreeHeap 不能只是披着树皮的 MLP

上一篇 `SPR-020` 说清楚了一件事：

```text
Soft Plus 的梯度管道已经通了。
但 clean kernel 是否能自己学会路由，还没有证明。
```

然后 Houming818 提了一个更深的问题：

```text
如果公式里没有地址、路径、子结构，
那它看起来还是一个 MLP 或线性内存，
只是外面贴了 TreeHeap 这个名字。
```

这个批评是对的。

所以 `C05` 不能只问：

```text
kernel-guided soft plus 能不能训练？
```

它必须先问：

```text
这个 kernel 到底有没有用到 TreeHeap 的结构？
```

## Flat MLP 的自然形式

线性回归是：

$$
\hat y = Wx + b
$$

MLP 是：

$$
\hat y = f_\theta(x)
$$

这类模型的核心是：

```text
把输入 x 映射到一个任务空间；
再通过距离、logit、argmax 得到输出。
```

这没有问题。

但它是 flat 的。

它没有天然的：

```text
地址；
路径；
前缀；
子堆；
递归更新。
```

如果 TreeHeap 公式只是：

$$
H_{t+1}
=
\sum_a p(a \mid H_t,x_t)\operatorname{Plus}_a(H_t,x_t)
$$

那还不够。

因为这里的 \(a\) 可能只是普通数组槽位：

```text
a = 0, 1, 2, 3, ...
```

这会退化成：

```text
softmax memory write
```

也就是一个 flat memory MLP。

## TreeHeap 的地址必须是路径

TreeHeap 里的地址不应该只是数字。

它应该是路径：

$$
a \in \{L,R\}^{*}
$$

例如：

```text
epsilon = root
L       = root -> left
R       = root -> right
LLR     = root -> left -> left -> right
```

这个路径空间有一个 flat index 没有的性质：

```text
前缀关系。
```

例如：

```text
L 是 LL 和 LR 的共同前缀；
LL 和 LR 比 LL 和 RR 更接近；
LLR 的父路径是 LL。
```

这就是结构。

所以 TreeHeap 的 kernel 不能只看：

```text
address_id
```

而应该看：

$$
K_\theta(\pi(a), \operatorname{subheap}(H,a), x)
$$

其中：

```text
pi(a)
路径表示

subheap(H,a)
以地址 a 为 root 的局部子堆

x
当前输入或查询
```

## Plus 也必须是递归的

如果 `Plus_a` 只是：

```text
arr[a] = x
```

那它仍然是数组写入。

TreeHeap 的 plus 应该沿路径递归。

如果目标地址是：

```text
a = d :: a'
```

其中 \(d\) 是第一步方向：

```text
d in {L, R}
```

那么递归 plus 应该是：

$$
\operatorname{Plus}^{tree}_{d::a'}(H,x)
=
\operatorname{rebuild}
(
root(H),
\operatorname{Plus}^{tree}_{a'}(child_d(H),x),
child_{\bar d}(H)
)
$$

终止条件是：

$$
\operatorname{Plus}^{tree}_{\epsilon}(H,x)
=
\operatorname{merge}(H,x)
$$

白话说：

```text
如果目标在 left 子树，
就递归更新 left 子树；
right 子树保持不变；
最后把 root、left、right 重新组装。
```

这才是结构化内存。

## C05 的新公式

所以 C05 的候选公式应该写成：

$$
H_{t+1}
=
\sum_{a \in A(H_t)}
\operatorname{softmax}_a
\left(
K_\theta(\pi(a), \operatorname{subheap}(H_t,a), x_t)
\right)
\cdot
\operatorname{Plus}^{tree}_{\phi,a}(H_t,x_t)
$$

这个式子里必须有三件东西：

```text
pi(a)                  路径
subheap(H_t,a)          子堆
Plus^{tree}_{a}         递归 plus
```

少了这些，C05 就不应该升级。

## 实验怎么 proof

我们设计一个很小的 toy。

生成一棵二叉树，在某个地址插入一个局部 pattern：

```text
pattern = (root_value, left_value, right_value)
```

例如：

```text
        0.90
       /    \
    -0.40   0.70
```

任务是：

```text
给定整棵树和 pattern，
找出 pattern 在哪个地址。
```

训练时只把 pattern 放在浅层：

```text
depth = 2, 3
```

测试时把 pattern 放到深层：

```text
depth = 5, 6
```

如果模型只是记地址，它应该失败。

如果模型真的看子堆，它应该能迁移。

## 四个模型

我们比较四个版本。

### C0：flat address

只看绝对地址编号。

```text
这个位置是 0 号、1 号、2 号……
```

它没有路径，也没有子堆。

预期：

```text
训练内可能记住；
未见深度会失败。
```

### C1：path only

看路径：

```text
L, R, LL, LR, ...
```

但不看节点内容。

预期：

```text
如果目标 pattern 随机出现在不同地址，
path only 也无法知道哪个子堆匹配。
```

### C2：subheap kernel

看局部子堆：

```text
candidate_root
candidate_left
candidate_right
```

并和 query pattern 比较。

预期：

```text
即使 pattern 移到深层，也能找到。
```

### C3：path + subheap kernel

同时看：

```text
路径
子堆
```

并能返回：

```text
目标地址路径
```

这个版本最接近 TreeHeap C05。

## 判定标准

如果结果是：

```text
C0 / C1 在深层失败；
C2 / C3 在深层成功；
```

说明：

```text
subheap kernel 真的提供了迁移能力。
```

如果 C3 还能返回合法路径：

```text
root -> left -> right -> ...
```

说明：

```text
它不仅找到了目标，还能进入 recursive plus。
```

这才是 TreeHeap 的味道。

## 实验结果

实验已经执行：

```text
src/structural_c05_probe.py
```

证据目录：

```text
ara/m0-treeheap-math/evidence/structural_c05_probe/
```

结果表：

| Variant | Train acc | Test acc | Hit@3 | Mean rank |
|---|---:|---:|---:|---:|
| flat_address | 0.439 | 0.000 | 0.000 | 16.09 |
| path_only | 0.439 | 0.000 | 0.000 | 35.44 |
| subheap_kernel | 1.000 | 1.000 | 1.000 | 1.00 |
| path_subheap_kernel | 1.000 | 1.000 | 1.000 | 1.00 |

这个结果很清楚。

`flat_address` 在训练集还有一点记忆能力：

```text
train_acc = 0.439
```

但到未见深度以后：

```text
test_acc = 0.000
```

说明它没有学到可迁移结构，只是在浅层地址上做记忆。

`path_only` 也失败：

```text
test_acc = 0.000
```

这说明只知道路径形式还不够。因为目标 pattern 是随机放到某个深层子堆里的，只看：

```text
LLR
RRLL
LRRL
```

无法知道哪个位置真的匹配 pattern。

真正成功的是：

```text
subheap_kernel
path_subheap_kernel
```

它们在未见深度上都是：

```text
test_acc = 1.000
mean_rank = 1.00
```

也就是说，同一个局部子堆 kernel 可以在更深地址复用。

## 这证明了什么

这次 proof 支持的是：

```text
M0-SOFT-C07:
TreeHeap kernel 必须暴露 path / subheap / recursive route 结构，
否则会退化成 flat soft memory。
```

更具体地说：

```text
subheap 是有效结构信号；
flat address 不是；
path alone 也不是。
```

这回应了前面那个批评：

```text
如果公式里没有地址、路径、子结构，
它就不像 TreeHeap。
```

现在实验告诉我们：

```text
至少在这个 toy 上，
子堆结构不是装饰；
它直接决定了未见深度迁移是否成立。
```

## 这没有证明什么

这个实验仍然很窄。

它没有证明：

```text
TreeHeap 会语言；
TreeHeap 会 WMT；
TreeHeap 已经优于 Transformer；
C05 的完整写入机制已经胜出。
```

为什么还不能升级完整 C05？

因为完整 C05 问的是：

```text
kernel-guided Soft Plus
是否优于 naive soft memory write
和 generic encoder soft plus？
```

而本实验只证明：

```text
结构特征是必要的；
subheap kernel 能做未见深度 relocation。
```

所以结论是：

```text
M0-SOFT-C07 -> supported pilot
M0-SOFT-C05 -> 仍然 open
```

下一步才是完整写入机制对比：

```text
A: naive soft memory write
B: encoder soft plus
C: path + subheap kernel-guided soft plus
```

> **License: GPLv3**
