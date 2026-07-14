---
title: "[SPR-053] 不让神经网络重写整棵树：让它学习选择 TreeHeap 算子"
date: 2026-07-12
lastmod: 2026-07-12
weight: 53
author: Codex Review
description: "检验结构能否进入 encoder，以及 TreeHeap 能否用自身算子恢复数据。未见地址成功，未见深度失败，并定位了失败位置。"
tags: [SPR, TreeHeap, ARA, M0, Encoder, Algebra, OOD]
---

# 不让神经网络重写整棵树：让它学习选择 TreeHeap 算子

Houming818 提出了两个比“再调一个模型”更根本的判断：

1. 数据中的结构规律，应该能够被 encoder 提取，并成为 encoder 与 decoder 共同使用的表示；
2. TreeHeap 中的数据变化，应该由 TreeHeap 自己的地址、子堆与算子完成，而不是让普通 MLP 把整个数组重新写一遍。

本实验不拿语言任务掩盖问题，而是在一个有限、可检查的世界里问：**神经网络能否只负责认出操作，真正的数据变换交给 TreeHeap 代数执行？**

## 1. 一个七节点例子

采用从 1 开始编号的二叉堆：

```text
          A[1]
        /      \
     A[2]      A[3]
     /  \      /  \
  A[4] A[5] A[6] A[7]
```

地址规则是：

\[
\operatorname{left}(i)=2i,\qquad \operatorname{right}(i)=2i+1
\]

为了让错误可以被客观识别，我们构造一个简单的数论世界：

\[
A[2i]=2A[i],\qquad A[2i+1]=2A[i]+1
\]

若根节点为 1，合法状态就是 `[1,2,3,4,5,6,7]`。实验随机选择一段子堆，用 TreeHeap 原生算子破坏它：

```text
MIRROR(address, depth)
SUBTREE_PLUS(address, depth, delta)
```

例如 `SUBTREE_PLUS(2, 1, 3)` 把地址 2 及其下一层子节点都加 3；`MIRROR` 递归交换指定子堆的左右分支。

## 2. encoder 学习什么

这里的参数 \(\theta\) 不是目标 TreeHeap，也不保存每一棵答案树。它是在所有节点上共享的小型识别 kernel：

\[
K_\theta(H,i)\rightarrow\bigl(P(o),P(i),P(d),P(\delta)\bigr)
\]

- \(H\)：当前被破坏的完整 TreeHeap 状态；
- \(i\)：kernel 正在观察的候选地址；
- \(o\)：`mirror` 或 `plus`；
- \(d\)：递归深度；
- \(\delta\)：加法参数。

kernel 读取当前节点及其父子违反数论规则的残差，并汇总各相对深度的子堆残差。它不输出 511 个新数，而是输出一张很短的维修工单：

```text
operator = plus
address  = 12
depth    = 2
delta    = -3
```

概率桶坍缩后，固定 executor 执行逆操作：

\[
\hat H=E_{\text{TreeHeap}}(H,\hat o,\hat i,\hat d,\hat\delta)
\]

最后检查 \(\hat H\) 是否与原始合法 TreeHeap 逐节点完全相同。神经网络没有权限直接生成答案数组。

| 对象 | 含义 | 是否学习 |
|---|---|---|
| \(H\) | 当前 TreeHeap 数据状态 | 每个样本不同 |
| \(\theta\) | 识别操作程序的共享 kernel | 梯度学习 |
| 地址和算子 | `2i/2i+1`、mirror、subtree plus | 固定数学规则 |

## 3. 怎样避免背答案

训练只出现浅地址和递归深度 1、2。测试分为：

| 测试 | 地址 | 操作深度 |
|---|---|---|
| IID | 训练范围内 | 1--2 |
| OOD address | 从未训练的深地址 | 1--2 |
| OOD depth | 浅地址 | 从未训练的 3--4 |
| OOD joint | 深地址 | 3--4 |

两个对照模型是：

- `flat_program`：把 511 个位置摊平，再预测同一张维修工单；
- `flat_rewriter`：把 511 个位置摊平，直接输出修复后的 511 个数。

## 4. 结果体检表

数值是整棵树完全恢复的比例，越大越好：

| 测试 | 结构程序 + 固定算子 | Flat 程序 | Flat 直接改写 | 判断 |
|---|---:|---:|---:|---|
| IID | **92.70%** | 15.35% | 72.05% | 强阳性 |
| 未见地址 | **84.00%** | 0% | 0% | 强阳性 |
| 未见深度 | **4.40%** | 0% | 0% | 不合格 |
| 地址与深度同时未见 | **5.80%** | 0% | 0% | 不合格 |

| 模型 | 参数量 |
|---|---:|
| 结构程序 encoder | **41,671** |
| Flat 程序预测 | 235,913 |
| Flat 直接改写 | 196,927 |

这支持一个窄但实在的结论：**共享的树结构 kernel 学到了一种可以搬到新地址的识别规则；摊平模型只记住训练位置。**

## 5. 为什么未见深度失败

我们增加了一项诊断：把真实地址告诉 depth decoder，只检查它能不能读出从未训练的深度 3、4。结果是 **93.65%**。

可是不提供真实地址时，OOD-depth 的地址准确率只有 **10.75%**，整树恢复随之跌到 4.40%。这说明：

> 深度本身大多可以从残差波中读出，但更深的操作改变了整片残差的形状，使只见过浅操作的地址定位器走错了。

所以当前 Claim 只能“部分支持”。它证明了地址迁移，没有证明递归深度外推。

下一步不是增加更大的 MLP，而是把一次性猜全局地址改成真正共享的递归过程：kernel 从根开始反复输出 `stop/left/right`，在每一层用同一规则寻找残差边界。只有它在深度 1、2 上训练，却能循环到 3、4，才算递归规律进入 encoder。

## 6. 单机 AI 的存活空间

这个实验尚未证明语言、世界模型或意识，但展示了一条适合单机研究的计算路线：

```text
大网络直接生成全部状态
        改为
小网络识别短程序 + 确定代数执行大量状态变化
```

一次子堆 mirror 可以改变许多节点，但学习器只需输出算子、地址和深度。树越大，程序描述不必同比增长。这是 TreeHeap 可能节省样本、参数和计算的具体来源，不是口号。

真正的语言版本仍需回答：语料中的哪些规律能形成这种可执行程序，以及 encoder 如何在没有人工数论规则时发现它们。SPR-053 只搭起第一座受控桥梁：**结构可以进入短程序，短程序可以调用 TreeHeap 自身算子恢复数据；但递归定位还没有学会。**

## Evidence

- Claim: `M0-OPCODEC-C01`
- Source: [algebraic_operator_codec_probe.py](https://github.com/houming818/sametime/blob/main/ara/m0-treeheap-math/src/algebraic_operator_codec_probe.py)
- Evidence: [algebraic_operator_codec_probe](https://github.com/houming818/sametime/tree/main/ara/m0-treeheap-math/evidence/algebraic_operator_codec_probe)
- Seed: `53`
- Device: `io.grepcode.cn`, NVIDIA RTX 3090

---

## 版权、原创与许可证

Copyright (C) 2026 Houming818 and SameTime contributors.

本文由 Houming818 提出核心研究方向，Codex Review 参与数学整理、ARA 声明、实验实现与结果分析。正文、表格和伪代码为本项目原创表达；实验结论以公开 ARA 源码和 Evidence 为边界，不声称已经证明语言、世界模型或意识。

> **SPDX-License-Identifier: GPL-3.0-only**
> **License: GNU General Public License v3.0 only**

本文允许复制、修改和分发，但衍生版本必须继续遵守 GNU GPL v3，并保留版权、许可证、修改说明及来源声明。完整许可证文本见本站 [/LICENSE](/LICENSE)。

本文按“原样”提供，不附带任何明示或暗示担保。数学思想和事实本身不受版权垄断；本许可证适用于本文的原创文字、结构、表格、伪代码及其他可受版权保护的表达。
