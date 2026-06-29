---
title: "[SPR-012] 子堆核搜索：TreeHeap 里的卷积式推理"
date: 2026-06-18
weight: 12
author: nio (Houming818) & Codex Review
description: "把矩阵卷积里的局部核匹配，改写成 TreeHeap 的 SubHeap Kernel Search：一种拓扑搜索和局部推理操作。"
tags: [SPR, TreeHeap, Algebra, Convolution, Topology]
---

# 子堆核搜索：TreeHeap 里的卷积式推理

上一篇文章讲了 TreeHeap Algebra：

```text
compose
decompose
transpose
project
unproject
energy
probability container
```

但这里还少了一个很重要的操作。

用户提出了一个矩阵卷积的类比：

```text
1 0 1
0 1 0
1 0 1
```

如果我们有这样一个卷积核，就可以在一张矩阵或图像上滑动它。
哪里局部模式相同，哪里就会有高响应。

这件事表面上是卷积。

但本质上是：

```text
用一个局部模式，在大结构里搜索对应部分。
```

这已经很接近推理。

因为推理很多时候不是“生成一个 token”，而是：

```text
在当前结构里找到一个已知模式。
```

所以这篇文章把这个操作整理成 TreeHeap 的新代数操作：

```text
SubHeap Kernel Search
```

中文可以叫：

```text
子堆核搜索
```

对应的公开实验仓：

```text
https://github.com/houming818/sametime
```

其中 ARA 记录入口是：

```text
ara/s2-translation/logic/predicts.md
ara/s2-translation/logic/solution/treeheap_algebra.md
ara/s2-translation/trace/research_dag.yaml
```

## 当前 TreeHeap 没有这个操作

先说清楚：

```text
当前实现里还没有子堆核搜索。
```

现在实现更多是：

```text
L0(token)
  x path/world
  -> CMul
  -> t_merge
```

这是点级变换。

也就是说，它主要回答：

```text
这个 token 进入某个背景以后，向量怎么变？
```

但子堆核搜索要回答的是：

```text
整个 TreeHeap 里，哪里出现了某个局部结构模式？
```

这不是同一类问题。

CMul 像是把一个点放进背景场。

SubHeap Kernel Search 像是在一整个结构里找模式。

## 图像卷积在做什么

先用图像理解。

假设有一个 kernel：

```text
1 0 1
0 1 0
1 0 1
```

它在图像上滑动。

每到一个位置，就问：

```text
这里的局部形状像不像这个 kernel？
```

像，就高响应。

不像，就低响应。

这就是：

```text
local pattern matching
```

中文可以说：

```text
局部模式匹配
```

## 线性秩序和取模周期

这里还有一个更底层的理解。

矩阵卷积不一定要先被看成神秘的二维图像操作。

它也可以被看成：

```text
线性秩序
+ 局部窗口
+ 取模位移
+ 同一个 kernel 的重复作用
```

例如一个一维序列：

```text
x[0], x[1], x[2], ..., x[n-1]
```

如果使用周期边界，那么位置可以这样移动：

```text
i + 1 mod n
i - 1 mod n
```

这就形成了一个循环结构。

二维矩阵也可以被展平成一维地址：

```text
index = row * width + col
```

然后用固定偏移找邻居：

```text
left  = index - 1
right = index + 1
up    = index - width
down  = index + width
```

如果加上边界取模：

```text
row = row mod height
col = col mod width
```

就得到一个周期性空间。

所以卷积的核心可以说是：

```text
在一个有秩序的地址空间里，
用固定偏移定义邻域，
再用同一个 kernel 反复测试局部模式。
```

这对 TreeHeap 很重要。

因为它提醒我们：

```text
TreeHeap kernel 不是一上来就必须是复杂语法树。
```

它可以先从更基础的东西开始：

```text
TreeHeap traversal order
+ heap address
+ parent/child offset
+ sibling offset
+ modular or cyclic neighborhood
```

也就是说，TreeHeap 需要先定义自己的“地址代数”。

矩阵里有：

```text
(row, col)
```

序列里有：

```text
i mod n
```

TreeHeap 里可能需要：

```text
path
parent(path)
left(path)
right(path)
sibling(path)
next_dfs(path) mod N
next_bfs(path) mod N
```

这样 kernel 才知道自己在什么空间里移动。

换句话说：

```text
卷积核不是单独成立的。
它依赖一个可移动、可取邻域、可重复作用的地址空间。
```

这也把 SubHeap Kernel Search 拆成两个问题：

```text
1. TreeHeap 地址空间怎么定义？
2. kernel 如何在这个地址空间里做局部匹配？
```

这个拆分很有价值。

因为如果地址空间都没定义好，直接谈复杂的子树匹配，就容易跳太快。

## TreeHeap 里没有规则网格

TreeHeap 不是二维矩阵。

它更像：

```text
树
堆
图
槽位结构
概率容器
```

所以 kernel 不能像 3x3 那样滑动。

TreeHeap 的 kernel 应该长这样：

```text
K = event {
  center: action-like
  slot_1: agent-like
  slot_2: object-like
  slot_3: location-like
}
```

它不是像素模板。

它是一个局部结构模板。

例如：

```text
eat_event {
  agent = ?
  object = ?
}
```

或者：

```text
move_event {
  mover = ?
  source = ?
  target = ?
}
```

这就是 SubHeap Kernel。

## 子堆核搜索怎么定义

可以定义一个操作：

```text
match_subheap(H, K) -> ProbabilityContainer[SubHeap]
```

其中：

```text
H = 整个 TreeHeap
K = 一个局部子堆核
```

输出不是一个硬位置。

输出应该是概率容器：

```text
{
  subheap_12: 0.71
  subheap_4:  0.18
  subheap_29: 0.07
}
```

这表示：

```text
K 最可能匹配 subheap_12，
但 subheap_4 和 subheap_29 也有可能。
```

这和 TreeHeap 的概率容器思想一致：

```text
信息不足时，不要过早 argmax。
```

## 为什么这是推理搜索

考虑三句话：

```text
cat eats fish
fish is eaten by the cat
the cat quickly eats fish
```

表面顺序不同。

但它们共享一个事件结构：

```text
eat_event {
  agent = cat
  object = fish
}
```

如果我们有一个 kernel：

```text
K = action(agent, object)
```

那么它应该在三句话里都找到这个事件。

这就是推理。

因为系统没有只看：

```text
cat 是否在 eats 左边
```

而是在看：

```text
谁在 action 的 agent 槽位？
谁在 object 槽位？
这个局部结构是否等价？
```

这就是拓扑搜索。

## 和普通 attention 有什么不同

Transformer attention 可以让 token 互相看。

但 attention 本身不一定显式告诉你：

```text
这里有一个 action(agent, object) kernel 匹配成功。
```

SubHeap Kernel Search 更像显式结构操作：

```text
给定一个 kernel，
在 TreeHeap 里找对应的子堆。
```

所以它更接近：

```text
结构检索
图模式匹配
局部推理模板匹配
```

它不是替代 attention。

它是给 TreeHeap 代数增加一种可解释操作。

## 这个操作需要处理什么困难

普通卷积很简单，因为图像是规则网格。

TreeHeap 更麻烦。

它至少要处理：

```text
1. 树/图不是规则网格。
2. child 顺序有时重要，有时不重要。
3. slot 顺序可能重要。
4. 有些 child 可以缺省。
5. 主动/被动会改变方向。
6. 中文和英文的表达顺序不同。
7. 匹配应该允许近似，而不是严格相等。
```

所以它更像：

```text
tree kernel
graph kernel
slot kernel
subgraph matching
message passing
```

但我们不要一上来做复杂。

先做最小实验。

## 新 predict：P-ALG02

可以写下：

```text
P-ALG02:
如果 TreeHeap 支持拓扑级推理，
那么同一个 SubHeap Kernel 应该能在不同表面顺序中，
找到等价的局部结构。
```

换句话说：

```text
同一个推理核，
应该能匹配不同说法里的同一个结构。
```

例如：

```text
cat eats fish
fish is eaten by the cat
the cat quickly eats fish
```

都应该激活：

```text
eat_event(agent=cat, object=fish)
```

## E-ALG05: kernel invariance

第一个实验叫：

```text
E-ALG05 kernel invariance
```

测试：

```text
同一个 kernel，
不同表面顺序，
是否找到同一个子堆。
```

例子：

```text
cat eats fish
fish is eaten by the cat
the cat quickly eats fish
```

成功标准：

```text
active/passive/paraphrase variants
rank the same event subheap in top-k
```

失败标准：

```text
只对 token 顺序敏感。
只匹配表面邻近。
主动变被动就失败。
```

## E-ALG06: kernel selectivity

第二个实验叫：

```text
E-ALG06 kernel selectivity
```

测试：

```text
同样的词，角色换了以后，分数应该下降。
```

例如：

```text
cat eats fish
fish eats cat
```

它们词一样，但结构不一样。

我们希望：

```text
score(agent=cat, object=fish)
>
score(agent=fish, object=cat)
```

如果两个分数差不多，说明 kernel 只是看到了词，没有看懂角色。

## E-ALG07: cross-lingual kernel transfer

第三个实验叫：

```text
E-ALG07 cross-lingual kernel transfer
```

测试：

```text
中文里的事件 kernel，
能不能对应到英文里的等价事件子堆。
```

例如：

```text
猫吃鱼
the cat eats fish
```

或者更复杂：

```text
鱼被猫吃了
the fish was eaten by the cat
```

如果 TreeHeap 真的要服务 WMT/S2，这个实验很关键。

因为翻译本质不是词对词。

翻译是：

```text
源语言局部拓扑
映射到
目标语言局部拓扑
```

SubHeap Kernel Search 正好可以测这件事。

## 和前面代数操作的关系

SubHeap Kernel Search 不是孤立的。

它会用到前面几种操作：

```text
project:
  把子堆放到某个参考系里解释。

transpose:
  处理主动/被动、parent/child 方向变化。

energy:
  给候选匹配排序。

probability container:
  保留多个可能匹配。

decompose:
  从 parent 里找可能 children。
```

所以它可以看作 TreeHeap Algebra 的第一个“推理搜索操作”。

## 工程上怎么先做

最小实现不用大模型。

可以先做 controlled toy set：

```text
cat eats fish
fish is eaten by cat
dog chases cat
cat is chased by dog
```

用 spaCy 或手写 proxy 结构先构造小 TreeHeap。

然后定义 kernel：

```text
K_action_object
K_agent_action_object
K_action_location
```

再比较：

```text
gold subheap score
shuffled-role score
surface-nearest score
random subheap score
```

如果连这个都跑不出来，就不应该直接上 WMT。

## 这对项目推进有什么意义

之前我们一直在问：

```text
TreeHeap 是否学出了世界模型？
```

这个问题太大。

现在可以拆小：

```text
TreeHeap 能不能定义一个局部结构核？
这个核能不能在大堆里找等价子堆？
这个匹配能不能跨主动/被动？
这个匹配能不能跨语言？
```

这比直接问“能不能翻译”更可测。

如果 P-ALG02 成立，下一步 S2 会更清楚：

```text
source sentence
-> SubHeap kernels find source reasoning structure
-> project/transpose to target frame
-> target SubHeap kernels recover target structure
-> decoder realizes surface text
```

如果 P-ALG02 失败，那也很清楚：

```text
TreeHeap 还没有 topology search 能力。
不要急着把它接到 WMT decoder。
```

## 当前状态

新增 predict：

```text
P-ALG02: SubHeap kernel search
```

新增实验计划：

```text
E-ALG05 kernel invariance
E-ALG06 kernel selectivity
E-ALG07 cross-lingual kernel transfer
```

计划实现：

```text
ara/s2-translation/src/subheap_kernel_probe.py
ara/s2-translation/evidence/subheap_kernel_probe/
```

状态：

```text
Design phase.
```

还没有 claim。

## 最后一句话

CMul 是点进入背景。

TreeHeap Algebra 是对象之间的数学操作。

SubHeap Kernel Search 则是：

```text
在高维堆里寻找局部推理模式。
```

这可能是 TreeHeap 从“保存信息”走向“结构推理”的关键一步。

> **License: GPLv3**
