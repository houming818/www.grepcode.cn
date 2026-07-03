---
title: "[SPR-044] S1-WMT canonical echo：从随机修复，改成最低熵中间态"
date: 2026-07-03
weight: 44
author: nio (Houming818) & Codex Review
description: "SPR-044 proof：在 50,000 对 WMT17 英中平行句上，训练 TreeHeap canonical state，让英中表面形式靠近，同时仍能 echo 回各自原句。"
tags: [SPR, TreeHeap, ARA, S1, WMT, Canonical, Echo]
---

# S1-WMT canonical echo：从随机修复，改成最低熵中间态

上一篇 SPR-043 做的是：

```text
给一句真实英文句子
用 TreeHeap 自己的 Flip 算子扰动
再学 inverse route 还原
```

这个实验有用，但 Houming818 指出一个根本问题：

```text
语言不是随机坏掉的句子。
上游是世界模型，下游是意识空间。
语言只是中间表达。
```

所以 S1-echo 的目标不应该是：

```text
random perturbation -> repair
```

而应该是：

```text
surface sentence
-> canonical TreeHeap state
-> surface sentence
```

这里的 `canonical TreeHeap state` 可以先粗略理解为：

```text
同一个意义的多种语言表面形式，
在 TreeHeap 空间里被压到更近、更低熵的中间状态。
```

然后 echo 的作用是检查：

```text
压到中间态以后，信息有没有丢光？
还能不能回读原来的表面句子？
```

这才是能接 S2 翻译的 S1。

## 这次的 claim

ARA claim：

```text
S1-CANON-WMT-C01
```

说人话：

```text
给 WMT 英中平行句：

EN sentence -> H_en
ZH sentence -> H_zh

如果 EN 和 ZH 是同一个平行句对，
H_en 和 H_zh 应该比随机错配句更近。

同时，
H_en 还要能 echo 回英文，
H_zh 还要能 echo 回中文。
```

这不是 BLEU。
这也不是完整翻译。

它只证明 S1 有没有开始形成一个：

```text
可对齐
可回读
不完全坍缩
的 bilingual canonical state
```

## 为什么需要 BoW baseline

这个实验不能只看 TreeHeap 自己。

因为 WMT 平行语料里有很多词面共现信号：

```text
数字
专名
标点
主题词
领域词
```

简单 bag-of-words 也可能很强。

所以这次同时训练两个模型：

```text
TreeHeapCanonical
BoWCanonical
```

它们用同一个任务：

```text
1. 拉近平行句对
2. 拉远错配句对
3. echo 回各自原句 token
```

如果 TreeHeap 没赢 BoW，那结论必须降级。

## TreeHeap 模型在做什么

TreeHeapCanonical 的结构是：

```text
token embedding
-> path/address embedding
-> balanced binary TreeHeap compose kernel
-> root canonical state
```

同时保留 leaf state 做 echo：

```text
leaf state -> token decoder -> 原语言 token
```

所以它有两个层面：

```text
root:  尝试表示跨语言 canonical state
leaf:  保留原句可回读信息
```

这点很重要。

如果只有 root，而 root 又要完整还原整句，第一版会很难。
如果只看 leaf echo，又会退化成复制 token。

所以这次先把问题拆开：

```text
root 负责 canonical alignment
leaf 负责 echo preservation
```

后续更严格的版本，要继续压缩 leaf memory，让更多信息进入 root / subheap state。

## Loss 怎么设计

这次不是一个大锅 loss。
脚本分别记录：

```text
L_align_en_to_zh
L_align_zh_to_en
L_echo_en
L_echo_zh
L_variance
```

核心 alignment 是 batch 内对比学习：

```text
score(i, j) = cosine(H_en_i, H_zh_j) / temperature
target(i) = i
```

也就是：

```text
第 i 个英文句子
应该找回第 i 个中文句子
而不是 batch 里的其他中文句子
```

这和翻译不同。
它更像在问：

```text
你能不能把同一个意义的两种语言形式放近？
```

另外加了一个 anti-collapse 的 variance loss。
因为“低熵”不能理解成：

```text
所有句子都坍缩到同一个点
```

那是没信息，不是 canonical。

我们要的是：

```text
等价表达更近；
不同意义仍然可分。
```

## 实验设置

运行位置：

```text
io.grepcode.cn
```

证据目录：

```text
ara/s1-echo/evidence/s1_wmt_canonical_echo_probe/
```

数据：

```text
WMT17 train.zh-en
50,000 sentence pairs
train/test/OOD = 40,000 / 5,000 / 5,000
max_len = 48
en_vocab = 8192
zh_vocab = 6805
dim = 128
epochs = 5
```

注意：

```text
OOD 不是新领域语料。
它是 held-out parallel pairs。
```

所以这个结果还是 S1 pilot，不是最终泛化证明。

## 结果

OOD 指标如下：

| model | pos distance | neg distance | margin | retrieval@1 | retrieval@5 | entropy |
|---|---:|---:|---:|---:|---:|---:|
| untrained TreeHeap | 0.8148 | 0.8178 | 0.0030 | 0.0010 | 0.0025 | 6.9731 |
| BoW | 0.4028 | 0.9968 | 0.5939 | 0.6285 | 0.8085 | 4.3442 |
| TreeHeap | 0.3458 | 0.9929 | 0.6472 | 0.6300 | 0.8195 | 4.0443 |

Echo 指标：

| model | EN echo token | ZH echo token | EN exact | ZH exact |
|---|---:|---:|---:|---:|
| TreeHeap | 1.0000 | 0.9981 | 1.0000 | 0.9610 |
| BoW | 1.0000 | 0.9985 | 1.0000 | 0.9690 |

先看最重要的部分：

```text
TreeHeap positive distance = 0.3458
TreeHeap negative distance = 0.9929
```

这说明 true parallel pair 的 canonical state 明显更近。

再看 retrieval：

```text
random retrieval@1 = 0.0005
TreeHeap retrieval@1 = 0.6300
TreeHeap retrieval@5 = 0.8195
```

也就是说，在 2000 个候选中文句子里，给一个英文 root state：

```text
63% 的时候，最近的中文 state 就是正确平行句；
81.95% 的时候，正确句在前 5 名。
```

这已经不是随机信号。

## TreeHeap 赢了吗？

要小心。

TreeHeap 没有“大胜” BoW。

BoW 的结果也很强：

```text
BoW retrieval@1 = 0.6285
TreeHeap retrieval@1 = 0.6300
```

差距很小。

TreeHeap 更明显的优势在：

```text
margin:
  TreeHeap = 0.6472
  BoW      = 0.5939

entropy:
  TreeHeap = 4.0443
  BoW      = 4.3442
```

这说明：

```text
TreeHeap 把正负样本拉得更开；
TreeHeap 的匹配分布更尖锐一些。
```

但这还不能说：

```text
TreeHeap 已经全面优于 BoW。
```

更诚实的结论是：

```text
WMT canonical echo 任务成立；
TreeHeap 在第一版里有小幅结构优势；
但 BoW baseline 很强，下一步必须加更强 sequence / Transformer baseline。
```

## 可读样例

证据目录里保存了样例。
例如一个成功样例：

```text
EN:
The tradable sector is expanding and is not dependent on leverage to generate aggregate demand.

ZH:
可贸易部门正在扩张，不需要依赖杠杆就能提振总需求。

TreeHeap paired cosine:
0.5795

top1:
true

EN echo:
the tradable sector is expanding and is not dependent on leverage to generate aggregate demand.
```

也有失败样例。
例如：

```text
EN:
As in Nigeria, vaccination delays will be highly detrimental for neighboring countries.

top1:
false
```

这说明模型已经能做很多 pair retrieval，但不是满分。
失败通常出现在：

```text
短句
领域词
低频词
专名
语料编码噪声
```

## 这证明了什么

SPR-044 支持：

```text
WMT 平行语料中，
不同语言表面形式可以被训练到一个更接近的 canonical state。

这个 state 不是纯坍缩，
因为它还能区分不同句子，
并且能支持同语言 echo。
```

更短一点：

```text
S1 可以从“复制句子”推进到“平行语义形式的中间态对齐”。
```

## 还没有证明什么

这次没有证明：

```text
WMT 翻译 BLEU
真正语义理解
世界模型 grounding
意识空间
无监督发现语言规律
TreeHeap 全面优于 Transformer
```

尤其要注意：

```text
这个实验用了平行语料监督。
```

所以它不是无监督语义发现。

它证明的是：

```text
在 WMT 平行监督下，
TreeHeap 可以学习一个可回读的 bilingual canonical state。
```

这已经比随机 flip 更接近 S2，但还不是 S2。

## 下一步

我认为下一步有三个门：

```text
1. 加 sequence / small Transformer baseline
2. 扩大 retrieval candidate pool，不只 2000
3. 把 root canonical state 和 leaf echo memory 分得更清楚
```

第三点最关键。

因为现在：

```text
root 负责对齐；
leaf 负责 echo。
```

后续要逐步提高要求：

```text
subheap state 也必须有可解释的 canonical 信息；
不能只让 leaf 偷偷保存所有表面 token。
```

这才会把 S1 推向真正的 S2：

```text
source surface
-> canonical TreeHeap state
-> target surface
```

> ARA: [S1 WMT canonical echo](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/s1_wmt_canonical_echo.md) / [evidence](https://github.com/houming818/sametime/tree/main/ara/s1-echo/evidence/s1_wmt_canonical_echo_probe) / [claims](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/claims.md)
