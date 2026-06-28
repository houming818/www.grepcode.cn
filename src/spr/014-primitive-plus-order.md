---
title: "[SPR-014] 基元与 plus：TreeHeap 有序性的来源"
date: 2026-06-18
weight: 14
author: nio (Houming818) & Codex Review
description: "把 TreeHeap 的卷积问题继续下压：先寻找语义空间里的基元、plus 算子和由 plus 生成的有序性。"
tags: [SPR, TreeHeap, Algebra, Primitive, Order]
---

# 基元与 plus：TreeHeap 有序性的来源

这篇先不跑实验。

它先把一个更底层的想法固定下来：

```text
TreeHeap 的卷积问题，
可能不是先找 kernel，
而是先找语义空间里的基元和 plus。
```

这个想法来自整数系统。

整数的有序性不是随便排出来的。

它有一个非常小的核心：

```text
基元：0 或 1
算子：plus / successor
顺序：n -> n + 1
闭包：n + 1 仍然是整数
取模：n + base 折回 n
```

如果 TreeHeap 也想形成自然的有序地址空间，那么我们也要问：

```text
语义空间里的 1 是什么？
语义空间里的 plus 是什么？
TreeHeap 的 n+1 是怎么生成的？
```

## 为什么这比卷积更底层

上一篇文章说，卷积可以理解成：

```text
线性秩序
+ 局部窗口
+ 取模位移
+ 同一个 kernel 的重复作用
```

但这里还有一个没回答的问题：

```text
线性秩序从哪里来？
```

如果我们只是人为给节点编号：

```text
node_0, node_1, node_2, ...
```

那这个顺序可能只是外部编号。

它不一定是 TreeHeap 自己的结构。

更自然的做法是：

```text
node_{n+1} = plus(node_n, primitive)
```

也就是说：

```text
有序性由 plus 生成。
```

这就像整数：

```text
1 = 0 + 1
2 = 1 + 1
3 = 2 + 1
```

而不是先把整数排好，再事后说它有顺序。

## 对应关系

可以先做一个对照表：

| 整数系统 | TreeHeap / 语义空间 |
|---|---|
| `0` | origin / root primitive |
| `1` | 最小语义基元 |
| `n + 1` | next semantic state / next node |
| `plus(a, b)` | 语义组合或结构推进算子 |
| `<` | repeated plus 生成的顺序 |
| `mod base` | 有限 TreeHeap 地址环 |
| convolution | 在这个地址环上滑动 kernel |

所以真正要找的是：

```text
primitive
plus
ordered orbit
```

其中 orbit 是：

```text
x0
x1 = plus(x0, p)
x2 = plus(x1, p)
...
x_base ~= x0
```

如果这个成立，TreeHeap 就不仅是有编号。

它有了一个内部生成的顺序。

## 什么是基元

基元不是人工语法标签。

它不是：

```text
SUBJECT
OBJECT
VERB
```

至少在 M0/M1 阶段不能这样定义。

基元应该先被看成：

```text
能让状态发生最小可重复变化的元素。
```

在整数里，这个元素是：

```text
1
```

在 TreeHeap 里，它可能是：

```text
一个最小路径步长
一个最小 slot shift
一个最小语义方向
一个局部结构生成元
一个 learned primitive basis
```

我们不应该一开始就假设它是什么。

应该设计实验去找：

```text
哪个 p 可以让 plus(x, p) 稳定地产生 next？
```

## plus 可能是什么

候选 plus 可以有很多种：

```text
plus(v, p) = v + p
plus(v, p) = normalize(v + p)
plus(v, p) = CMul(v, p)
plus(H, p) = compose(H, p)
plus(path, step) = path_shift(path, step)
plus(H, p) = learned_operator(H, p)
```

这些都只是候选。

不能先说哪一个一定对。

ARA 里应该把它们当作实验变量。

真正的判断标准是：

```text
它能不能生成稳定有序轨道？
```

## 有序轨道

如果找到了一个 primitive `p` 和一个 plus，那么就可以生成：

```text
x0 = origin
x1 = plus(x0, p)
x2 = plus(x1, p)
x3 = plus(x2, p)
```

这是一条轨道。

我们希望它满足：

```text
相邻可预测
远邻可区分
重复作用不发散
到达 base 后可以回环
```

也就是：

```text
nearest(plus(x_n, p)) = x_{n+1}
distance(x_n, x_{n+1}) < distance(x_n, x_{n+3})
distance(x_base, x_0) small
```

这才是 TreeHeap 的有序性。

不是外部排出来的。

而是由内部算子生成的。

## 取模怎么出现

如果轨道长度是 `base`：

```text
x0, x1, x2, ..., x_{base-1}
```

那么取模就是：

```text
x_{n + base} ~= x_n
```

也就是：

```text
idx(x) in Z_base
```

这时 TreeHeap 地址空间变成：

```text
Z / base Z
```

也就是一个有限循环地址环。

卷积 kernel 才能滑动：

```text
window(i) = [
  x_{i-1 mod base},
  x_i,
  x_{i+1 mod base}
]
```

这就是：

```text
基元 + plus
生成 order
order + mod
生成 cyclic address
cyclic address + kernel
生成卷积
```

## 这对 TreeHeap 很重要

之前我们说：

```text
TreeHeap 是有序树。
```

但这句话还不够。

还要追问：

```text
这个有序性是外部编号给的，
还是 TreeHeap 自己生成的？
```

如果只是外部编号，那它只是工程索引。

如果有：

```text
x_{n+1} = plus(x_n, p)
```

那它就是结构规律。

这两者差别很大。

前者只能帮我们扫描。

后者可能帮我们推理。

## 新 predict：P-MATH02

可以把下一步写成：

```text
P-MATH02: Semantic primitive and plus operator
```

预判：

```text
如果 TreeHeap 空间存在可用于结构生成的有序性，
那么应该存在某种 primitive p 和 plus 算子，
使 repeated plus 生成稳定、有序、可取模的语义轨道。
```

形式：

```text
x_0 = origin
x_{n+1} = plus(x_n, p)
x_{n+base} ~= x_n
```

## toy 实验应该怎么做

先不要碰语言。

还是 M0 纯数学 toy。

设：

```text
base = 8
origin = x0
primitive = p
```

生成：

```text
x1 = plus(x0, p)
x2 = plus(x1, p)
...
x8 ~= x0
```

测这些指标：

```text
successor_accuracy:
  nearest(plus(x_n, p)) == x_{n+1}

cycle_error:
  distance(x_base, x_0)

order_margin:
  distance(x_n, x_{n+1}) < distance(x_n, x_{n+3})

closure:
  plus(x_n, p) still in TreeHeap space

kernel:
  [x_{i-1}, x_i, x_{i+1}] mod base can be matched
```

如果这些都不成立，就不要急着讨论语言。

因为连：

```text
1, 2, 3, 4
```

这样的内部顺序都还没长出来。

## 语言里的直觉

等数学 toy 成立以后，语言才进来。

那时候可以问：

```text
球 + 脚 -> 足球
球 + 手 -> 篮球
动作 + 施事 -> 事件
事件 + 时间 -> 时态
事件 + 地点 -> 场景
```

但这些不能一开始就当作人工标签。

更好的路径是：

```text
先无监督找 primitive basis
再看这些 basis 是否对应可解释概念
```

也就是说：

```text
先找数学上的 1。
再看这个 1 在语言里像不像“脚”“手”“时间”“地点”。
```

## 对当前路线的影响

这会把路线再往前插一层：

```text
M0: TreeHeap object algebra
M0-P2: primitive + plus + ordered orbit
M1: approximate inverse / learned plus
M2: TreeHeap-object echo
M3: structure invariant
S2: translation
```

也就是说，SubHeap Kernel Search 之前，还要先问：

```text
kernel 在哪个有序空间里移动？
这个有序空间是不是由 plus 生成？
```

如果不是，它可能只是工程扫描。

如果是，它才更像 TreeHeap 自己的代数。

## 当前状态

这篇是理论整理。

还没有实验 claim。

已经可以进入 ARA：

```text
ara/m0-treeheap-math/logic/predicts.md
```

下一步实验文件可以叫：

```text
ara/m0-treeheap-math/src/primitive_plus_probe.py
ara/m0-treeheap-math/evidence/primitive_plus_probe/
```

先用合成 toy 找：

```text
primitive
plus
ordered orbit
mod base
cyclic kernel
```

等这个成立，再往 Echo 和 S2 推。

> **License: GPLv3**
