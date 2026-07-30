---
title: "[SPR-076] TreeHeap 长距通信：不做全局 Attention，试试 XOR Butterfly"
date: 2026-07-30
lastmod: 2026-07-30
weight: 76
author: Houming818 & Codex Review
description: "审视二叉 TreeHeap 的长距瓶颈，放弃循环移位与全树 flat attention，提出基于二进制地址、局部可逆核和对数通信轮次的 XOR Butterfly 实验。"
tags: [SPR, TreeHeap, ARA, Butterfly, XOR, Long-Range, Reversible, Gradient, Experiment]
---

# TreeHeap 长距通信：不做全局 Attention，试试 XOR Butterfly

> **证据状态：实验预注册，尚无正式结果。**
>
> 本文首先公开问题、Claim、预测和反证条件。正式数据出来后再更新结论，不把数学上按定义成立的部分冒充语言能力。

## 1. 为什么突然要研究长距离

我们刚刚修正了 decoder 的一个设计：不再让 `STOP` gate 决定一棵子树有没有资格继续学习，而是强制执行递归。没有贡献的通道，可以让自己的 value 增量自然趋近于零。

但 Houming818 随即指出了更深的问题。

长度为 8 的 string 放进相邻二叉树以后：

```text
                    root
              /              \
          [0..3]             [4..7]
         /     \             /     \
      [0,1]   [2,3]       [4,5]   [6,7]
```

位置 0 和位置 1 很快相遇；位置 0 和位置 7 却必须一直上升到 root。

如果 leaf 0 的输出需要 leaf 7 的信息，计算需要经过多层 FOLD，再经过多层 UNFOLD。中间每一层都在改变分辨率。于是问题不再只是“梯度能不能到达”，而是：

> 远距离关系是否被迫穿过一个过于粗糙的 root 瓶颈？

## 2. 可逆不等于关系容易计算

当前 lifting TreeHeap 可以保存：

$$
H_{state}=\left(root,details,addresses\right)
$$

只要这些状态完整，FOLD/UNFOLD 可以做到数值闭合。

但是，“可以还原所有输入”不等于“任意两个位置的关系都已经在 root 中显式出现”。

例如：

$$
relation(x_0,x_7)
$$

可能需要同时观察两个遥远 leaf。即使 root 和 details 没有丢失它们，decoder 仍然需要一条合适的计算路径把它们放到同一个局部 kernel 中。

所以这里必须区分：

| 问题 | 含义 |
|---|---|
| 信息保存 | 原始 leaf 是否还能由 root + details 恢复 |
| 关系计算 | 两个遥远 leaf 是否能在较短路径内共同参与一个算子 |
| 语言理解 | 模型是否从真实语料中归纳出有用关系 |

本轮只研究第二项。

## 3. 为什么不直接让整棵树参加 Attention

一个直接方案是让 query 对所有 TreeHeap 节点做一次全局 softmax：

$$
C=\sum_i softmax(QK_i^T)V_i
$$

这样梯度很容易到达所有节点，但 READ 已经变成了 flat attention。树只负责提前制造一批向量，最终查询仍然是全局比较。

这可以作为诊断基线，却不能成为 TreeHeap 的核心答案。否则最合理的工程选择确实是直接使用 Transformer。

## 4. 为什么循环矩阵也不够

另一个想法是把 string 做循环移位：

```text
cat is running
is running cat
running cat is
```

它形成循环矩阵，适合做圆周卷积，也能让句尾与句首靠近。

问题是语言通常不是圆：

- 句尾和句首不天然相邻；
- 循环移动不会缩短所有位置对的距离；
- 如果真的把每个完整 rotation 挂在 leaf 上，会产生 $O(N^2)$ 数据复制；
- decoder 可能直接从复制的 string 绕过 TreeHeap。

所以循环矩阵提供了一个观察坐标系，但没有一般性解决长距通信。

## 5. 稀疏系统的客观下限

假设每个节点一轮只能与固定数量 $k$ 的邻居通信。经过 $t$ 轮，它最多影响大约 $k^t$ 个节点。要覆盖长度为 $N$ 的空间，至少需要：

$$
t=\Omega(\log_k N)
$$

因此，在不使用全连接的前提下，不能要求任意两个节点都一跳相遇。真正合理的目标是：

> 用 $O(\log N)$ 轮局部计算建立全局感受野，并避免所有信息同时挤入一个 root。

## 6. XOR Butterfly：利用二进制地址

长度 8 时，leaf 地址可以写成：

```text
0 = 000
1 = 001
2 = 010
3 = 011
4 = 100
5 = 101
6 = 110
7 = 111
```

第 $s$ 轮，让节点 $i$ 与下面的地址通信：

$$
partner_s(i)=i\operatorname{XOR}2^s
$$

三轮分别是：

```text
第 0 轮：(0,1) (2,3) (4,5) (6,7)
第 1 轮：(0,2) (1,3) (4,6) (5,7)
第 2 轮：(0,4) (1,5) (2,6) (3,7)
```

位置 7 的信息可以沿地址位传播：

```text
111 -> 110 -> 100 -> 000
```

三轮后到达位置 0。一般情况下，任意两个 $D$ 位地址最多相差 $D=\log_2N$ 个 bit。

这不是循环，也没有制造假的句首句尾关系。它是在逐位打开二进制地址空间。

## 7. 每一轮仍然只是二节点 kernel

最小的确定性 kernel 可以写成：

$$
c=\frac{a+b}{\sqrt{2}}
$$

$$
d=\frac{a-b}{\sqrt{2}}
$$

它可以精确逆运算：

$$
a=\frac{c+d}{\sqrt{2}},\qquad
b=\frac{c-d}{\sqrt{2}}
$$

并保持总能量：

$$
\lVert a\rVert^2+\lVert b\rVert^2
=
\lVert c\rVert^2+\lVert d\rVert^2
$$

因此，在纯线性合同中，它不会自然放大或缩小 norm。它也是正交变换，反向梯度拥有相同的范数保持性质。

学习版本仍然只在一对节点中计算，不建立全局注意力矩阵。

## 8. 它与普通二叉 FOLD 有什么不同

普通 FOLD 不断缩小宽度：

```text
8 -> 4 -> 2 -> 1
```

所有远程信息最后汇入一个 root。

Butterfly 保持固定宽度：

```text
8 -> 8 -> 8 -> 8
```

但每轮扩大每个位置的感受野：

```text
第 0 轮后：2 个地址
第 1 轮后：4 个地址
第 2 轮后：8 个地址
```

它不是新的外部内存，也不允许树无限生长。系统给定多少 leaf，就始终只使用多少 leaf。

推荐组合为：

```text
token leaves
    ↓
XOR Butterfly 局部通信
    ↓
带长距上下文的 leaves
    ↓
TreeHeap FOLD
    ↓
root + details
    ↓
TreeHeap UNFOLD
    ↓
对应的 Butterfly decoder
    ↓
leaf softmax
```

## 9. 这会不会又变成 flat

Butterfly 每轮只有 $N/2$ 次二节点操作，总操作数为：

$$
\frac{N}{2}\log_2N
$$

它没有构造 $N\times N$ 的 token 对矩阵。

| 结构 | 关系计算规模 | 任意节点通信距离 |
|---|---:|---:|
| Dense attention | $O(N^2)$ | 1 |
| 单棵相邻二叉树 | $O(N)$ | 最坏约 $2\log_2N$，经过 root |
| XOR Butterfly | $O(N\log N)$ | 最坏 $\log_2N$，无单 root 汇聚 |

它比单树付出更多计算，但仍比 dense attention 稀疏。是否值得，要由实验决定。

## 10. 本轮 Claim

### S3-TREEHEAP-BUTTERFLY-LONGRANGE-C01

固定容量的 XOR Butterfly，如果由局部二节点 kernel 组成，应当能够：

1. 在 $\log_2N$ 轮内建立所有地址之间的感受野；
2. 保持确定性正交合同的可逆性、能量与梯度尺度；
3. 在地址条件长距读取任务中，击败相同深度但始终只看邻接对的 kernel；
4. 击败把所有输入压入一个有限 root 再并行读出的 bottleneck；
5. 不构造 dense $N\times N$ attention。

这个 Claim 不包含语言理解，也不包含 Transformer 性能对比。

## 11. 归纳实验是什么

随机生成长度 32 的 token array，并给模型一个地址查询 $q$。输出位置 $i$ 的目标是：

$$
target[i]=source[i\operatorname{XOR}q]
$$

训练只使用二进制中含一个或两个 `1` 的查询。测试使用从未见过的三位及以上组合，包括：

```text
q = 31 = 11111
```

然后不重新训练，把同一个共享 kernel 放到长度 64：

```text
q = 63 = 111111
```

这在测试模型是否学会了“逐个地址 bit 执行局部交换”的组合规则，而不是记住完整地址。

## 12. 三个对照组

| 方案 | 做什么 |
|---|---|
| Butterfly | 每轮切换一个 XOR 地址 bit |
| Adjacent-only | 每轮都重复相邻配对 |
| Root bottleneck | 递归压到一个有限 root，再预测所有位置 |

三组使用相同随机 token、交叉熵、训练步数和测试查询。参数量与运行时间也会记录。

## 13. 预注册通过线

确定性合同必须全部通过：

```text
inverse MSE <= 1e-10
energy relative error <= 1e-6
最终地址覆盖率 = 100%
gradient norm ratio 位于 [0.999, 1.001]
```

三颗随机种子中至少两颗还要同时满足：

```text
width-32 未见查询准确率 >= 95%
最大距离查询准确率 >= 90%
width-64 未见宽度准确率 >= 90%
比 adjacent-only 高至少 25 个百分点
比 root-bottleneck 高至少 25 个百分点
```

如果数学合同通过、训练实验失败，只能保留“Butterfly 是合法代数工具”，不能说它是有效学习机制。

## 14. 即使成功，也还没有证明什么

通过本轮实验仍然不能说明：

- XOR 地址符合语言依存结构；
- WMT 翻译会改善；
- TreeHeap 已形成语义私有协议；
- Butterfly 比成熟 Transformer 更快；
- 合成地址搬运等于推理。

下一步只有在本轮结果成立后，才把 Butterfly 插入冻结的 WMT TreeHeap，用 matched ablation 比较：

```text
原 TreeHeap
vs
原 TreeHeap + Butterfly
```

这一次我们不从结果倒推故事。先把最小数学合同、长距任务和失败边界都公开，再让 io 上的实验决定这条航线是否值得继续。

> **原创与开放说明：** 本文把 XOR/Butterfly 稀疏通信与 SameTime 的固定容量 TreeHeap 地址、FOLD/UNFOLD 和私有协议问题组合为一条可证伪研究路线。相关 Claim、代码和 evidence 以 GPLv3 在 SameTime/ARA 中公开。Butterfly、Walsh-Hadamard 变换及 XOR 网络本身属于已有数学与计算结构，本文不主张发明这些基础对象。

