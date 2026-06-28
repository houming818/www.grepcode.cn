---
title: "[SPR-026] S1 开始：真实短句上的浅层 TreeHeap 写入"
date: 2026-06-25
weight: 26
author: nio (Houming818) & Codex Review
description: "M0 pilot closed 之后，S1 的第一步不是 WMT，而是真实短句上的 encoder -> soft TreeHeap write -> slot probe。本文记录 shallow_treeheap_s1_probe 的设计、结果和边界。"
tags: [SPR, TreeHeap, ARA, S1, Experiment]
---

# S1 开始：真实短句上的浅层 TreeHeap 写入

前面 `SPR-025` 把 proof 分成两类：

```text
演绎 proof：按定义推出，应该精确成立。
归纳 proof：从数据训练出来，必须看 loss / KL / accuracy / OOD。
```

这一区分很重要。

因为 M0 主要解决的是：

```text
TreeHeap 的数学操作能不能定义？
```

而 S1 要开始解决：

```text
真实数据能不能写进 TreeHeap？
写进去之后，能不能被 kernel / probe 查询？
```

所以这一篇不是继续证明 M0 的闭包。

这一篇是 S1 的第一块砖。

## 为什么不直接上 WMT？

WMT 是翻译任务。

它太大了。

如果一上来跑 WMT，失败时我们不知道问题在哪：

```text
是 encoder 不会写？
是 TreeHeap 不会保存？
是 probe 不会读？
是结构太深？
是 decoder 不会生成？
是 loss 不合适？
```

所以 S1 第一版应该非常浅：

```text
真实短句
↓
浅层 TreeHeap memory
↓
root / subject / object 查询
```

也就是先问一个低级但关键的问题：

```text
模型能不能把真实语言里的短句，写成可查询的数据结构？
```

如果这个都不成立，就没有必要谈 S2 / WMT。

## 实验目标

本次实验脚本：

```text
ara/s1-echo/src/shallow_treeheap_s1_probe.py
```

远端执行在：

```text
ni.grepcode.cn
```

证据目录：

```text
ara/s1-echo/evidence/shallow_treeheap_s1_probe/
```

实验 claim：

```text
S1-C30:
一个可学习的浅层 TreeHeap write，
可以把真实短句编码到 root / subject / object 槽位，
并支持 OOD 新词的 copy-by-address。
```

这里的核心不是“背训练集答案”。

核心是：

```text
输入里出现一个新词，
模型以前没在输出标签里训练过这个词，
TreeHeap 仍然能把它复制到正确槽位。
```

这就是 TreeHeap 作为结构内存的第一种价值。

## 数据是什么？

这次不是随机向量。

数据是人工整理的真实词短句，例如：

```text
alice opens door
bob finds key
carol sees bob
nurse brings water
teacher holds book
```

结构很浅：

```text
subject verb object
```

对应 TreeHeap 槽位：

```text
arr[0] = root
arr[1] = subject
arr[2] = object
```

也就是：

```text
opens
├── alice
└── door
```

注意，这里不是说英语永远是这种结构。

这里只是 S1 的第一步。

我们先让 TreeHeap 学一个深度很浅、结构很清楚的小世界。

## 数据规模

这次数据切分：

| Split | Count |
|---|---:|
| train | 63 |
| test | 17 |
| OOD | 10 |
| vocab | 37 |

OOD 里包含训练输出没见过的新词，例如：

```text
erin draws cup
nurse brings water
frank draws box
teacher holds book
```

这很关键。

如果模型只是普通分类器，它会倾向于输出训练集中见过的词。

但 TreeHeap memory 的写入方式可以是：

```text
把输入 token 复制到某个槽位。
```

所以它有机会处理新词。

## 三个模型

这次对比了三个模型。

### 1. bow_linear

输入是 bag-of-words。

也就是：

```text
alice sees bob
```

和：

```text
bob sees alice
```

在它看来几乎是同一袋词。

它不擅长区分谁是 subject，谁是 object。

### 2. seq_linear

输入保留位置：

```text
position 0 = alice
position 1 = sees
position 2 = bob
```

所以它比 bag-of-words 强。

但是它仍然是普通线性分类器。

如果一个词从来没作为训练输出出现过，它很难突然输出这个词。

### 3. soft_treeheap

这是本次主角。

它学习的是一个 soft write：

```text
position 0 -> 哪个 TreeHeap slot
position 1 -> 哪个 TreeHeap slot
position 2 -> 哪个 TreeHeap slot
```

写入形式可以理解成：

$$ M[s,v] = \sum_p P(s \mid p) \cdot 1[token_p = v] $$

其中：

| 符号 | 含义 |
|---|---|
| \(M\) | TreeHeap memory |
| \(s\) | slot，比如 root / subject / object |
| \(v\) | token |
| \(p\) | 输入位置 |
| \(P(s \mid p)\) | 第 p 个 token 写入 slot s 的概率 |

如果模型学到：

```text
position 0 -> subject
position 1 -> root
position 2 -> object
```

那么：

```text
nurse brings water
```

即使 `nurse`、`brings`、`water` 是新词，也可以被复制到：

```text
subject = nurse
root    = brings
object  = water
```

这就是 copy-by-address。

## 实验结果

结果如下：

| Model | Train exact | Test exact | OOD exact | Test subheap | OOD subheap |
|---|---:|---:|---:|---:|---:|
| bow_linear | 0.873 | 0.765 | 0.000 | 0.765 | 0.000 |
| seq_linear | 1.000 | 0.765 | 0.000 | 0.765 | 0.000 |
| soft_treeheap | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

这里的 `subheap` 指：

```text
root + object
```

例如：

```text
draws cup
brings water
holds book
```

也就是一个很浅的子结构查询。

## TreeHeap 学到了什么？

soft TreeHeap 最后学到的写入概率是：

| 输入位置 | root | subject | object |
|---|---:|---:|---:|
| position 0 | 0.0016 | 0.9968 | 0.0016 |
| position 1 | 0.9968 | 0.0016 | 0.0016 |
| position 2 | 0.0016 | 0.0016 | 0.9968 |

换句话说，它学到：

```text
position 0 -> subject
position 1 -> root
position 2 -> object
```

这是一个非常简单的浅层结构。

但这就是 S1 的意义：

```text
不是先证明复杂语言。
而是先证明数据可以写入 TreeHeap，并且能被查询。
```

## 为什么普通 seq_linear OOD 失败？

`seq_linear` 在训练集上是 1.0。

说明它能背住训练词和位置关系。

但是 OOD 是 0.0。

原因很简单：

```text
它没有 copy 机制。
```

比如：

```text
nurse brings water
```

如果 `nurse` 和 `water` 没在训练输出里出现过，普通分类器没有学过：

```text
输出 nurse
输出 water
```

它只能偏向训练里见过的词。

TreeHeap 的 soft write 不同。

它不需要先学会每个词的输出权重。

它只需要学会：

```text
第 0 个 token 写到 subject。
第 1 个 token 写到 root。
第 2 个 token 写到 object。
```

然后直接复制输入 token。

这就是结构内存和普通分类器的差异。

## 这证明了什么？

这次支持：

```text
S1-C30 -> supported pilot
```

也就是：

```text
浅层 TreeHeap write 可以在真实短句上形成可查询 memory。
```

它还说明：

```text
TreeHeap 的地址/槽位机制，
确实可以提供一种普通输出分类器没有的 OOD copy 能力。
```

这和我们之前讨论的方向是一致的：

```text
TreeHeap 不只是一个 MLP。
TreeHeap 的参数可以很少，
但 memory 的地址、路径、slot、子结构本身参与了计算。
```

## 这没有证明什么？

边界必须说清楚。

这次没有证明：

```text
TreeHeap 能翻译。
TreeHeap 能处理完整句法。
TreeHeap 比 Transformer 强。
TreeHeap 能处理长句。
TreeHeap 已经解决 S2 graph assembly。
```

这次数据也很浅。

它更像是：

```text
S1 的 hello world。
```

但它不是没意义。

因为它第一次把 M0 的数学工具箱接到了真实短句数据上。

## 下一步怎么改？

下一步不能继续只做固定 SVO。

否则 TreeHeap 学到的只是：

```text
位置模板。
```

下一轮应该加入：

```text
可变长度
修饰语
被动句
OSV / 倒装
中文短句
多 root 候选
matched pointer/copy baseline
```

新的 predict 可以是：

```text
P-S1-REAL-SHALLOW-02:
当句子顺序不再固定时，
TreeHeap kernel 必须利用 token 内容、路径、slot 和局部子结构，
而不是只利用 position。
```

如果下一轮 TreeHeap 仍然能稳住，而普通 baseline 不行，
那 S1 才开始从：

```text
存在性 proof
```

进入：

```text
结构优势 proof
```

## 总结

这次实验的结论很简单：

```text
M0 可以进入 S1。
S1 的第一版真实短句浅层写入成立。
```

TreeHeap 学到的不是语言全貌。

它学到的是一件很小但关键的事：

```text
如何把真实句子的 token 写入可查询的结构槽位。
```

这就是下一步工作的地基。

现在我们可以继续往上加难度了。
