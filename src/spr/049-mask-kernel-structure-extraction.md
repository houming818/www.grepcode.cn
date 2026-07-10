---
title: "[SPR-049] Mask Kernel：从 token 识别转向结构信息提取"
date: 2026-07-10
lastmod: 2026-07-10
author: Codex Review
description: "承接 SPR-048 的私有编码森林，把下一步问题改写为：TreeHeap kernel 如何在 mask string / masked TreeHeap 上卷积，输出可坍缩的概率桶，而不是只识别单个 token。"
tags: [SPR, TreeHeap, ARA, S1, Mask, Kernel, Structure Extraction]
---

# Mask Kernel：从 token 识别转向结构信息提取

SPR-048 证明了一个很小但重要的机制：

```text
scalar loss 可以把规律写入参数 TreeHeap forest；
多个 head 可以串行组合；
held-out composition 可以超过常量 baseline 和未训练 baseline。
```

但 048 仍然是一个 toy codec proof。它更像是在问：

```text
参数树能不能记住并组合一个有限规则？
```

现在要往前走一步。Houming818 提醒了一个更合适的问题：

> 不要把目标理解成 token 识别。  
> 应该让 kernel 在一个 mask string / masked TreeHeap 上卷积，输出一个 string list，也就是可能的推理结果列表。

这句话把下一阶段的 S1 任务说清楚了。

## 1. 不是“这个 token 是谁”

传统 echo 任务容易把我们带偏：

```text
输入：I ate rice
输出：I ate rice
```

这里模型最容易学到的是：

```text
第 3 个位置是 rice
```

这当然有用，因为 TreeHeap 必须保真。但如果一直停在这里，TreeHeap 就只是一个结构化复读机。

真正更接近推理的问题应该是：

```text
输入：I ate [MASK]
输出：一组可能填入 [MASK] 的东西
```

例如：

```text
K_food_like("I ate [MASK]")
  -> rice, noodles, bread, apple, fish, ...
```

这里输出不再是一个确定 token，而是一个概率桶：

```text
P(x | "I ate [MASK]")
```

也就是说，模型要回答：

```text
这个空位在当前结构里像什么位置？
这个位置通常能接受哪些候选？
这些候选之间有什么可替换关系？
```

这就是结构信息提取。

## 2. Mask string 如何变成 TreeHeap

先从最简单的线性句子开始：

```text
I ate [MASK]
```

把它写入一个 TreeHeap：

```text
          root
        /      \
      left     right
     /   \     /   \
    I   ate  MASK  PAD
```

这棵树不是语言理论的最终形态，只是一个可计算的结构载体。

此时 kernel 可以在树上卷积。局部输入是：

```text
K_theta(q, H_i, H_left, H_right)
```

其中：

```text
q       = 当前 query，比如 "fill MASK" 或 "food-like"
H_i     = 当前节点状态
H_left  = 左子节点状态
H_right = 右子节点状态
```

kernel 输出可以是：

```text
[p_stop, p_left, p_right]
```

表示：

```text
停在当前节点读取；
继续去左子树；
继续去右子树。
```

也可以输出一个候选 token 概率桶：

```text
P(vocab | q, H_i, H_left, H_right)
```

更合理的设计是两者都有：

```text
route bucket:
  stop / left / right

fill bucket:
  rice / noodles / apple / park / museum / ...
```

## 3. 卷积不是一次查表

如果输入是：

```text
I ate [MASK]
```

一个 naive 查表模型可能只是记住：

```text
"I ate [MASK]" -> rice
```

这不是我们要的。

TreeHeap mask kernel 应该做的是在整棵树上滑动/递归读取：

```text
root:
  看到句子整体是一个主谓宾缺宾语结构

right:
  看到 MASK 在宾语位置

ate:
  提供动词约束

MASK:
  提供待坍缩位置
```

最后输出：

```text
P(token | verb=eat, slot=object, local_structure)
```

所以它不是识别 `rice`，而是提取了这样的结构：

```text
eat 的宾语位置
```

这个结构应该能支持多个答案：

```text
rice
noodles
bread
apple
fish
...
```

这才是概率容器。

## 4. 为什么这比 token echo 更接近推理

看一个 held-out 例子：

训练集中有：

```text
I ate rice
I ate noodles
I cooked rice
```

训练集中没有：

```text
I cooked noodles
```

如果模型只会 pair memory，它只能记住：

```text
ate-rice
ate-noodles
cooked-rice
```

它没有理由推出：

```text
cooked-noodles
```

但如果模型学到了结构信息：

```text
rice 和 noodles 在 ate object 位置可替换；
rice 又出现在 cooked object 位置；
那么 noodles 也可能适合 cooked object。
```

这就是一种很小的归纳迁移。

它还不是完整自然语言理解，但已经不是简单 token 识别。

## 5. Claim

下一步可以立这个 Claim：

```text
S1-MASK-KERNEL-C01

TreeHeap mask kernel can convolve over a masked string / masked TreeHeap state
and output a probability bucket of structurally plausible fillers, rather than
only reconstructing an observed token.
```

中文说法：

```text
TreeHeap mask kernel 能在带 mask 的句子结构上做卷积，
提取 mask 所在位置的结构约束，
并输出一组候选填充值的概率桶。
```

注意它的重点不是：

```text
能不能猜中某一个 token。
```

重点是：

```text
候选列表是否像一个结构类；
held-out 组合是否能迁移；
shuffled corpus 是否会破坏这种能力。
```

## 6. Predict

如果这个 Claim 成立，我们应该看到：

```text
P1. "I ate [MASK]" 的 top-k 候选偏向可食用对象；
P2. "I visited [MASK]" 的 top-k 候选偏向地点；
P3. "I drank [MASK]" 的 top-k 候选偏向饮品；
P4. held-out pair 的候选排名高于 pair-memory baseline；
P5. shuffled corpus control 会显著变差；
P6. 输出是有熵的概率桶，不应过早坍缩成一个 token。
```

“有熵”不是说越乱越好，而是说：

```text
模型在信息不足时应该保留多个合理候选。
```

例如：

```text
I ate [MASK]
```

如果输出只有：

```text
rice: 0.99
```

反而可能说明模型在记忆训练集。

更合理的是：

```text
rice:    0.20
noodles: 0.16
bread:   0.12
apple:   0.10
fish:    0.08
...
```

然后后续上下文再继续坍缩。

## 7. 最小数据集

先不要直接上 WMT。第一步应该用 controlled corpus，因为我们需要知道模型到底学到了什么。

例子：

```text
I ate rice
I ate noodles
I ate apple
I ate bread

I cooked rice
I cooked noodles
I cooked fish

I drank water
I drank milk
I drank juice

I visited Paris
I visited Beijing
I visited museum
I visited park

I bought rice
I bought medicine
I bought apple
```

训练时把一部分句子 mask：

```text
I ate [MASK]     -> rice / noodles / apple / bread
I drank [MASK]   -> water / milk / juice
I visited [MASK] -> Paris / Beijing / museum / park
```

然后保留一些未见组合：

```text
I cooked apple
I cooked bread
I bought noodles
I visited garden
```

如果模型能把这些候选排到合理位置，才说明它提取了结构。

## 8. 模型形式

一个最小 TreeHeap mask kernel 可以这样写：

```text
masked sentence
  -> WriteLeaves(tokens, mask_marker)
  -> Compose bottom-up
  -> for each node:
       K_theta(q, H_i, H_left, H_right)
  -> aggregate mask-position state
  -> softmax over vocab
```

损失函数：

```text
L_mask = CE(P_theta(token | masked_tree), gold_token)
```

但单 token CE 容易鼓励过早坍缩，所以评估时不能只看 top1。

还要看：

```text
top5 / top10
MRR
bucket purity
held-out rank
entropy
structured-vs-shuffled gap
```

其中：

```text
bucket purity
```

不是训练信号，只用于审计：

```text
I ate [MASK] 的 top10 里有多少属于 food-like？
I visited [MASK] 的 top10 里有多少属于 place-like？
```

## 9. Baseline

必须放 baseline，否则 proof 没意义。

最少要有：

```text
pair memory:
  只记 seen context-token pair

BoW MLP:
  不看树结构，只看 bag-of-words

flat sequence MLP:
  看位置，但没有 TreeHeap 子结构卷积

shuffled corpus:
  保持 token 频率，打乱 context-token 关系
```

TreeHeap 的价值不在于训练集 top1 高，而在于：

```text
held-out pair rank 更好；
top-k bucket 更合理；
shuffled control 明显失败；
相同参数量下比 flat baseline 更稳。
```

## 10. Proof Gate

第一版 proof gate 可以保守一点：

```text
TreeHeap heldout MRR > pair memory heldout MRR
TreeHeap heldout MRR > shuffled TreeHeap heldout MRR
TreeHeap bucket purity > shuffled bucket purity
TreeHeap top5 > pair memory top5
entropy 落在合理范围，不能完全坍缩
```

如果 BoW MLP 赢了，也不是世界末日。那说明：

```text
这个 toy 数据还没有要求 TreeHeap 结构；
或者 kernel 设计没有真正用到子结构。
```

这会反过来帮助我们改数据和模型。

## 11. ARA 草案

```text
Claim:
  S1-MASK-KERNEL-C01

Predict:
  Masked TreeHeap convolution produces structurally plausible probability
  buckets and transfers to held-out context-token combinations.

Proof:
  Train on controlled masked corpus.
  Compare TreeHeap mask kernel against pair memory, BoW MLP, flat sequence MLP,
  and shuffled-corpus control.

Evidence:
  summary.json
  trace.jsonl
  topk_examples.json
  README.md

Falsification:
  If shuffled corpus matches TreeHeap, structure was not learned.
  If pair memory matches held-out rank, no transfer occurred.
  If BoW/flat baselines dominate, TreeHeap kernel has not shown added value.
  If output always collapses to one token, probability-container behavior is absent.
```

## 12. 当前结论

SPR-048 说的是：

```text
参数 TreeHeap forest 可以被 loss 写入，并能做串行组合。
```

SPR-049 要推进的是：

```text
kernel 在 masked TreeHeap 上卷积，读出的不是一个 token，
而是一个结构位置对应的候选概率桶。
```

这一步如果成立，S1 的目标就会更清楚：

```text
先不要问 TreeHeap 是否懂语言；
先问它是否能从语料观察里提取可复用的结构槽位，
并用 kernel 输出可坍缩的推理候选列表。
```

这才是从 echo 走向 encoder/world-observer 的下一块台阶。
