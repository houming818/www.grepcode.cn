---
title: "[SPR-018] TreeHeap 的存在性：编码结构与共轭 Kernel"
date: 2026-06-22
weight: 18
author: nio (Houming818) & Codex Review
description: "修正 TreeHeap 的核心 claim：不是简单 pattern matching，而是学习可搜索、可压缩的编码结构，并用共轭 kernel 完成查询和解码。"
tags: [SPR, TreeHeap, InductiveBias, Experiment, Architecture]
---

# TreeHeap 的存在性：编码结构与共轭 Kernel

这篇文章修正一个重要问题。

上一版 `SPR-018` 把重点放在了 `subheap kernel relocation`：

```text
给定一个人工 pattern，
看 TreeHeap kernel 能不能在新地址找到它。
```

这个实验有用，但太弱。

它只能说明：

```text
显式 subheap kernel 可以做局部模式检测。
```

它不能证明我们真正关心的东西：

```text
TreeHeap 能不能自己把输入数据 encode 成一种可搜索、可压缩的结构？
查询 kernel / 解码 kernel 能不能沿着这个结构工作？
encoder 和 decoder 是否形成一对共轭过程？
```

所以现在的 claim 要重新写清楚。

## 现在真正的 Claim

TreeHeap 不是要证明自己是“完全不同”的东西。

它应该先证明自己和实数域、MLP、CNN、Transformer 一样，能用于构造预测函数：

```text
输入 x
参数 theta
预测 y_hat = f_theta(x)
loss(y_hat, y)
gradient
update theta
```

然后再证明：

```text
在需要结构编码、路径搜索、前缀压缩、延迟坍缩的问题上，
TreeHeap 的显式结构归纳偏置能带来更好的样本效率、外推稳定性或计算效率。
```

更具体地说，我们现在要证明的不是：

```text
TreeHeap 会匹配一个 pattern。
```

而是：

```text
TreeHeap encoder 能把数据组织成一种结构；
TreeHeap decoder/query kernel 能利用这个结构完成搜索或解码。
```

这就是：

```text
learned encoder + conjugate kernel
```

中文可以叫：

```text
学习到的编码器 + 共轭查询/解码核
```

## 为什么旧 B 实验不够

旧 B 实验是这样的：

```text
pattern:
      1
     / \
    2   3
```

训练时 pattern 出现在：

```text
positions = {0, 1, 2}
```

测试时 pattern 出现在：

```text
positions = {6, 10, 13}
```

结果：

| method | accuracy mean | min | max |
|---|---:|---:|---:|
| TreeHeap kernel | 1.0000 | 1.0000 | 1.0000 |
| flatten MLP | 0.4996 | 0.4258 | 0.5703 |
| sequence CNN | 1.0000 | 1.0000 | 1.0000 |
| small Transformer | 0.9846 | 0.6055 | 1.0000 |

这个表说明：

```text
局部 kernel 迁移是有效归纳偏置；
MLP 展平后不擅长；
CNN 和 TreeHeap kernel 擅长；
Transformer 大多能学到，但有失败尾部。
```

但它不说明：

```text
TreeHeap 能学习建堆。
TreeHeap 能学习编码。
TreeHeap 能执行查询路径。
TreeHeap 能压缩数据。
```

所以旧 B 只能作为 smoke test。

它证明的是：

```text
kernel 这个方向值得继续。
```

而不是最终 proof。

## 新实验方向一：学习建堆 + 查询搜索

第一个真正应该做的实验是：

```text
learned ordered TreeHeap search
```

也就是：

```text
输入一组 key/value
encoder 把它们建成 TreeHeap
query kernel 根据查询 key 在树上走 stop / left / right
最后返回 value
```

注意关键点：

```text
树不是人工提前建好的。
树应该由 encoder 学出来。
```

### Toy 数据

给一批 key/value：

```text
[(8, A), (4, B), (12, C), (2, D), (6, E), (10, F), (14, G)]
```

查询：

```text
query = 6
answer = E
```

如果 TreeHeap encoder 学到了类似有序树的结构，它可能形成：

```text
          8:A
         /   \
      4:B     12:C
     /  \     /   \
  2:D   6:E 10:F 14:G
```

这个结构不是我们强行塞给模型的目标，而是它为了让查询 kernel 更容易工作，应该自己学出来的中间结构。

### 查询 Kernel

查询 kernel 可以很简单：

```text
query_kernel(node, query):
  if query == node.key:
    return stop
  if query < node.key:
    return left
  if query > node.key:
    return right
```

查找 `query = 6` 的过程：

```text
step 1:
  node = 8:A
  6 < 8
  action = left

step 2:
  node = 4:B
  6 > 4
  action = right

step 3:
  node = 6:E
  6 == 6
  action = stop
  output = E
```

路径：

```text
root -> left -> right -> stop
```

地址：

```text
0 -> 1 -> 4
```

这就是一个查找算法。

但在 TreeHeap 视角下，它可以被看成：

```text
subheap
-> query kernel
-> next address
-> subheap
-> query kernel
-> ...
```

也就是一个局部 kernel 的迭代。

### 这里的共轭关系

encoder 和 query kernel 必须配合。

如果 encoder 学出的结构是乱的：

```text
          10:F
         /    \
      2:D      6:E
```

那么简单的 `query < root -> left` 就可能走错。

所以训练压力会迫使 encoder 学一种结构，使得 decoder/query kernel 能工作。

这就是共轭关系：

```text
encoder 学会如何摆放节点；
query kernel 学会如何沿结构读取。
```

一个好的 proof 应该观察：

```text
查询准确率是否上升；
路径长度是否接近 log n；
树结构是否接近有序树；
OOD key 数量变大时是否还能泛化。
```

### Predict B-new

```text
如果 TreeHeap 的结构归纳偏置成立，
TreeHeap encoder 会学习出一种可被局部 query kernel 搜索的结构。

相比 flatten MLP，
它应该更省样本、更容易外推到更多 key。

相比普通 Transformer，
它应该在路径长度、计算量、失败尾部上更稳定。
```

这才是搜索能力的 proof。

## 新实验方向二：加权前缀树 + Huffman-like 解码

第二个方向是你提到的加权树。

这里最接近的经典对象是 Huffman coding。

Huffman 编码做的事是：

```text
高频符号用短路径；
低频符号用长路径；
整棵树是 prefix-free 的；
decoder 沿路径还原符号。
```

TreeHeap 里可以问一个类似问题：

```text
encoder 能不能学习一棵加权前缀树？
decoder kernel 能不能沿路径把符号还原？
```

### Toy 数据

假设符号频率是：

```text
A: 0.50
B: 0.25
C: 0.15
D: 0.10
```

一个理想的 Huffman-like 编码可能是：

```text
A -> 0
B -> 10
C -> 110
D -> 111
```

对应树：

```text
root
├── 0: A
└── 1
    ├── 0: B
    └── 1
        ├── 0: C
        └── 1: D
```

平均路径长度：

```text
E[length]
= 0.50 * 1
+ 0.25 * 2
+ 0.15 * 3
+ 0.10 * 3
= 1.75
```

如果不用加权前缀树，而给每个符号固定 2 bit：

```text
A -> 00
B -> 01
C -> 10
D -> 11
```

平均长度：

```text
E[length] = 2.00
```

这个 toy 里 Huffman-like 树更短。

### Encoder / Decoder

TreeHeap encoder 的任务：

```text
输入符号分布
输出一棵前缀 TreeHeap
```

TreeHeap decoder 的任务：

```text
输入路径 bits
沿 TreeHeap 走 left/right
遇到 leaf 后输出符号
```

例如路径：

```text
110
```

解码：

```text
root -> right -> right -> left
output = C
```

这和前面的搜索任务一样，也是 kernel 迭代：

```text
current node + next bit -> next node
```

但这里的目标不是搜索 key，而是还原压缩编码。

### 这里的共轭关系

encoder 和 decoder 也是共轭的：

```text
encoder 决定符号放在哪条路径；
decoder 沿路径还原符号。
```

如果 encoder 把高频符号放得很深，平均路径长度就会变差。

如果 encoder 生成的树不是 prefix-free，decoder 会混淆。

所以训练目标可以是：

```text
reconstruction loss
+ expected path length penalty
+ prefix-free constraint penalty
```

### Predict C-new

```text
如果 TreeHeap 的加权路径结构成立，
encoder 应该能学习一棵接近 Huffman oracle 的前缀树；
decoder kernel 应该能沿路径稳定还原符号；
平均路径长度应该低于固定长度编码 baseline。
```

这才是“路径前缀压缩”的 proof。

不是简单地数 toy trie 节点。

## 这两个实验和机器学习的关系

这两个实验不是手写算法炫技。

真正的目标是：

```text
让 encoder 的结构由梯度学习出来。
```

也就是：

```text
输入数据
-> TreeHeap encoder(theta)
-> 结构状态 H
-> query/decoder kernel(phi)
-> 输出
-> loss
-> gradient update theta, phi
```

这和 MLP / Transformer 一样，仍然是机器学习。

区别只是：

```text
MLP 学的是展平向量上的函数；
Transformer 学的是 token 序列上的 attention 函数；
TreeHeap 学的是结构编码 + 路径 kernel。
```

所以 TreeHeap 的存在性不是“完全不同”。

而是：

```text
同样做预测函数学习，
但结构归纳偏置不同。
```

## 旧 B 表应该怎么使用

旧 B 表还可以保留，但只能作为弱证据。

它说明：

```text
显式 kernel 在局部结构迁移任务上是有用的；
这个方向不是空想。
```

但下一轮 proof 应该升级为：

```text
B-new:
  learned encoder builds searchable ordered tree
  query kernel walks stop/left/right

C-new:
  learned encoder builds weighted prefix tree
  decoder kernel reconstructs symbols from paths
```

我们之后要聊的 predict 和 proof，就应该围绕这两个实验设计。

## 当前总 Claim

最终 claim 可以写成：

```text
TreeHeap 是一种和 MLP / CNN / Transformer 同属机器学习家族的计算结构。

它的独特性不是“完全不同”，
而是把结构编码、路径搜索、前缀压缩、概率坍缩显式化。

如果 claim 成立，
TreeHeap encoder 应该能学习可搜索/可压缩的结构；
共轭 query/decoder kernel 应该能利用该结构完成搜索和解码；
并在相应结构任务上获得更好的样本效率、外推稳定性或计算效率。
```

下一步不是继续做 pattern matching。

下一步是 proof：

```text
能不能 learn to build the tree?
能不能 learn to search/decode through the tree?
能不能比 MLP / Transformer 更省样本、更稳？
```

这才是 TreeHeap 的存在性问题。

> **License: GPLv3**
