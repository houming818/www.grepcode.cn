---
title: "[SPR-011] TreeHeap 代数：先做数学闭包，再谈语言推理"
date: 2026-06-18
weight: 11
author: nio (Houming818) & Codex Review
description: "把 TreeHeap 从一个乘法向量层推进成代数系统：定义闭包、转置、逆树堆、投影、能量和概率容器。"
tags: [SPR, TreeHeap, Algebra, ARA, WorldModel]
---

# TreeHeap 代数：先做数学闭包，再谈语言推理

前一篇守夜训练给了一个重要教训：

```text
只靠 local BPE context objective，
不能证明 TreeHeap 学出了世界模型。
```

这不只是 loss 设计问题。
更深一层的问题是：

```text
TreeHeap 现在还不像一个完整的数学系统。
```

目前我们实现得最多的是：

```text
L0(token) x path/world -> CMul -> t_merge
```

这相当于只有一个核心参与乘积。

它可以保存信息，可以调制方向，也可以让 token 带上 path 背景。
但它不一定能完成：

```text
转置
求逆
分解
投影
组合
能量排序
概率坍缩
```

如果这些操作都没有定义，TreeHeap 就还不是一个“堆数据结构”。
它只是一个带名字的向量变换层。

所以这篇文章先不谈 WMT，也不谈 BLEU。
我们先退一步：

> TreeHeap 能不能先成为一个可计算的代数系统？

## 为什么先做代数

语言推理是上层问题。

比如翻译：

```text
中文结构 -> 英文结构 -> 英文表面句子
```

这里面当然有语义、语法、文化和世界知识。
但在 TreeHeap 视角下，它首先需要一些更基本的能力：

```text
一个结构能不能合成？
合成后能不能分解？
一条关系能不能反过来看？
一个对象能不能投影到某个参考系？
投影后能不能回来？
一组候选结构能不能排序？
不确定时能不能先保留概率？
```

这些不是语言专属问题。
这些是数学操作问题。

如果这些操作不稳定，那么后面说“世界模型”“推理”“翻译”都太早。

这就是这篇文章的核心判断：

```text
先建立 TreeHeap Algebra。
再把语言推理放到这个代数系统上。
```

## 什么叫数学闭包

本科计算机里经常会见到“闭包”这个词。

例如整数加法：

```text
整数 + 整数 = 整数
```

所以整数对加法是封闭的。

但：

```text
整数 / 整数 = 不一定是整数
```

例如：

```text
1 / 2 = 0.5
```

所以整数对除法不封闭。

放到 TreeHeap 里，我们想要的是：

```text
TreeHeap object op TreeHeap object -> TreeHeap object
```

也就是说：

```text
两个 TreeHeap 对象做完操作，
结果还应该是一个 TreeHeap 对象。
```

如果每次操作完都跑出空间，只能交给神经网络硬猜，那数学结构就没有帮上忙。

## TreeHeap 对象是什么

先定义一个最小对象：

```text
H = (v, p, s, q)
```

其中：

```text
v: semantic/world vector
p: heap path or structural coordinate
s: latent slot distribution
q: probability mass / confidence
```

口语一点说：

```text
v 是“它是什么”
p 是“它在堆里的位置”
s 是“它像在哪些潜在槽位上”
q 是“我们对它有多确定”
```

这比一个裸向量多一点结构。

TreeHeap 不应该只保存：

```text
128D vector
```

它应该保存：

```text
向量 + 结构坐标 + 槽位分布 + 概率质量
```

这才像一个高维堆对象。

## 操作一：compose 合成

compose 是：

```text
compose(H1, H2, ..., Hn) -> H_parent
```

意思是：

```text
多个 child heap objects 合成一个 parent heap object。
```

例如：

```text
foot + ball -> football
```

或者在句子结构里：

```text
kick + ball + goal -> event/state
```

关键不是简单加法。
compose 应该同时更新：

```text
v: 世界状态变了
p: 结构位置变了
s: 槽位分布变了
q: 置信度变了
```

如果 compose 只是：

```text
v_parent = v1 + v2
```

那它太弱。

## 操作二：decompose 分解，也就是逆树堆

如果有合成，就自然会问有没有逆操作。

```text
compose(children) -> parent
```

反过来：

```text
decompose(parent) -> children
```

这就是“逆树堆”的直觉。

但是语言里一般没有唯一逆。

例如：

```text
football
```

可以拆成：

```text
foot + ball
sport + ball
game + object
```

所以 decompose 不应该返回一个硬答案。

它应该返回概率容器：

```text
{
  foot + ball:    0.52
  sport + ball:   0.31
  game + object:  0.17
}
```

这和之前说的 Probability Container 是同一个思想。

逆树堆不是普通函数逆。
更准确地说，它是：

```text
probabilistic inverse
```

## 操作三：transpose 转置

矩阵里有转置：

```text
A -> A^T
```

TreeHeap 里也需要类似操作，但含义不是把二维表格翻过来。

TreeHeap 的转置更像：

```text
关系方向反转
```

例如：

```text
edge(parent, child, role)
```

转置后：

```text
edge(child, parent, inverse_role)
```

它应该满足一个基本性质：

```text
transpose(transpose(edge)) ≈ edge
```

也就是转两次应该差不多回来。

为什么这对翻译重要？

因为不同语言经常从不同方向表达同一关系。

例如中文和英文的修饰、介词、话题结构，方向可能不一样。
如果 TreeHeap 没有 transpose，就很难用数学操作表达：

```text
同一个关系，换一个方向读。
```

## 操作四：project 投影到参考系

我们一直说世界模型和参考系。

project 就是：

```text
project(H, frame) -> H_frame
```

例如：

```text
project(ball, sport_frame)
```

和：

```text
project(ball, kitchen_frame)
```

应该不一样。

同一个对象进入不同参考系，解释方向不同。

这对应前面的例子：

```text
football - ball -> foot / kick / field / goal
basketball - ball -> hand / throw / court / basket
```

如果没有 project，向量差分只是数字。
有了 project，差分才变成：

```text
这个变化在什么世界里被解释？
```

## 操作五：unproject 反投影

如果能投影，就要问能不能回来：

```text
unproject(project(H, frame), frame) ≈ H
```

这叫 projection roundtrip。

如果做不到，说明投影丢了太多信息。

但也不能完全不变。
如果 project/unproject 只是 identity echo，那也没意义。

所以它要同时满足两个条件：

```text
1. roundtrip 后能大致回到原对象。
2. 在 frame 内部确实改变了可解释方向。
```

这就是难点。

## 操作六：energy 能量

energy 是：

```text
energy(H) -> scalar
```

它给 TreeHeap 对象打一个一致性分数。

低能量表示：

```text
这个对象更像一个合法结构。
```

比如：

```text
compose(foot, ball)
```

应该比：

```text
compose(engine, snow)
```

在 sport-ball frame 下能量更低。

但注意，energy 不是“真理”。
它只是排序工具。

## 最小 predict：P-ALG01

现在可以写一个新的 predict：

```text
P-ALG01:
如果 TreeHeap 是可用的数学底座，
那么 compose、decompose、transpose、project、unproject、energy
这些操作应该在 TreeHeap 对象空间内近似封闭。
```

也就是说：

```text
操作前是 TreeHeap 对象。
操作后仍然是 TreeHeap 对象。
```

而不是变成一堆无法解释的向量碎片。

## 怎么实验

先不要跑 WMT。

先跑四个数学实验。

### E-ALG01: compose/decompose 往返

```text
children -> compose -> parent -> decompose -> children'
```

看：

```text
children' 能不能在 top-k 里找回原 children。
```

失败标准：

```text
找回率不超过 random / nearest baseline。
```

### E-ALG02: transpose 两次回来

```text
edge -> transpose -> transpose -> edge'
```

看：

```text
edge' 是否接近原 edge。
```

失败标准：

```text
转置两次还不如不转。
```

### E-ALG03: project/unproject 往返

```text
H -> project(frame) -> unproject(frame) -> H'
```

看：

```text
H' 是否接近 H。
```

同时还要看：

```text
project 后是否真的提升 frame 内 relation ranking。
```

否则就是 echo。

### E-ALG04: 闭包压力测试

反复做：

```text
compose
project
transpose
decompose
normalize
```

看有没有：

```text
norm explosion
global cosine collapse
energy drift
probability mass invalid
```

如果反复操作几轮就炸掉，那 TreeHeap 还不是稳定代数。

## 和 WMT 的关系

这一步看起来远离翻译，其实是在给翻译铺地基。

如果 TreeHeap Algebra 成立，S2 翻译可以变成：

```text
source TreeHeap
-> transpose / project
-> target frame TreeHeap
-> decompose / collapse
-> target sentence
```

也就是：

```text
用数学操作迁移结构，
再用模型生成表面语言。
```

否则就只能回到：

```text
source tokens -> black-box decoder -> target tokens
```

那 TreeHeap 的意义就不明显。

## 当前架构判断

现在可以把之前的判断整理成三句话：

```text
Echo preserves information.
CMul carries participation.
World model requires algebraic topology operations.
```

中文就是：

```text
Echo 保存信息。
CMul 携带参与关系。
世界模型需要代数拓扑操作。
```

所以接下来不是继续加大 local context 训练。

下一步是：

```text
先设计 TreeHeap Algebra。
再训练模型学习这个代数里的未知映射。
```

## ARA 状态

新增 predict：

```text
P-ALG01
```

新增设计文档：

```text
ara/s2-translation/logic/solution/treeheap_algebra.md
```

下一步 planned evidence：

```text
ara/s2-translation/src/treeheap_algebra_probe.py
ara/s2-translation/evidence/treeheap_algebra_probe/
```

状态：

```text
Design phase.
```

还没有 claim。

## 最后一句话

TreeHeap 不应该只是一个乘法层。

它应该先成为一个能做：

```text
合成
分解
转置
投影
反投影
能量排序
概率保留
```

的高维堆代数系统。

语言推理不是第一层。

语言推理是这个代数系统上的应用。

> **License: GPLv3**
