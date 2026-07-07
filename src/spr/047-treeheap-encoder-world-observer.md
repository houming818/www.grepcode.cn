---
title: "[SPR-047] TreeHeap Encoder：世界观察者如何把规律写进树"
date: 2026-07-07
author: Codex Review
description: "SPR-047 把问题从 route/read 推回 encoder：TreeHeap 的语义结构不能靠哲学假设写入，必须由 encoder 通过 echo、上下文预测、InfoNCE、替换一致性和描述长度等可压缩性信号，从观察数据中学出 placement、fold 和 prefix。"
tags: [SPR, TreeHeap, ARA, Encoder, InfoNCE, Compression]
---

# TreeHeap Encoder：世界观察者如何把规律写进树

我们需要把问题退回更前面。

之前讨论了很多：

```text
route 怎么走
root 是不是 word bag
semantic prefix 能不能支持推理
compact state 为什么掉精度
```

这些问题都重要。

但它们有一个共同前提：

```text
H_tree 已经存在。
```

也就是说，我们默认已经有一个 TreeHeap state。

可是现在真正的问题是：

> 原始数据到底如何被 encoder 写成 TreeHeap？

如果 encoder 写错了，后面的 route、read、collapse、decode 都是在读错误状态。

所以 SPR-047 的核心不是 route。

核心是：

```text
Encode_Theta(raw observations) -> H_tree
```

这个 encoder 才是 TreeHeap 的世界观察者。

## 不能靠哲学把数据压进树

我们可以在文章里说：

```text
阿莫西林 -> 药品 -> 可摄入对象
米饭     -> 食物 -> 可摄入对象
```

这个说法很顺。

但它不是学习。

如果这些前缀是人手写进去的，那么 proof 只能证明：

```text
TreeHeap 可以使用已知语义前缀。
```

它不能证明：

```text
TreeHeap 可以从观察中发现语义前缀。
```

这就是当前的核心断点。

我们不能用哲学推理替代 encoder。

必须让 encoder 通过数据和 loss 自己学习：

```text
哪些东西应该靠近；
哪些东西应该合并；
哪些东西应该形成 internal node；
哪些 internal node 有迁移价值。
```

## Encoder 是世界观察者

我现在把 encoder 定义成：

```text
世界观察者 = 看见样本流，并把可复用规律排进 TreeHeap 的系统。
```

它不是简单 token embedding。

它要做几件事：

```text
1. 观察 token / span / relation
2. 给候选 placement 打分
3. 决定哪些东西应该合并
4. 生成 internal node state
5. 保持 echo 可读
6. 让有共同规律的对象共享 prefix
```

最小形式可以写成：

```text
tokens / spans / observations
  -> token states
  -> candidate placement scores
  -> soft TreeHeap write
  -> soft compose
  -> H_tree
```

其中：

```text
H_tree = 当前样本的运行时 TreeHeap state
Theta  = encoder / compose / route / read 的可学习参数
```

## 排序规律从哪里来

TreeHeap encoder 不会凭空知道排序规律。

它必须被目标函数选择。

我当前的假设是：

```text
TreeHeap 排序规律来自可压缩性。
```

也就是：

```text
如果一组 token / subheap 放在一起以后，
能更好地重构、预测、替换、迁移、减少规则数量，
那么它们应该靠近。
```

例如：

```text
eat rice
eat noodle
eat apple
cook rice
cook noodle
cook apple
```

如果没有 prefix，模型要记很多 pair。

如果形成一个 internal node：

```text
food-like = {rice, noodle, apple}
```

规则可以压缩成：

```text
eat food-like
cook food-like
```

这就是压缩收益。

所以 encoder 不是靠直觉发现 food。

它是发现：

```text
这些词共享上下文、替换行为和预测规律，
把它们合并后描述长度更短。
```

## 五个训练信号

我建议 TreeHeap encoder 至少需要五类 loss。

### 1. Echo / Reconstruction

压缩不能破坏样本。

```text
Decode(H_tree, read_position=k) -> token_k
Decode(H_tree, read_subheap=i)  -> subheap_i
```

如果只能形成语义类，但原句读不回来，那不是 S1 echo。

所以 echo loss 是底线。

### 2. Context Prediction

无监督学习不能凭空发现语义。

它只能从上下文统计里提取结构。

例如：

```text
eat [MASK] -> rice / noodle / apple
take [MASK] -> amoxicillin / ibuprofen
drink [MASK] -> water / milk
```

如果多个对象出现在相似上下文里，encoder 应该把它们推向相近 prefix。

### 3. InfoNCE / Contrastive Learning

InfoNCE 可以把“同一规律”的观察拉近，把错配观察推远。

形式上：

```text
L_InfoNCE =
  -log exp(sim(anchor, positive) / tau)
       / sum_j exp(sim(anchor, candidate_j) / tau)
```

positive 可以不是人工标签。

它可以来自：

```text
同一个 masked slot
同一个上下文窗口
同一个翻译对
同一个重复构式
```

negative 可以来自：

```text
错上下文
错翻译
随机替换
打乱语料
```

这让 encoder 有机会学到：

```text
哪些对象在观察上相似。
```

### 4. Replacement Consistency

如果两个词在很多上下文中可以互换，它们应该靠近。

例如：

```text
eat rice
eat noodle
eat apple
```

这里 rice / noodle / apple 有替换一致性。

但：

```text
eat shirt
```

不应被认为一致。

这种信号可以迫使 TreeHeap 形成可迁移 prefix。

### 5. Description Length / Compression Pressure

这是最接近 TreeHeap 精神的部分。

好的 internal node 应该减少描述长度。

没有 prefix：

```text
eat rice
eat noodle
eat apple
cook rice
cook noodle
cook apple
```

有 prefix：

```text
food-like = {rice, noodle, apple}
eat food-like
cook food-like
```

如果后者解释同样数据更短，就应该奖励。

这可以看成 MDL，Minimum Description Length。

也就是：

```text
好结构 = 用更短规则解释更多观察。
```

## 三种推理如何进入 encoder

我们一直说演绎、归纳、类比。

现在可以落到 encoder 上。

### 演绎

如果 prefix 已经存在：

```text
amoxicillin -> medicine -> consumable
eat accepts consumable
```

那么可以推出：

```text
eat amoxicillin
```

这是 SPR-046 的 supervised semantic-prefix toy proof 已经支持的窄结论。

### 归纳

现在更关键的是归纳。

模型只看见：

```text
eat rice
eat noodle
cook rice
cook noodle
```

它要归纳出：

```text
rice / noodle 共享某个 prefix
```

这个 prefix 不必一开始叫 food。

它可以只是 latent prefix。

名字是人类事后解释。

### 类比

类比更复杂，可以晚一点做。

例如：

```text
rice : food :: amoxicillin : medicine
eat : food :: take : medicine
```

这需要结构关系之间也可比较。

当前先不要急着 claim。

## 最小 proof 应该怎么设计

不要一上来 WMT。

先做无标签 synthetic corpus。

训练数据只给观察，不给类别：

```text
eat rice
eat noodle
eat apple
cook rice
cook noodle
cook apple

take amoxicillin
take ibuprofen
prescribe amoxicillin
prescribe ibuprofen

drink water
drink milk
pour water
pour milk
```

训练时不提供：

```text
food
medicine
beverage
```

训练目标：

```text
L = L_echo
  + L_context_prediction
  + L_InfoNCE
  + L_replacement_consistency
  + lambda * L_description_length
```

然后评估：

```text
rice/noodle/apple 是否形成相近 prefix
amoxicillin/ibuprofen 是否形成相近 prefix
water/milk 是否形成相近 prefix
held-out context 是否能迁移
```

注意：

```text
标签只能用于评估，不能用于训练。
```

这就避免了“监督假设”的循环。

## 必须有 shuffled control

这里最容易自欺欺人。

如果模型在任何数据上都能画出团簇，那就没意义。

所以必须有打乱语料对照。

例如 structured corpus：

```text
eat rice
eat noodle
cook rice
cook noodle
```

shuffled corpus：

```text
eat car
cook shirt
take apple
drink hoodie
```

预测应该是：

```text
structured corpus -> 稳定 prefix
shuffled corpus   -> prefix 消失或明显变差
```

如果两者一样好，说明模型不是在学习世界结构，而是在制造幻觉。

## 二维投影只能当显微镜

还有一个容易误会的点。

我们可以把高维 TreeHeap state 用 PCA / UMAP / t-SNE 压到二维。

如果 food-like / medicine-like 分开，会很直观。

但二维图不是训练目标本身。

它只是观察工具。

真正要优化的是高维 `H_tree`：

```text
echo 是否保留
context prediction 是否变好
InfoNCE retrieval 是否变好
held-out transfer 是否成立
structured-vs-shuffled gap 是否存在
```

二维图可以放在报告里，但不能只靠肉眼判断。

需要数字指标：

```text
nearest-neighbor class accuracy
cluster purity
ARI / NMI
held-out transfer accuracy
echo exact
```

## 当前 claim

这篇不是实验结果。

它是下一步设计。

当前 claim 是：

```text
TreeHeap semantic structure must be learned by an encoder-as-world-observer:
the encoder should infer placement, fold, and prefix structure from
compressibility signals rather than receive semantic labels by philosophical
assumption.
```

中文说：

```text
TreeHeap 的语义结构不能靠我们手写进去。
encoder 必须通过观察数据和 loss，
自己学出放置、折叠和前缀规律。
```

## Falsification

这个方向可以被证伪。

如果出现下面情况，就要降级或重做：

```text
1. shuffled corpus 也能产生同样 prefix；
2. flat / bag / pair baseline 在 held-out transfer 上追平；
3. TreeHeap 保住 echo 时就学不出 prefix；
4. 学出 prefix 时 echo 被破坏；
5. prefix 必须靠人工标签才能出现；
6. 学出的 prefix 对 route/read 没帮助。
```

## 下一步

我建议 DS 先 review 这套设计，而不是立刻跑大实验。

需要审的问题：

```text
1. 这些 loss 是否足以驱动 prefix induction？
2. description-length pressure 如何实现最小版？
3. InfoNCE positive/negative 是否会偷渡监督？
4. shuffled corpus control 是否足够？
5. flat baseline 应该怎么配？
6. TreeHeap 特异性在哪里，如何避免退化成普通 embedding clustering？
```

如果这些过了，再写 proof。

目标不是证明 TreeHeap 已经理解世界。

目标是证明一个更小的东西：

```text
encoder 能不能从观察中，把可压缩规律写进 TreeHeap。
```

> ARA: [encoder design](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/s1_encoder_world_observer.md) / [claims](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/claims.md) / [experiments](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/experiments.md)
