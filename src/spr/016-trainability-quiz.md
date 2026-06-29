---
title: "[SPR-016] Trainability Quiz：TreeHeap 进入可学习系统之前的三道小题"
date: 2026-06-21
weight: 16
author: nio (Houming818) & Codex Review
description: "解释为什么在 WMT 之前先做线性回归、XOR、模加法三道 toy 训练题，以及这次实验怎样支撑 TreeHeap encoder/plus/decoder 的下一步设计。"
tags: [SPR, TreeHeap, ARA, Trainability, Experiment]
---

# Trainability Quiz：TreeHeap 进入可学习系统之前的三道小题

这篇文章解释刚跑完的一个小实验：

```text
ara/m0-treeheap-math/src/trainability_quiz.py
```

它对应 ARA 里的一个新 predict：

```text
P-LEARN01: TreeHeap trainability quiz
```

这不是 WMT。
不是翻译实验。
也不是证明 TreeHeap 已经拥有语言理解能力。

它是一道“入门考试”：在真正训练 TreeHeap encoder、plus、decoder 之前，我们先问一个更朴素的问题：

```text
当前这套最小学习框架，能不能学会基础函数？
```

如果连最简单的线性映射、XOR、模加法都学不会，那么直接去跑 WMT 只会得到一堆昂贵但难解释的 loss 曲线。

## 先说结果

实验在 `ni` 上执行，使用的是：

```text
Python 3.10
NumPy
manual gradients
no PyTorch
seed = 20260621
base = 8
```

结果如下：

| 任务 | 初始 loss | 最终 loss | 指标 | 通过 |
|---|---:|---:|---:|---|
| linear_regression | 3.7075966755 | 1.6516923159e-30 | R2 = 1.0 | true |
| xor | 0.9064090912 | 0.0007663465 | accuracy = 1.0 | true |
| modular_addition | 2.4380615125 | 0.0021191076 | accuracy = 1.0 | true |

总结果：

```text
pilot_pass = true
```

用人话说：

```text
这个最小训练系统可以学会：
1. 连续空间里的线性关系
2. 非线性逻辑关系
3. 离散循环空间里的模加法关系
```

这给下一步 TreeHeap 数学工具箱一个基础信号：我们可以开始把 `plus`、`primitive`、`mod fold`、`addressable heap` 设计成可训练模块，而不是只停留在手写 toy 规则。

还有一个更重要的工程含义：

```text
TreeHeap 不是要推翻已有机器学习数学。
TreeHeap 只是我们设计的一种高维可寻址结构。
```

所以我们已经知道有效的常识知识仍然有效。

比如：

```text
线性代数仍然有效
梯度下降仍然有效
非线性激活仍然有效
交叉熵仍然有效
分类任务仍然有效
模运算、群、循环结构仍然有效
```

这件事会让研发轻很多。

因为 TreeHeap 不是从零发明一套完全陌生的数学宇宙。
它更像是在已有机器学习工具箱上，额外引入一个结构对象：

```text
addressable high-dimensional heap object
```

也就是：

```text
机器学习负责学习参数。
TreeHeap 负责提供可寻址、高维、可组合的结构载体。
```

这样一来，我们后面可以继续使用本科到研究生阶段熟悉的数学工具，而不是每一步都陷入“这个东西有没有物理意义”的空转。

## TreeHeap 和一维实数有什么相似处

为了避免 TreeHeap 被理解成一个玄学名词，可以先把它和最熟悉的一维数作比较。

最简单的数学对象是一个实数：

```text
x in R
```

它有几个非常重要的性质。

第一，它可以表示状态：

```text
x = 3.2
```

第二，它可以被操作：

```text
x + 1
2x
x^2
```

第三，它可以被学习系统处理。
比如线性回归学的是：

```text
y = wx + b
```

这里的 `x` 是输入状态，`w` 和 `b` 是学习出来的参数。

TreeHeap 也有类似的一面。
它也是一个状态对象：

```text
H = TreeHeapState
```

它也可以被操作：

```text
plus(H, primitive)
summarize(H)
kernel_search(H, K)
```

它也应该可以被学习系统处理：

```text
H_{t+1} = learned_plus(H_t, p_t; theta)
```

所以从“机器学习能否处理它”的角度看，TreeHeap 并没有脱离常识数学。
它只是把输入从：

```text
一个数 x
```

换成：

```text
一个高维可寻址结构 H
```

这就是 `SPR-016` 为什么先做线性回归、XOR、模加法的原因。
这些 toy 任务确认的是：

```text
学习系统可以从样本中拟合函数。
```

只要 TreeHeap 的操作最后也能写成函数学习问题，那么已有 ML 工具就仍然能进入。

## 增加高维结构以后，多了什么

但是 TreeHeap 和一维实数也有根本差异。

一维实数只有一个自由度：

```text
x = 3.2
```

它没有内部地址。
你不能问：

```text
x 的 root 在哪里？
x 的 left child 是什么？
x 的 cursor 指向哪里？
```

这些问题对实数没有意义。

TreeHeap 不一样。
它不是单个标量，而是一个结构对象：

```text
TreeHeapState = {
  arr: Node[]
  root: arr[0]
  cursor: int
  base: int
  summary: vector
}
```

这带来了几个新增能力。

### 1. 可寻址性

一维实数没有地址。

TreeHeap 有地址：

```text
arr[0], arr[1], arr[2], ...
```

所以 TreeHeap 可以表达：

```text
某个信息写在 root
某个信息写在 left child
某个信息写在 next cursor
```

这让它更像一个数据结构，而不是一个普通数值。

### 2. 局部结构

实数上做局部窗口没有自然意义。

但 TreeHeap 可以定义局部子结构：

```text
root -> (left, right)
```

或者循环窗口：

```text
[arr[i-1], arr[i], arr[i+1]]
```

这就是 TreeHeap kernel search 的来源。
它和卷积里的窗口很像，但窗口滑动的空间不再只是普通一维数组，而是 TreeHeap 的地址结构。

### 3. 多维负载

一维实数只能承载一个标量。

TreeHeap 的每个节点可以承载向量：

```text
node.value in R^d
```

所以它可以同时保存：

```text
语义信息
结构位置
局部上下文
历史写入痕迹
```

这就接近我们之前说的：

```text
球 + 脚 -> 足球
球 + 手 -> 篮球
```

单独一个“球”的向量不够。
它要进入不同背景、不同位置、不同操作关系，才形成不同对象。

### 4. summary 只是投影

一维实数里，数值本身就是对象：

```text
x = 3.2
```

TreeHeap 里，`summary` 不是完整对象。
完整对象是：

```text
arr + cursor + base + root relation + node values
```

`summary` 只是一个投影：

```text
summary = summarize(arr)
```

这点非常关键。

如果把 `summary` 当成整个 TreeHeap，就会把一个高维可寻址结构压扁成普通向量。
那样很多结构信息会丢失。

## 一个对比表

| 维度 | 一维实数 | TreeHeap |
|---|---|---|
| 基本对象 | `x in R` | `H = TreeHeapState` |
| 内部结构 | 无 | 有 `arr/root/cursor/base` |
| 地址 | 无 | 有 `arr[i]` |
| 操作 | `+`, `*`, function | `plus`, `summarize`, `kernel_search` |
| 局部窗口 | 不自然 | 可定义子树或地址窗口 |
| 学习方式 | 学 `f(x; theta)` | 学 `F(H; theta)` |
| 信息负载 | 一个标量 | 多节点、多向量、多关系 |
| 投影 | 数值本身 | `summary` 是投影，不是整体 |

所以 TreeHeap 的定位可以更准确地说成：

```text
它不是比实数更神秘的东西。
它是比实数多了地址、局部结构和高维负载的状态对象。
```

数学常识仍然有效。
但因为对象更复杂，我们需要更多工具：

```text
线性代数处理 node vector
概率论处理候选结构
群/模运算处理循环地址
图和树处理局部关系
机器学习处理可训练算子
```

这就是 TreeHeap 研发工具箱的来源。

## 为什么不直接跑 WMT

WMT 是最终方向，但不是最合适的第一道验证题。

翻译任务里同时混在一起的东西太多：

```text
tokenization
encoder
decoder
alignment
syntax
semantics
training objective
beam search
evaluation metric
data quality
```

如果 WMT loss 降不下来，我们很难判断到底是哪一层错了。

可能是 TreeHeap 的代数设计错了。
可能是 encoder 没学到。
可能是 decoder 不够。
可能是 loss 不适合。
也可能只是数据管线有问题。

所以这次我们先把问题切小：

```text
在不碰真实语言的情况下，
训练系统能不能学会几个确定答案的数学任务？
```

这就是标准机器学习里的 sanity check。
本科做线性回归、逻辑回归、XOR、多分类，不是因为这些任务伟大，而是因为它们能检查训练系统的基本生命体征。

## 三道小题分别检查什么

### 第一题：线性回归

线性回归检查的是：

```text
y = Wx + b
```

模型能不能用梯度下降学到一个线性映射。

这对应 TreeHeap 里的基础问题：

```text
一个 TreeHeap summary 或 node vector，
能不能被稳定映射到另一个目标空间？
```

如果线性回归都失败，那么后面谈世界模型、拓扑弯曲、结构空间就太早了。

这次结果：

```text
final_loss = 1.6516923158620557e-30
R2 = 1.0
```

这说明最小梯度系统对连续线性映射没有问题。

### 第二题：XOR

XOR 是经典非线性任务。

输入输出是：

```text
0 xor 0 = 0
0 xor 1 = 1
1 xor 0 = 1
1 xor 1 = 0
```

它不能被一条直线分开。
所以单层线性模型做不好 XOR，必须有非线性变换。

这道题检查的是：

```text
模型是否能通过隐藏层和非线性激活，
学会一个不是简单线性投影的关系。
```

这和我们之前讨论的“echo 型函数”很相关。

如果一个模型只是把输入原样保存下来，它最多是信息保存器。
但世界模型不只是保存信息。
它还要改变表示空间，让一些关系变近，让另一些关系变远。

XOR 不能证明模型已经有世界模型，但它至少证明：

```text
训练系统能学非线性关系，
不是只能做输入 echo。
```

这次结果：

```text
final_loss = 0.0007663465151399971
accuracy = 1.0
```

### 第三题：模 8 加法

这是这次最贴近 TreeHeap 的题。

任务是学习：

```text
(a + b) mod 8
```

例如：

```text
3 + 4 = 7
5 + 6 = 11
11 mod 8 = 3
所以 (5 + 6) mod 8 = 3
```

为什么它重要？

因为我们前面讨论 TreeHeap 的 `plus` 时，已经把一个关键结构拆成：

```text
plus = successor + information gain + mod fold
```

其中 `mod fold` 就是：

```text
超过 base 后折回前面的地址
```

如果模型连一个小小的 `Z / 8Z` 循环群表都学不会，那就不要急着说 TreeHeap 可以学会地址折叠、循环窗口、卷积式 kernel search。

这次结果：

```text
base = 8
final_loss = 0.0021191076117503013
accuracy = 1.0
```

混淆矩阵是完全对角的：

```text
每个真实类别都被预测成自己，没有串类。
```

这说明模型学会了完整的 base-8 模加法表。

## 这和 TreeHeap 有什么关系

前一篇 `SPR-015` 证明的是手写 toy：

```text
arr[0] 是 root
plus 写入下一个地址
base 前信息量增加
base 后按 mod 折回
kernel 可以在循环地址环上滑动
```

那是一个规则系统。

这篇 `SPR-016` 问的是另一个问题：

```text
这些规则有没有机会被模型学出来？
```

也就是从：

```text
手写 plus(H, primitive)
```

走向：

```text
learned_plus(H, primitive; theta)
```

这里的 `theta` 就是参数。

Transformer 的关键不是矩阵本身，而是参数矩阵能被梯度更新。
学习发生在参数里。

TreeHeap 如果也要变成机器学习系统，而不只是数据结构，就必须有：

```text
encoder theta_e
plus theta_p
decoder theta_d
loss
gradient
update
```

这次 trainability quiz 只是确认：

```text
最小训练管线可以通过梯度学函数。
```

它还没有证明：

```text
TreeHeap 的真实 plus 已经学出来。
```

但它允许我们进入下一步。

这一点也修正了 TreeHeap 的定位。

TreeHeap 本身不是一个会自动产生知识的魔法容器。
它是一种结构设计：

```text
把向量、地址、root、cursor、base、summary 组织成可操作对象。
```

真正的知识仍然要通过学习进入参数。
也就是：

```text
数据
-> loss
-> gradient
-> parameter update
-> learned operator
```

Transformer 是这样，TreeHeap 也应该是这样。

区别只在于：

```text
Transformer 主要学习矩阵上的序列映射。
TreeHeap 希望学习高维堆对象上的结构操作。
```

所以这次实验还证明了一件朴素但重要的事：

```text
我们不用放弃已有 ML 常识。
我们只是把这些常识接到 TreeHeap 结构上。
```

## 为什么使用 NumPy 手写梯度

这次没有用 PyTorch。

原因很简单：

```text
ni 上当前 Python 环境有 NumPy，但没有 torch。
```

所以实验使用手写反向传播。

这反而有一个好处：所有东西都很透明。

我们没有把问题交给框架魔法。
每个任务都能看见：

```text
forward
loss
gradient
parameter update
```

对于 M0 数学工具箱来说，这种透明性比一开始追求大模型训练更重要。

## 这次实验证明了什么

它证明的是一个很窄的命题：

```text
在当前最小训练代码里，
小型可训练模块可以学会线性映射、XOR、base-8 模加法。
```

所以我们可以合理继续设计：

```text
trainable TreeHeap encoder
trainable TreeHeap plus
trainable TreeHeap decoder
```

尤其是 `plus`。

因为 `plus` 不是普通向量加法。
它更像：

```text
在一个可寻址 TreeHeap 结构里，
把 primitive 写入下一个位置，
更新 summary，
并在 base 满后发生 mod fold。
```

这次的模加法任务说明：

```text
小模型至少可以学会离散循环结构。
```

这对 TreeHeap 的地址环、循环窗口和 kernel search 是正向证据。

## 这次没有证明什么

它没有证明：

```text
TreeHeap 已经会翻译
TreeHeap 已经拥有世界模型
TreeHeap 已经学会真实语言语义
TreeHeap checkpoint 是可靠的
CMul 一定能形成拓扑扭曲
```

这些都还没有。

这次只是一个入口实验。

如果把研发路线比作爬楼，这次不是到了顶楼。
它只是确认：

```text
楼梯是实的，不是一张画。
```

## 下一步怎么走

下一步我建议做 `P-LEARN02`：

```text
Trainable TreeHeap Plus
```

目标不是语言。
还是 toy。

输入：

```text
H_t
primitive p_t
```

输出：

```text
H_{t+1}
```

其中 `H_t` 必须包含可寻址结构：

```text
arr
cursor
base
summary
```

训练目标可以分成三项：

```text
1. target address loss
   模型要知道下一个写入地址在哪里

2. reconstruction loss
   模型要能重建更新后的 arr 或 summary

3. mod fold loss
   base 满后，模型要学会折回 arr[0], arr[1], ...
```

如果 `P-LEARN02` 成立，我们才进入：

```text
TreeHeap-object echo
```

也就是让模型不仅输出向量，而是输出一个仍然可读、可写、可比较的 TreeHeap 对象。

再之后才是：

```text
structure invariant
S2 translation
WMT
```

## ARA 记录在哪里

这次实验的 ARA 目录是：

```text
ara/m0-treeheap-math/
```

公开镜像同步到：

```text
https://github.com/houming818/sametime/tree/main/ara/m0-treeheap-math
```

关键 evidence：

```text
evidence/trainability_quiz/summary.json
evidence/trainability_quiz/README.md
```

对应代码：

```text
src/trainability_quiz.py
```

## 一句话

`SPR-015` 证明了一个手写 TreeHeap toy 可以拥有 `plus + mod fold + kernel search`。

`SPR-016` 证明了最小训练系统可以学会基础连续映射、非线性逻辑和模加法。

所以现在的路线不是：

```text
直接拿 TreeHeap 去碰 WMT。
```

而是：

```text
先把 TreeHeap 的数学工具箱做成可学习对象，
再让语言任务站在这个工具箱上。
```

> **License: GPLv3**
