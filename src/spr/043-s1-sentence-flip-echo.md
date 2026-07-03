---
title: "[SPR-043] S1-echo 句级还原：用 TreeHeap 自己的 Flip 搅动，再学着恢复"
date: 2026-07-02
weight: 43
author: nio (Houming818) & Codex Review
description: "SPR-043 proof：在 20,000 条真实英文短句上，用 TreeHeap Flip(root, full_depth) 做同群扰动，再学习 inverse route 还原句子，并按句长统计 exact/token/edit。"
tags: [SPR, TreeHeap, ARA, S1, Echo, Flip]
---

# S1-echo 句级还原：用 TreeHeap 自己的 Flip 搅动，再学着恢复

这篇是补 SPR-041 缺的东西。

之前的 041 讲了很多理论：

```text
mirror 输入
-> inverse gate
-> canonical echo state
-> shared decoder
```

但 Houming818 的批评是对的：

```text
这还是有点空。
你得拿真实句子出来，看 echo 到底能还原到什么程度。
```

所以 SPR-043 做一个更直观的实验：

```text
真实英文句子
-> TreeHeap 自己的 Flip 算子搅动
-> 学一个 inverse route
-> 还原原句
```

并且按句长统计：

```text
exact_match
token_acc
edit_similarity
```

这不是翻译实验。

它只是问：

```text
S1-echo 在句子级别，能不能把被 TreeHeap 同群操作扰动过的句子还原回来？
```

## 为什么必须是“同群扰动”

这里有一个很重要的修正。

不能这样做：

```text
用 Python array reverse 搅乱句子；
再让 TreeHeap 恢复。
```

这不干净。

因为那等于：

```text
用别的代数系统制造扰动，
再让 TreeHeap 背锅恢复。
```

这不能说明 TreeHeap 自己的代数闭包。

所以这次的规则是：

```text
扰动必须由 TreeHeap 自己的算子产生。
恢复也必须由 TreeHeap 自己的算子表达。
```

也就是：

```text
H = WriteLeaves(sentence)
H_observed = Flip(H, root, full_depth)
H_restored = learned_inverse(H_observed)
```

## TreeHeap Flip 是什么

对一个 TreeHeap 节点：

```text
Flip(node):
  swap(left, right)
  recursively Flip(left)
  recursively Flip(right)
```

如果从 root 开始，翻到完整深度：

```text
Flip(root, full_depth)
```

它在 leaf 顺序上看起来像整句反转。

但定义不是：

```text
tokens[::-1]
```

而是树上的操作：

```text
left child <-> right child
```

递归执行。

这就是“同群扰动”的意思。

## Hard proof：先证明闭包

先不学习。

直接做：

```text
H = WriteLeaves(sentence)
H1 = Flip(H, root, full_depth)
H2 = Flip(H1, root, full_depth)
DecodeLeaves(H2)
```

因为 mirror / flip 是自逆的：

```text
Flip(Flip(H)) = H
```

所以 hard proof 应该 100% 还原。

实验结果：

```text
hard_treeheap_closure_exact = 1.000000
```

这说明：

```text
TreeHeap Flip 自己的代数闭包没问题。
```

## Learned proof：再学习 inverse route

学习版不是直接手写第二次 Flip。

它拿到的是被 TreeHeap Flip 搅动后的句子：

```text
observed = Flip(H)
```

然后学习一个 inverse route，把它规约回 canonical state：

```text
observed leaf embeddings
-> learned inverse route
-> canonical state
-> shared decoder
-> original sentence
```

loss 仍然不只看输出 token。

它包含：

```text
CE(output, target_tokens)
+ state_loss(canonical_state, target_state)
+ route_entropy
```

原因和 SPR-041 一样：

```text
如果只看输出 token，
decoder 可能补偿错误结构。
```

我们要让中间 state 也接近 canonical state。

## 数据规模

这次不是 toy token id。

数据来自：

```text
WMT17 English side
```

处理方式：

```text
whitespace / punctuation tokenization
句长 3 到 32
词表 8192
丢弃 UNK 句子
```

样本：

```text
total = 20,000
train = 16,000
test = 2,000
ood = 2,000
```

这里的 OOD 不是跨分布语言外推，只是 held-out split。它的作用是：

```text
看模型有没有把训练句子死记住。
```

## 总体结果

证据目录：

```text
ara/s1-echo/evidence/s1_sentence_flip_echo_probe/
```

脚本：

```text
ara/s1-echo/src/s1_sentence_flip_echo_probe.py
```

主机：

```text
io.grepcode.cn
```

结果：

| 指标 | 数值 |
|---|---:|
| hard TreeHeap closure exact | `1.000000` |
| learned OOD exact | `0.964500` |
| learned OOD token acc | `0.997818` |
| learned OOD edit similarity | `0.997871` |
| no-inverse baseline OOD exact | `0.000000` |
| pilot_pass | `true` |

这说明：

```text
在 2000 条 held-out 句子上，
完全还原率是 96.45%。

token 级准确率是 99.78%。

没有 inverse 的 baseline 完全无法整句还原。
```

这比“空理论”扎实很多。

## 按句长看

部分长度桶：

| length | samples | exact | token_acc |
|---:|---:|---:|---:|
| 3 | 41 | `1.0000` | `1.0000` |
| 8 | 61 | `1.0000` | `1.0000` |
| 12 | 68 | `0.9706` | `0.9975` |
| 16 | 104 | `0.9615` | `0.9970` |
| 20 | 83 | `0.9759` | `0.9988` |
| 24 | 84 | `0.9405` | `0.9960` |
| 28 | 52 | `0.9615` | `0.9986` |
| 32 | 42 | `0.9286` | `0.9978` |

完整长度表在：

```text
summary.json
```

一个值得注意的现象：

```text
句长变长后，exact 会有波动和下降，
但 token_acc 仍然很高。
```

这说明多数失败不是整句崩掉，而是少数 token 错位或词混淆。

## 可读例子

例子 1：

```text
observed:
. nato transform would step bold a such, yes

restored:
yes, such a bold step would transform nato.

target:
yes, such a bold step would transform nato.
```

例子 2：

```text
observed:
. challenges of set unique a faces countries brics the of each governance poor and institutions weak, example for confront economies developing all almost that problems the beyond

restored:
beyond the problems that almost all developing economies confront for example, weak institutions and poor governance each of the brics countries faces a unique set of challenges.

target:
beyond the problems that almost all developing economies confront for example, weak institutions and poor governance each of the brics countries faces a unique set of challenges.
```

例子 3，长句：

```text
observed:
. substantially resistance antibiotic of rise the slowing, 80 nearly by antibiotics of use the reduce would agencies regulatory governmental by enacted be could which of both alone measures two these

restored:
these two measures alone both of which could be enacted by governmental regulatory agencies would reduce the use of antibiotics by nearly 80, slowing the rise of antibiotic resistance substantially.

target:
these two measures alone both of which could be enacted by governmental regulatory agencies would reduce the use of antibiotics by nearly 80, slowing the rise of antibiotic resistance substantially.
```

也有失败例子。

```text
observed:
. quickly adopted be can office s prosecutor the reforming legislation condition eu remaining only the

restored:
the only remaining eu condition legislation reforming the systems s office can be adopted quickly.

target:
the only remaining eu condition legislation reforming the prosecutor s office can be adopted quickly.
```

这里错在：

```text
prosecutor -> systems
```

结构基本还原了，但 token 识别错了。

这符合总体统计：

```text
exact 不是 100%，但 token_acc 很高。
```

## 这证明了什么

SPR-043 支持：

```text
S1-echo 不只是 toy token id。
它可以在真实句子上做句级同群扰动恢复。
```

更具体：

```text
TreeHeap Flip(root, full_depth)
可以制造合法扰动；
hard Flip 闭包 100%；
learned inverse route 可以把大多数真实短句还原；
按句长统计后仍有较高 exact/token/edit。
```

## 还没有证明什么

这篇没有证明：

```text
翻译
语义理解
局部 subheap 自动发现
自然语言 trigger
自动选择 node/depth
复杂语法迁移
```

这次还是：

```text
root/full_depth flip
```

也就是说：

```text
node 和 depth 是给定的。
```

下一步才是：

```text
学习 P(node, depth | H, context)
```

让模型自己判断：

```text
该翻哪个 subheap？
翻多深？
```

## 结论

SPR-043 把 S1-echo 从“抽象机制”推进到“可读句子证据”。

一句话：

```text
用 TreeHeap 自己的 Flip 算子把真实句子搅动后，
learned inverse route 可以在 held-out 句子上达到：

exact = 96.45%
token_acc = 99.78%
edit_similarity = 99.79%
```

这不是 WMT 翻译。

但它证明了：

```text
TreeHeap S1-echo 在句级 hash / 句级结构 state 层面，
已经能做可观察、可统计、可读的恢复实验。
```

> ARA: [S1 sentence flip echo](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/s1_sentence_flip_echo.md) / [evidence](https://github.com/houming818/sametime/tree/main/ara/s1-echo/evidence/s1_sentence_flip_echo_probe) / [claims](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/claims.md)

## 2026-07-03 修正：从整树 flip 到局部 subheap flip

Houming818 对上面的整树实验提出了一个很重要的批评：

```text
整句 Flip(root, full_depth) 太理想化。
真实语言迁移通常不是整句反转，而是某个局部 subheap 被调整。
```

这个批评是对的。
所以上面的 `S1-ECHO-SENT-C01` 现在应该读成：

```text
整树 same-algebra flip smoke proof
```

它证明 TreeHeap 自己的 `Flip` 算子可以制造合法扰动，也证明 learned inverse route 可以恢复大部分真实短句。
但它还不够像真实语言。

因此我补了一个更接近实际的实验：

```text
S1-ECHO-LOCAL-FLIP-C01
```

### 新实验怎么做

这次不再翻整棵树。
对每个真实英文短句，先选一个局部连续 span：

```text
sentence = [w0, w1, ..., wk, ..., wn]
span = [wi, ..., wj]
```

然后只对这个 span 建一个局部 TreeHeap：

```text
H_span = WriteLeaves(span)
```

再用 TreeHeap 自己的局部 flip：

```text
H_span_observed = Flip(span_root, full_depth)
```

句子的其他部分保持不动：

```text
left_context + DecodeLeaves(H_span_observed) + right_context
```

最后训练一个 inverse route，把局部 span 扭回 canonical echo state，再用同一个固定 codebook decoder 读回 token。

注意，这里仍然不是翻译。
它只问一个更小、更清楚的问题：

```text
如果真实句子里某个局部 subheap 被 TreeHeap 同群算子 flip 过，
模型能不能用梯度学会把这个局部结构恢复？
```

### 数据和结果

运行位置：

```text
io.grepcode.cn
```

证据目录：

```text
ara/s1-echo/evidence/s1_local_flip_echo_probe/
```

数据设置：

```text
WMT17 English side
samples = 20,000
train/test/OOD = 16,000 / 2,000 / 2,000
sentence length = 8..32
vocab = 8192
local span length = 2..8
```

结果：

```text
hard_local_treeheap_closure_exact = 1.0000
learned_ood_exact                 = 1.0000
learned_ood_token_acc             = 1.0000
learned_ood_edit_similarity       = 1.0000

no_inverse_ood_exact              = 0.0010
no_inverse_ood_token_acc          = 0.7698
no_inverse_ood_edit_similarity    = 0.7376
```

按 span 长度拆开看：

| span length | OOD exact | OOD token acc |
|---:|---:|---:|
| 2 | 1.0000 | 1.0000 |
| 3 | 1.0000 | 1.0000 |
| 4 | 1.0000 | 1.0000 |
| 5 | 1.0000 | 1.0000 |
| 6 | 1.0000 | 1.0000 |
| 7 | 1.0000 | 1.0000 |
| 8 | 1.0000 | 1.0000 |

按 span 在句子里的位置拆开看：

| span position | OOD exact | OOD token acc |
|---|---:|---:|
| front | 1.0000 | 1.0000 |
| middle | 1.0000 | 1.0000 |
| back | 1.0000 | 1.0000 |

这个结果比整树 flip 更干净。
因为 no-inverse baseline 已经能保留未翻转的上下文 token，所以它的 token acc 还有 `0.7698`。
但它几乎不能完整还原句子：

```text
no_inverse_ood_exact = 0.0010
```

这说明真正缺的不是 token 读取能力，而是局部结构 inverse。

### 这证明了什么

这次 proof 支持一个更准确的 claim：

```text
TreeHeap 的局部 subheap flip 可以作为同群结构扰动；
给定 span start/span length 时，
一个可学习 inverse route 可以通过梯度恢复 canonical echo state。
```

换成更直白的话：

```text
TreeHeap 不只是整句反转玩具。
它可以在真实句子中的局部片段上做结构扰动和结构恢复。
```

这对后续 S1 有意义，因为真实语言里的调整通常就是局部的：

```text
介词短语移动
时间短语前置
定语范围调整
局部词序变化
```

### 还没有证明什么

这次实验仍然没有证明：

```text
模型能自动发现哪个 subheap 需要 flip
模型能自动决定 flip depth
模型知道这个 flip 对应真实翻译规则
模型理解语义
模型能直接提升 WMT 翻译质量
```

因为这次实验里：

```text
span start/span length 是给定的 metadata
```

所以真正的下一步不是继续证明“能不能反翻转”。
这个已经过了。

下一步应该是：

```text
学习 P(node, depth | H, context)
```

也就是让模型自己判断：

```text
该动哪一个局部 subheap？
动到多深？
什么时候不动？
```

这才更接近 S1 走向 S2 的入口。

> ARA update: [local flip logic](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/s1_local_flip_echo.md) / [local flip evidence](https://github.com/houming818/sametime/tree/main/ara/s1-echo/evidence/s1_local_flip_echo_probe)
