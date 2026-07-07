---
title: "[SPR-046] TreeHeap 语义前缀压缩：从 word bag 到可迁移的结构状态"
date: 2026-07-06
author: Codex Review
description: "SPR-046 重写版：用本科可理解的方式说明 Transformer 并不保存所有可能句子，TreeHeap 的假设是用树形语义前缀压缩形成可解码、可迁移的结构状态；并记录 content-aware route、compact state 和 semantic-prefix toy proof 的证据与边界。"
tags: [SPR, TreeHeap, ARA, S1, Routing, State, Semantics]
---

# TreeHeap 语义前缀压缩：从 word bag 到可迁移的结构状态

这篇重写 046。

之前版本把太多中间修正写进正文：查找树、route、content-aware、compact state、H/Q/Theta、霍夫曼类比、语义前缀 proof 混在一起。读起来像沿途事故记录，不像一篇能帮助后续工作的文章。

现在从基本知识重新讲。

这篇只回答一个问题：

> TreeHeap 的 root / internal node 如果不是 word bag，那它应该是什么？

我的当前答案是：

```text
TreeHeap state 应该是可解码、可压缩、可迁移的语义前缀结构。
```

也就是说，root 不是把所有词混在一起。

root 应该保存一种结构状态，使得模型在给定问题 `Q` 时，可以从中坍缩出需要的信息。

## 第一件事：Transformer 也不是把所有可能性存下来

先拿 Transformer 做参照。

假设语料里有很多句子：

```text
我 吃 米饭
我 吃 面条
我 吃 苹果
我 吃 药
我 吃 阿莫西林
```

我们可能会误以为 Transformer 学到的是一个巨大表：

```text
吃 -> {米饭, 面条, 苹果, 药, 阿莫西林, ...}
```

但这不是准确理解。

Transformer 不会为每个词保存“后面所有可能词的完整集合”。

它学的是一个条件概率函数：

```text
P(next token | context)
```

训练时，模型看到大量上下文和目标 token。

例如：

```text
context = 我 正在 吃
target  = 米饭
```

模型会生成一个 hidden state：

```text
h = Transformer(context)
```

然后输出词表概率：

```text
logits = W_vocab h
P(token) = softmax(logits)
```

如果正确答案是“米饭”，loss 会推动参数，让“米饭”的概率更高。

长期训练后，模型不是记住一张简单共现表，而是在参数矩阵里形成一个分布式函数。

这个函数会捕捉类似：

```text
吃 后面常接可摄入对象
可摄入对象包括食物、药品、某些抽象对象
```

但这些结构通常是隐式的。

也就是说，Transformer 的强项是：

```text
用大规模参数矩阵学习 flat context -> probability 的函数。
```

它不枚举所有可能。

它学习一个能泛化的概率曲面。

## 第二件事：word bag 不够

现在回到 TreeHeap。

如果一句话是：

```text
I like small cats
```

一个 word bag 表示是：

```text
{I, like, small, cats}
```

这个表示能回答：

```text
cats 出现过吗？
```

但它不能回答：

```text
第 1 个词是什么？
small 修饰谁？
small cats 是不是一个 subheap？
I like small cats 和 cats like small I 是否不同？
```

所以 word bag 不是 echo 所需的 root state。

Echo 要求至少能恢复：

```text
token identity    有哪些 token
address / path    token 在哪个结构位置
composition       token 如何组成 subheap / sentence
```

如果 root 只保存 bag，那顺序和结构已经丢了。

所以更合理的说法是：

```text
root 不是词集合。
root 是一个可解码的结构状态。
```

给一个 query：

```text
Q = read position 2
```

decoder 应该能读出：

```text
small
```

给另一个 query：

```text
Q = read subheap containing adjective+noun
```

decoder 应该能读出：

```text
small cats
```

也就是说，root 的含义不是靠我们肉眼解释出来的。

它靠读出能力证明：

```text
Decode(root, Q) -> expected information
```

## 第三件事：TreeHeap 的不同假设

Transformer 做的是 flat context function。

TreeHeap 想做的是 structured heap context function。

可以写成：

```text
Transformer:
  H_flat = sequence hidden states
  Q      = decoder step / attention query
  Theta  = attention + MLP + vocab head parameters
  output = token probability

TreeHeap:
  H_tree = TreeHeap states
  Q      = read / write / generate intent
  Theta  = TreeHeap kernel parameters
  output = route / read / token probability
```

所以 TreeHeap 不是要比 Transformer 更神秘。

它的假设更具体：

```text
语言信息本身有层级、前缀、子结构和组合关系。
如果模型的状态空间也显式支持这些结构，
就可能在某些任务上更容易泛化。
```

这里的重点不是“树比矩阵高级”。

重点是 TreeHeap 可能提供一种归纳偏置：

```text
address
path
subheap
compose
decompose
prefix compression
probabilistic collapse
```

这些结构在普通 flat 表示里不显式。

## 第四件事：语义前缀压缩

现在进入这篇的核心。

TreeHeap root / internal node 不应该只是频率压缩。

也不应该只是 word bag 压缩。

它应该尝试形成语义前缀压缩。

什么叫语义前缀？

例如：

```text
阿莫西林 -> 药品 -> 可摄入对象 -> 物体
米饭     -> 食物 -> 可摄入对象 -> 物体
面条     -> 食物 -> 可摄入对象 -> 物体
苹果     -> 食物 -> 可摄入对象 -> 物体
```

如果模型只记 pair，它只知道：

```text
吃 + 米饭
吃 + 面条
吃 + 苹果
```

如果新组合出现：

```text
吃 + 阿莫西林
```

pair memory 没见过，就容易失败。

但如果模型有语义前缀，它可以做一个演绎迁移：

```text
阿莫西林 是 药品
药品 是 可摄入对象
吃 接受 可摄入对象
所以 吃 + 阿莫西林 可以成立
```

这就是 TreeHeap 可能比 word bag 更有意义的地方。

它不是保存所有句子。

它保存可复用的中间语义节点。

这些节点可以支持未见组合的推理。

## 第五件事：这和霍夫曼树像在哪里，不像在哪里

霍夫曼树是一种编码树。

它把高频符号放到短路径，低频符号放到长路径。

它的目标是压缩长度。

TreeHeap 的语义前缀树可以借用这个直觉：

```text
路径是一种编码。
internal node 是一组可以共享前缀的信息。
leaf 是更具体的信息。
```

但 TreeHeap 不应该只按频率压缩。

它更应该按可推理性压缩。

也就是说，internal node 应该回答：

```text
哪些叶子共享同一种语义规则？
哪些组合可以通过这个节点迁移？
哪个前缀能最大化当前任务的信息增益？
```

所以它更像：

```text
Huffman-like semantic prefix tree
```

而不是普通 Huffman coding。

## 第六件事：route 不是查找树，而是信息坍缩

这点也要说清楚。

以前我把 TreeHeap route 讲成：

```text
从 root 开始，找 cats，走 left/right/stop。
```

这个类比太像二叉搜索树。

二叉搜索树的问题是：

```text
给定 key
比较大小
往左或往右找
```

TreeHeap 的目标不是这个。

更准确地说，TreeHeap route 是：

```text
在当前问题 Q 下，
从当前 node 的信息分布里，
选择是否停下，或者坍缩到哪个子信息分支。
```

动作不是“找 key”。

动作含义应该是：

| 动作 | 含义 |
|---|---|
| `stop` | 当前 node 的信息已经足够回答 Q |
| `left` | 左分支的信息对 Q 更有用 |
| `right` | 右分支的信息对 Q 更有用 |

所以更准确的名字是：

```text
InformationCollapseRoute
```

它输出的是一个概率桶：

```text
P(stop), P(left), P(right)
```

如果要硬执行，就坍缩成一个动作。

如果还不确定，就保留概率容器。

这和我们之前一直说的“延迟坍缩”是一致的。

## 第七件事：H、Q、Theta 的位置

现在把对象定义清楚。

```text
H      = 当前样本形成的 TreeHeap state
Q      = 当前任务意图 / query / read-write intent
Theta  = 可学习的参数 TreeHeap 或 kernel 参数
Output = 概率桶
```

形式上：

```text
Route_Theta(H, Q, node=i)
  -> P(stop), P(left), P(right)
```

这里 `H` 不是长期参数。

`H` 是输入样本的运行时状态。

比如：

```text
H = Encode("I like small cats")
```

`Theta` 才是训练后保留下来的东西。

类比线性回归：

```text
y = w x + b

x    是输入
w,b  是参数
```

TreeHeap 里：

```text
H      是输入形成的状态
Theta  是模型学到的参数
Q      是这次要解决的问题
P      是输出概率
```

训练时，loss 会更新 `Theta`。

如果 encoder / compose / route / read 都是可学习的，那么可能有多组参数：

```text
Theta_encode
Theta_compose
Theta_route
Theta_read
Theta_decode
```

但现在不能把这些混在一起。

否则即使实验成功，我们也不知道到底是谁学会了东西。

## 第八件事：当前证据 1，content-aware dense route

先说已经做过的 route proof。

实验：

```text
S1-CONTENT-ROUTE-C01
```

问题是：

```text
kernel 能不能真的读 arr[i] / arr[left] / arr[right] 的内容，
而不是读几何答案 feature？
```

dense 版本把每个 subheap 表示成 vocab-count 向量。

也就是说：

```text
arr[i] = 这个子堆里有哪些 token 的清单
```

这不是最终语义表示。

但它可以作为机制尺子：

```text
如果清单都跑不通，route 机制就有问题。
```

结果：

| 指标 | 数值 |
|---|---:|
| samples | `20000` |
| train route steps | `352110` |
| OOD route steps | `44130` |
| dense feature memory | `6191.25 MB` |
| OOD step acc | `0.9983` |
| OOD route exact | `0.9902` |
| flat length-matrix OOD exact | `0.0000` |
| pilot pass | `true` |

这说明：

```text
content-aware route 可以读 subheap 内容并完成递归 stop/left/right。
```

边界：

```text
这不是语义理解。
这不是翻译。
这仍然使用 supervised query token。
这仍然依赖 dense vocab-count state。
```

## 第九件事：当前证据 2，compact state 失败在哪里

接着做 compact 版本。

目标是把 dense vocab-count state 换成小向量。

做法：

```text
token id -> 固定随机向量
arr[i]   -> 子堆 token 向量求和
```

64D 结果：

| 指标 | 数值 |
|---|---:|
| compact memory | `324.84 MB` |
| dense prior memory | `6191.25 MB` |
| memory reduction | `19.06x` |
| OOD step acc | `0.9973` |
| OOD route exact | `0.9838` |
| pilot pass | `false` |

128D 结果：

| 指标 | 数值 |
|---|---:|
| compact memory | `637.59 MB` |
| memory reduction | `9.71x` |
| OOD step acc | `0.9973` |
| OOD route exact | `0.9837` |
| pilot pass | `false` |

这个结果说明：

```text
随机 token sum 能大幅省内存，
但会损失路径级 exactness。
```

而且 128D 没有明显变好。

所以问题不是简单的维度不够。

更可能是：

```text
随机向量求和不是好的 subheap state。
```

下一步应该学：

```text
learned token embedding
learned subheap compose
learned prefix state
```

## 第十件事：当前证据 3，语义前缀 toy proof

为了验证“语义前缀能带来演绎迁移”，我做了一个很小的 toy proof。

它不是自然语料实验。

它只测试一个基本机制：

```text
如果语义前缀结构存在，
它能不能支持未见 pair 的推理？
```

Toy ontology：

```text
rice        -> entity -> consumable -> food
noodle      -> entity -> consumable -> food
apple       -> entity -> consumable -> food
amoxicillin -> entity -> consumable -> medicine
ibuprofen   -> entity -> consumable -> medicine
water       -> entity -> drinkable  -> beverage
shirt       -> entity -> wearable   -> clothing
car         -> entity -> drivable   -> vehicle
```

谓词规则：

```text
eat   accepts consumable
take  accepts medicine
drink accepts drinkable
wear  accepts wearable
drive accepts drivable
visit accepts visitable
```

关键设置：

```text
训练集不包含 eat + amoxicillin。
```

但是训练集包含：

```text
eat + rice
eat + noodle
eat + apple
take + amoxicillin
```

对照组：

```text
pair_memory       只记见过的正例 pair
pair_logistic     只用 verb-object pair id
token_additive    只用 verb id + object id
semantic_prefix   使用 object 的语义前缀 path
```

结果：

| 模型 | test acc |
|---|---:|
| pair memory | `0.4` |
| pair logistic | `0.4` |
| token additive | `0.6` |
| semantic prefix | `1.0` |

关键 held-out case：

```text
Question:
  Can eat + amoxicillin be accepted without that pair in training?

pair_memory:
  gold = 1
  pred = 0

semantic_prefix:
  path = [entity, consumable, medicine]
  gold = 1
  prob = 0.7088
  pred = 1
```

这支持一个很窄的 claim：

```text
有监督的语义前缀结构，
可以支持 pair memory 不具备的演绎迁移。
```

边界必须写清楚：

```text
ontology 是手工给的；
prefix path 是监督的；
这不证明模型能从自然语料自动学出 medicine / consumable；
这不证明 WMT；
这不证明自然语言理解。
```

## 当前假设

现在我会把假设写得更干净。

### Hypothesis 1: root 不是 word bag

TreeHeap root 应该是可解码结构状态。

它至少要支持：

```text
read token
read path
read subheap
read semantic prefix
```

如果只能回答“某词是否出现”，那只是 bag，不够。

### Hypothesis 2: internal node 应该承载可迁移前缀

internal node 不只是左右孩子求和。

它应该尽可能形成：

```text
可复用的语义类
可组合的短语结构
可迁移的推理前缀
```

例如：

```text
medicine -> consumable
food -> consumable
```

这样新的 leaf 可以继承规则。

### Hypothesis 3: route 是信息坍缩

Route 不应该理解成查找树搜索。

它应该是：

```text
Collapse(H_i, Q; Theta) -> ProbabilityBucket(stop, left, right)
```

其中 left/right 代表信息分支，stop 代表当前信息已经足够。

### Hypothesis 4: Theta 应该逐步 TreeHeap 化

当前实验里的 `Theta` 还常常是普通 MLP 或 logistic 权重。

这只是工程近似。

更强的目标是：

```text
Theta_encode
Theta_compose
Theta_route
Theta_read
```

都逐步变成显式 TreeHeap kernel / parameter heap。

否则我们只是在普通模型外面套 TreeHeap 词汇。

## 下一步怎么走

我建议下一步不是继续写更大口号。

而是做三个 proof。

### Proof A: learned prefix induction

现在 semantic prefix 是手工给的。

下一步要从数据里学出来。

例如只给训练事实：

```text
eat rice
eat noodle
eat apple
take amoxicillin
take ibuprofen
```

看模型能否形成隐含前缀：

```text
food
medicine
consumable
```

这是最关键的一步。

### Proof B: prefix state + echo

不仅要判断 pair 是否成立，还要能 echo。

也就是说：

```text
root state
  -> read position
  -> read subheap
  -> read semantic prefix
```

三件事要同时成立。

否则语义前缀可能破坏 echo。

### Proof C: TreeHeap Theta

把普通 logistic/MLP 参数替换成更明确的参数 TreeHeap。

目标是证明：

```text
Theta 本身可以按 root/left/right/prefix slot 组织，
并通过 loss 学会坍缩规则。
```

这是从工程近似走向 TreeHeap 理论闭包的关键。

## 结论

SPR-046 现在的结论是：

```text
TreeHeap 的核心不应该是 word bag root。
```

更合理的方向是：

```text
root/internal node 形成可解码、可压缩、可迁移的语义前缀结构。
```

Transformer 学的是：

```text
flat context -> probability
```

TreeHeap 想学的是：

```text
structured heap context -> probability
```

当前证据支持三个很小的点：

```text
1. content-aware route 可以读 subheap 内容；
2. random-sum compact state 不够好；
3. supervised semantic prefix 可以支持 toy deductive transfer。
```

但还没有证明：

```text
TreeHeap 能从自然语料学出语义前缀；
TreeHeap 能翻译；
TreeHeap 已经优于 Transformer；
Theta 已经是严格参数 TreeHeap。
```

所以当前航行问题已经变清楚了：

```text
不要再争 root 是不是 word bag。
它不应该是。

下一步要证明：
语义前缀能不能从数据里学出来，
并且不破坏 echo / route / read。
```

> ARA: [claims](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/claims.md) / [experiments](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/experiments.md) / [content route evidence](https://github.com/houming818/sametime/tree/main/ara/s1-echo/evidence/s1_content_treeheap_route_probe_20k_e5) / [compact evidence](https://github.com/houming818/sametime/tree/main/ara/s1-echo/evidence/s1_compact_content_treeheap_route_probe_20k_e5) / [semantic prefix evidence](https://github.com/houming818/sametime/tree/main/ara/s1-echo/evidence/s1_semantic_prefix_compression_probe)
