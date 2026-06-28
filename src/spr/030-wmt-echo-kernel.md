---
title: "[SPR-030] 用 WMT 真语料做 Echo：先证明 TreeHeap Kernel 能写入真实 BPE 序列"
date: 2026-06-25
weight: 30
author: nio (Houming818) & Codex Review
description: "这次不直接做翻译，而是用 WMT 真语料做短序列 echo，验证 TreeHeap kernel 是否能把真实 SentencePiece token 写入树堆地址，再稳定读出。"
tags: [SPR, TreeHeap, ARA, S1, WMT, Kernel, Echo]
---

# 用 WMT 真语料做 Echo：先证明 TreeHeap Kernel 能写入真实 BPE 序列

这次我们回到 Houming818 一直强调的问题：

```text
TreeHeap 怎么把真实数据写进自己的高维结构？
```

如果连真实语料的 token 序列都不能稳定写入、读出，那么后面谈翻译、世界模型、概率坍缩都太早。

所以 `SPR-030` 不直接做 WMT 翻译。
它先做一个更低一级、但更必要的实验：

```text
WMT 真语料
-> SentencePiece BPE token
-> TreeHeap kernel 写入
-> TreeHeap kernel 读出
-> 和原 token 序列比较
```

这叫 echo 实验。

它不是翻译。
它测试的是：

```text
TreeHeap kernel 是否能处理真实语料的离散 token 序列。
```

## 为什么不是马上做翻译？

翻译任务太复杂。

一句英文到一句中文，中间至少包含：

```text
词义
语序
短语结构
跨语言对齐
生成概率
目标语言流畅性
```

如果直接上 WMT BLEU，结果不好时我们不知道问题在哪里。

可能是 encoder 不行。
可能是 decoder 不行。
可能是 kernel 不行。
可能是 loss 不行。
也可能只是训练规模太小。

所以这次先拆开：

```text
第一步：真实 token 能不能写入 TreeHeap？
第二步：写入后能不能读出来？
第三步：结构化 kernel 是否比普通 flat 模型更适合这个问题？
```

这就是 S1 echo 的意义。

## 数据来自哪里？

实验使用 io 上的 WMT17 数据：

```text
source file:
/mnt/nas/datasets/wmt17/train.zh-en

SentencePiece model:
/mnt/nas/datasets/wmt17/sp_bpe.model
```

我们取英文侧文本，然后用 SentencePiece 切成 BPE token。

实验只取短序列：

```text
token length = 3..8
samples = 3000
train/test/ood = 2400/300/300
vocab limit including PAD = 2048
average non-pad length = 5.9533
```

为什么先限制长度？

因为这次不是要证明长文本翻译。
这次要先验证最小写入机制：

```text
一个真实 BPE 序列，能不能被 TreeHeap 地址结构保存。
```

## Echo 任务具体是什么？

输入是一段 BPE token：

```text
[t1, t2, t3, ...]
```

目标输出还是它自己：

```text
[t1, t2, t3, ...]
```

这看起来很简单，但它能测出一个关键点：

```text
模型是否保存了 token 的位置、顺序、地址。
```

如果模型只是知道句子里有哪些 token，但不知道顺序，就会失败。

例如：

```text
[A, B, C]
```

和：

```text
[C, B, A]
```

bag-of-words 看起来差不多，但 echo 必须区分它们。

所以 echo 不是语义任务，却是结构写入任务。

## 三个模型对比

这次比较三个模型。

| Model | 含义 |
|---|---|
| `bow_linear` | 只看 token 集合，不看顺序 |
| `seq_mlp` | 把固定位置拼平，交给普通 MLP |
| `treeheap_kernel_echo` | 把 token 写到 TreeHeap 叶子地址，再用共享 kernel 自底向上 compose |

### 1. bow_linear

`bow_linear` 看到的是：

```text
这个句子里出现过哪些 token
```

它不知道 token 在第几个位置。

所以它适合作为反例 baseline：

```text
如果 BoW 也能做好 echo，那说明任务太简单。
```

### 2. seq_mlp

`seq_mlp` 是普通 flat MLP。

它看到的是固定位置展开后的向量：

```text
position 1 token
position 2 token
position 3 token
...
```

它有顺序信息。
但它没有显式树地址、子结构、compose kernel。

可以理解为：

```text
把序列压平成一张大表，然后学习 input -> output。
```

### 3. treeheap_kernel_echo

TreeHeap 模型做的是：

```text
token id -> shared token embedding
position -> fixed heap leaf address
internal nodes -> shared bottom-up compose kernel
leaf readout -> shared decoder
```

换成人话：

```text
每个 token 先写到树堆的一个叶子地址上。
然后树里的父节点用同一个 compose kernel 汇总左右孩子。
最后从叶子状态读回 token。
```

关键点是：

```text
模型必须利用 TreeHeap 的地址结构。
```

它不是把整个句子拼成一个大向量随便读。
它被迫经过：

```text
叶子地址
子结构
自底向上 compose
共享 decoder
```

这就是 kernel 设计的意义。

## 实验结果

脚本：

```text
ara/s1-echo/src/s1_wmt_echo_kernel_probe.py
```

证据：

```text
ara/s1-echo/evidence/s1_wmt_echo_kernel_probe/
```

执行主机：

```text
io.grepcode.cn
```

结果如下：

| Model | Params | Test token | Test exact | OOD token | OOD exact |
|---|---:|---:|---:|---:|---:|
| `bow_linear` | 33,570,816 | 0.1679 | 0.0033 | 0.1659 | 0.0033 |
| `seq_mlp` | 16,794,112 | 0.5801 | 0.0567 | 0.5986 | 0.0533 |
| `treeheap_kernel_echo` | 423,104 | 0.9818 | 0.8900 | 0.9818 | 0.9000 |

这里有两个指标：

```text
token accuracy:
  每个位置的 token 是否预测正确。

exact:
  整个序列是否完全预测正确。
```

exact 更严格。
只要一个位置错了，整个序列就算错。

## 结果说明什么？

第一，BoW 几乎失败。

```text
OOD exact = 0.0033
```

这说明任务不是只靠 token 集合就能完成。
顺序和地址确实重要。

第二，flat MLP 训练集可以学会，但 OOD 很差。

```text
seq_mlp OOD exact = 0.0533
```

它有 16,794,112 个参数，比 TreeHeap 多很多。
但它在新样本上不能稳定复制完整序列。

第三，TreeHeap kernel 表现明显更好。

```text
treeheap_kernel_echo OOD token = 0.9818
treeheap_kernel_echo OOD exact = 0.9000
```

而且参数更少：

```text
TreeHeap params = 423,104
seq_mlp params  = 16,794,112
```

大约是：

```text
TreeHeap 参数量约为 seq_mlp 的 2.5%
```

这支持一个小 claim：

```text
在真实 WMT 短 BPE echo 任务上，
TreeHeap kernel 可以更有效地利用地址和路径结构。
```

## 这和 kernel 设计有什么关系？

前面我们反复讨论：

```text
TreeHeap 的核心操作不是普通矩阵拼接，
而是 kernel 在树结构上的卷积。
```

这次实验里的 kernel 很朴素：

```text
leaf write kernel:
  把 token embedding 写到固定叶子地址。

compose kernel:
  对每个内部节点，用同一个函数合并 left/right child。

read kernel:
  从叶子状态预测原 token。
```

它像一维 CNN 里的卷积核，但滑动对象不是平面像素，而是 TreeHeap 子结构。

CNN 的 3x3 kernel 看局部像素。
TreeHeap kernel 看局部树堆：

```text
parent
├── left child
└── right child
```

所以它天然带着：

```text
地址
路径
子结构
组合
分解
```

这些信息。

这正是 flat MLP 没有显式拥有的归纳偏置。

## 这次 claim 是什么？

ARA 里记录为：

```text
S1-WMT-ECHO-C01
```

claim：

```text
A structured TreeHeap kernel can write and read real WMT SentencePiece short
sequences in an echo setting, using tree addresses and shared compose/read
kernels rather than only a flat memorization map.
```

状态：

```text
supported pilot
```

用中文说：

```text
结构化 TreeHeap kernel 能在真实 WMT 短 BPE 序列上完成写入和读出。
这个结果支持 TreeHeap 的地址/路径结构是有用的。
```

## 这没有证明什么？

边界要说清楚。

这次没有证明：

```text
TreeHeap 已经会翻译。
TreeHeap 已经有语义世界模型。
TreeHeap 已经能压缩长文本。
TreeHeap 已经解决长距离句法。
TreeHeap 已经击败 Transformer。
```

它只证明一件更基础的事：

```text
真实 WMT token 可以被 TreeHeap kernel 稳定写入和读出。
```

这对 S1 是有意义的。
但离 S2/S3 还有距离。

## 下一步怎么做？

下一步不是立刻喊胜利。
应该继续加难度。

### 1. 更长序列

现在是：

```text
length = 3..8
```

下一步要测：

```text
length = 8..16
length = 16..32
```

如果长度一长就崩，说明 TreeHeap kernel 还只是短序列技巧。

### 2. 噪声 echo

普通 echo 是原样复制。

下一步可以做：

```text
mask 一个 token，让模型恢复。
drop 一个 token，让模型恢复。
swap 两个 token，让模型判断并修正。
```

这开始接近推理。

因为模型不能只照抄，它必须利用上下文。

### 3. subheap query

不要总是读整个句子。
可以问：

```text
读左子树。
读右子树。
读某个短语窗口。
读某条路径下的 token。
```

这能测试 TreeHeap 的子结构是否真的可查询。

### 4. 更公平的 baseline

这次的 `seq_mlp` 不是最强序列模型。

下一步要加：

```text
pointer/copy baseline
small Transformer
tiny RNN/GRU
matched parameter sequence model
```

如果这些模型在相同参数和数据预算下追上 TreeHeap，那么 claim 要收缩。

## 总结

`SPR-030` 的结论是：

```text
可以用 WMT 真语料做 echo。
TreeHeap kernel 在短 BPE 序列写入/读出上表现很好。
它用更少参数，明显超过 BoW 和 flat seq MLP。
```

这说明：

```text
kernel 设计是关键。
```

TreeHeap 的存在性不能只靠抽象代数。
它必须在具体任务上显示：

```text
地址有用。
路径有用。
子结构有用。
组合/分解有用。
```

这次只是第一块真实语料证据。
下一步要从：

```text
短序列 echo
```

推进到：

```text
长序列 echo
噪声恢复
subheap query
copy/pointer baseline battle
```

如果这些也成立，S1 才能更稳地往 S2 翻译折叠推进。
