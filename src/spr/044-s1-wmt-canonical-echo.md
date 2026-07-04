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

## 指标体检报告：这些数字到底怎么看

这次的指标有点多。
如果只看一两个数字，很容易误判。

可以把它当成体检报告来看：

```text
不是每个指标都是越大越好。
有些是越小越好。
有些要看 TreeHeap 和 BoW 的差距。
有些只说明任务成立，不说明 TreeHeap 有结构优势。
```

### positive distance

含义：

```text
d(H_en, H_zh)
```

也就是一对真实平行句的 canonical state 距离。

健康趋势：

```text
越小越好。
```

因为英文和中文如果表达同一个意义，它们的中间态应该更近。

这次结果：

```text
TreeHeap = 0.3458
BoW      = 0.4028
```

读数：

```text
TreeHeap 更好。
```

但这个指标不能单独看。
如果所有句子都坍缩到同一个点，positive distance 也会很小。
所以必须同时看 negative distance 和 retrieval。

### negative distance

含义：

```text
d(H_en, H_zh_wrong)
```

也就是英文句子和错配中文句子的距离。

健康趋势：

```text
越大越好。
```

不同意义的句子应该离远一点。

这次结果：

```text
TreeHeap = 0.9929
BoW      = 0.9968
```

读数：

```text
两者都健康，BoW 略高。
```

但 negative distance 高不一定代表整体更好，还要看 positive 是否也低。

### margin

含义：

```text
margin = negative_distance - positive_distance
```

这是最像“血压差”的指标。
它衡量模型能不能把：

```text
真平行句拉近
错配句推远
```

健康趋势：

```text
越大越好。
```

这次结果：

```text
Untrained TreeHeap = 0.0030
BoW                = 0.5939
TreeHeap           = 0.6472
```

读数：

```text
训练确实产生了强信号。
TreeHeap 比 BoW 高 0.0533。
```

这个是 TreeHeap 本次最主要的正向证据。

但注意：

```text
0.6472 vs 0.5939
```

不是碾压。
只能叫 small advantage。

### retrieval@1

含义：

```text
给一个英文 H_en，
在 2000 个中文候选 H_zh 里找最近的，
最近那个是不是正确平行句？
```

健康趋势：

```text
越大越好。
```

这次结果：

```text
random   = 0.0005
BoW      = 0.6285
TreeHeap = 0.6300
```

读数：

```text
任务成立。
TreeHeap 和 BoW 几乎持平。
```

这也是 DS 说“弱”的原因。
如果只看 retrieval@1，TreeHeap 不能说有结构性优势。

### retrieval@5

含义：

```text
正确中文句是否在最近的前 5 个候选里？
```

健康趋势：

```text
越大越好。
```

这次结果：

```text
BoW      = 0.8085
TreeHeap = 0.8195
```

读数：

```text
TreeHeap 略好。
```

但还是小优势。

### entropy

entropy 就是熵。

这里它衡量的是：

```text
模型在 2000 个中文候选里选择匹配对象时，
分布有多不确定。
```

如果分布很平：

```text
每个候选都差不多像
```

熵就高。

如果分布更尖：

```text
少数候选明显更像
```

熵就低。

健康趋势：

```text
在不坍缩的前提下，越小越好。
```

为什么要加“在不坍缩的前提下”？

因为如果模型胡乱把所有概率压到一个错误候选，熵也会低。
所以 entropy 必须和 retrieval、margin 一起看。

这次结果：

```text
Untrained TreeHeap = 6.9731
BoW                = 4.3442
TreeHeap           = 4.0443
```

读数：

```text
TreeHeap 的匹配分布更尖锐。
这是正向信号。
```

但它不是单独的胜利指标。
如果 retrieval 没提升，低熵可能只是更自信地错。

### echo token

含义：

```text
canonical/leaf state 能不能把原句 token 读回来？
```

健康趋势：

```text
越大越好。
```

这次结果：

```text
TreeHeap EN/ZH = 1.0000 / 0.9981
BoW EN/ZH      = 1.0000 / 0.9985
```

读数：

```text
echo 基本没崩。
但这不是 TreeHeap 优势。
```

因为 BoW 也能 echo 得很好。

### 体检总评

如果把这些指标合在一起：

| 指标 | 健康趋势 | TreeHeap 本次读数 | 结论 |
|---|---|---:|---|
| positive distance | 越小越好 | 0.3458 | 好于 BoW |
| negative distance | 越大越好 | 0.9929 | 健康，略低于 BoW |
| margin | 越大越好 | 0.6472 | 好于 BoW，主要正证据 |
| retrieval@1 | 越大越好 | 0.6300 | 与 BoW 几乎持平 |
| retrieval@5 | 越大越好 | 0.8195 | 略好于 BoW |
| entropy | 不坍缩前提下越小越好 | 4.0443 | 好于 BoW |
| echo token | 越大越好 | 1.0000 / 0.9981 | 健康，但 BoW 也健康 |

所以结论不能写成：

```text
TreeHeap 已经证明 canonicalization 有结构性优势。
```

更准确是：

```text
WMT canonical echo 任务成立。
TreeHeap 有 signal。
TreeHeap 在 margin 和 entropy 上优于 BoW。
但 retrieval@1 几乎持平，所以只能叫 weak positive / small advantage。
```

DS 的审计意见是合理的。

### 如果“最佳结果就是持平”，怎么办

有一种可能：

```text
在当前数据切分和当前模型容量下，
BoW 已经吃掉了大部分可用信号。
```

这不奇怪。
WMT 平行语料里，主题词、数字、专名、标点和领域词很强。
BoW 不懂结构，但它能抓这些共现线索。

所以如果 retrieval@1 长期持平，我们需要换测试方法，而不是硬说 TreeHeap 赢了。

下一轮应该增加这些测试：

| 测试 | 目的 |
|---|---|
| 长句 bucket | 看 TreeHeap 是否在长句、结构更复杂时超过 BoW |
| 词袋干扰 | 打乱词序但保留词袋，检查 BoW 是否被保留优势 |
| 低频词过滤 | 降低专名/数字带来的捷径 |
| 结构重排对 | 测试局部顺序变化时 TreeHeap 是否更稳 |
| 更大 retrieval pool | 从 2000 扩到 10k/50k，看优势是否保留 |
| small Transformer baseline | 判断 TreeHeap 是否只是打赢弱 baseline |
| root-only echo 限制 | 防止 leaf memory 偷偷承担全部回读任务 |

这才是后续能真正验证 TreeHeap 结构性的方向。

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
