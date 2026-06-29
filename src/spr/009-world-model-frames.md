---
title: "[SPR-009] 世界模型与参考系：TreeHeap 术语统一"
date: 2026-06-17
weight: 9
author: nio (Houming818) & Codex Review
description: "统一 TreeHeap 的世界模型、参与乘积、参考系、latent slot 和概率容器术语，为后续 ARA predict 做准备。"
tags: [SPR, TreeHeap, WorldModel, ARA, SemanticFrame]
---

# 世界模型与参考系：TreeHeap 术语统一

这篇文章先不急着做新实验。它的目标是统一语言。

因为如果我们继续混用：

```text
背景场
path field
概率意识场
world topology
context field
```

讨论会很快发散。后面统一叫：

```text
世界模型（World Model）
```

## 为什么要叫世界模型

TreeHeap 里真正想表达的不是“一个词的孤立含义”。

比如：

```text
ball
```

它可以进入很多世界：

```text
football
basketball
baseball
volleyball
```

这些词都包含 `ball`，但它们不是同一个东西。

差别来自：

```text
脚
手
球场
球网
规则
动作
人与物的关系
```

所以：

```text
球 + 脚 = 足球
球 + 手 = 篮球
```

不是简单的词向量加法，而是在说：

```text
同一个实体进入了不同的世界模型。
```

`ball` 是对象，`foot/hand/field/court/rule` 是它参与的世界关系。

## 术语表

先给一张沟通表。

| 术语 | 英文名 | 含义 | 在 TreeHeap 里的位置 | 例子 |
|---|---|---|---|---|
| 词法基底 | Lexical Base / L0 | token 自己的基础语义向量 | `L0[token]` | `ball`, `foot`, `hand` |
| 世界模型 | World Model | token 所处的关系、场景、规则、拓扑背景 | path nodes / context / latent frame | “脚能踢球”、“手能投球”、“球场规则” |
| 参与乘积 | Participation Product | 让 L0 进入世界模型，形成带背景的状态 | `CMul(L0, WorldModel)` | `ball × sport-frame` |
| 入世状态 | Token-in-World State | token 参与世界模型后的状态 | CMul pre-merge 或 post-merge | “足球语境里的 ball” |
| 读出层 | Readout / Merge | 把入世状态投影成下游可用向量 | `t_merge` | 128D final vector |
| 参考系 | Frame of Reference | 解释向量方向的局部坐标系 | latent axes / frame basis | sport frame, body-part frame |
| 结构槽位 | Latent Slot | 无监督或弱监督发现的结构位置，不等于主谓宾 | Fold / role-slot layer | `slot_3`, `slot_12` |
| 差分方向 | Relation Delta | 两个概念的差分，表示关系变化 | vector difference | `football - ball` |
| 投影解释 | Frame Projection | 把差分投到某个参考系，看它指向什么 | `delta · frame_axis` | 是否更接近 `foot/kick` |
| 概率容器 | Probability Container | 不急着 argmax，保留多个候选状态 | L2/L3 collapse 前 | parent top-k, slot top-k |
| 坍缩 | Collapse | 从多个可能状态选择或收敛到一个状态 | 下游决策阶段 | 从 top-3 parent 选一个 |
| 证据门 | Evidence Gate | 提前写好的通过/失败标准 | ARA `/logic` | rank、probe、top-k |

口语版：

```text
L0 是“词自己”。
世界模型是“这个词所在的世界规则”。
参与乘积是“词进入这个世界”。
入世状态是“词进入世界后的样子”。
参考系是“我们用什么坐标解释它”。
slot 是“结构自己长出来的位置”。
概率容器是“先别拍死，保留多个可能”。
坍缩是“信息足够后再做决定”。
```

## 一个例子：足球和篮球

假设我们有：

```text
ball
football
basketball
foot
hand
kick
throw
field
court
goal
basket
```

我们不想只问：

```text
football 和 basketball 像不像？
```

我们更想问：

```text
football 相对 ball 多出来的关系是什么？
basketball 相对 ball 多出来的关系是什么？
```

也就是：

```text
delta_football = football - ball
delta_basketball = basketball - ball
```

如果 TreeHeap 的世界模型有效，那么在某个运动参考系里：

```text
delta_football
```

应该更接近：

```text
foot
kick
field
goal
```

而：

```text
delta_basketball
```

应该更接近：

```text
hand
throw
court
basket
```

这就叫：

```text
参考系解释。
```

没有参考系，向量差分只是一些数字。  
有参考系，差分才变成“这个变化指向哪种世界关系”。

## 为什么不能只看 raw cosine

前面的 `t_merge` 诊断告诉我们一件事：

```text
raw cosine 可能会误导。
```

旧 checkpoint 的 final tree output 看起来高度相似：

```text
tree output raw cosine mean ≈ 0.985
```

但减去公共均值之后：

```text
centered cosine mean ≈ 0
```

这说明：

```text
向量里有一个很强的公共世界背景方向。
```

如果直接拿 raw cosine 判断，就会误以为所有 token 都一样。

所以后面的世界模型实验应该比较：

```text
L0
CMul pre-merge
merge_no_bias
centered tree
raw tree
```

不要只看 raw tree。

## Latent Slot 不是主谓宾

还有一个必须纠正的点。

前面为了讲清楚，我们经常举：

```text
SUBJECT
ROOT
OBJECT
```

但这只是临时解释用的 proxy。

TreeHeap 最终不应该直接规定：

```text
slot_0 = SUBJECT
slot_1 = OBJECT
```

更合理的是：

```text
先从数据里无监督或弱监督学出 latent slots。
然后再观察这些 slot 和人类语法标签有什么关系。
```

也就是说：

```text
slot_3 可能经常表现得像主语。
slot_8 可能经常表现得像宾语。
slot_12 可能是某种修饰位置。
```

但这些名字应该是事后解释，不是事前规定。

这点很重要。否则我们会把传统语法体系偷偷塞进 TreeHeap，最后得到的不是结构涌现，而是语法标签蒸馏。

## 概率容器的位置

世界模型不是每一步都要立刻做决定。

比如一个短语可能有多个合理挂接：

```text
Parent A: 0.61
Parent B: 0.27
Parent C: 0.12
```

旧方式会直接：

```text
argmax -> Parent A
```

但 TreeHeap 的方向应该是：

```text
先保留这个分布。
```

也就是：

```text
ParentContainer {
  A: 0.61
  B: 0.27
  C: 0.12
}
```

等到后面有更大的世界上下文，比如翻译、生成、执行器，再坍缩。

这和 L0 的多义叠加是同一个思想：

```text
信息不足时，不要过早拍死。
```

## 一句话定义

当前可以先这样定义 TreeHeap：

```text
TreeHeap = L0 词法基底参与世界模型，
生成可被参考系解释、
可延迟坍缩的结构状态。
```

展开成管线：

```text
L0[token]
  -> World Model / Frame
  -> Participation Product
  -> Token-in-World State
  -> Latent Slots / Probability Containers
  -> Collapse when enough context exists
```

## 接下来怎么提 predict

这篇先统一术语，下一篇再正式写 ARA `/logic` 里的 predict。

但方向已经很明确：

```text
P-FRAME01:
如果 TreeHeap 的世界模型携带真实拓扑信息，
那么复合概念的差分方向，
应该能在某些局部参考系里投影到可解释关系。
```

例子：

```text
football - ball -> foot / kick / field / goal
basketball - ball -> hand / throw / court / basket
baseball - ball -> bat / field
volleyball - ball -> hand / net
```

这个 predict 还不能算 evidence。  
它只是下一轮实验的逻辑起点。

下一步要把它写成：

```text
/logic/predicts.md
```

再设计：

```text
/src/frame_probe.py
```

最后把结果放进：

```text
/evidence/frame_probe/
```

这才符合 ARA。

> **License: GPLv3**
