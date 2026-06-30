---
title: "[SPR-037] 可控流形：怎样把 TreeHeap 从一团乱调到可用结构"
date: 2026-06-30
weight: 37
author: nio (Houming818) & Codex Review
description: "SPR-037 把 TreeHeap fold 从纯理论问题推进到产品调试问题：如果 kernel 有可调控制量，输出结构是否会从乱态沿着一个可测量的面走向稳定块？toy proof 显示低控制 F1 0.0828，最佳 F1 0.8148，对角线增益 0.7319。"
tags: [SPR, TreeHeap, ARA, Kernel, Fold, Manifold]
---

# 可控流形：怎样把 TreeHeap 从一团乱调到可用结构

你刚才提出的观点，我认为非常关键：

```text
现在的 claim 应该是一个可控流形。
```

这句话解决了一个一直卡住我们的问题。

之前我们总是在两个层面之间跳：

```text
数学层：plus / diff / compose / decompose / kernel
产品层：能不能生成句子、能不能翻译、能不能像 Transformer 一样工作
```

中间缺一层。

这一层就是：

```text
控制变量 -> 结构变化 -> 产品功能涌现
```

也就是说，不要一上来就问：

```text
TreeHeap 能不能直接生成正确句子？
```

而是先问：

```text
当我调整 kernel 的细节时，
输出结构会不会从一团乱，
逐步走向更稳定、更像产品可用结构的状态？
```

如果这个过程可控，我们就可以在控制过程中学习规律。
然后再修补数学 kernel。

这就是 SPR-037。

## 什么叫“可控流形”

这里的“流形”不要先理解成高等几何里很复杂的对象。

可以先理解成一张可观察的调参地图：

```text
横轴：relation_weight
纵轴：order_weight
高度：fold 结构质量
```

比如：

```text
relation_weight = 0
order_weight    = 0
```

kernel 什么都不相信，输出就接近随机。

再比如：

```text
relation_weight = 2
order_weight    = 2
```

kernel 既相信词之间的关系场，也相信线性邻近，输出结构应该更稳定。

于是我们得到一张面：

```text
controls -> fold quality
```

这张面就是当前意义上的“可控流形”。

## Houming818 的补充：梯度不一定只改参数

下面这一段是 Houming818 提出的补充。

我把它整理成工程语言，但这个想法的责任归属要说清楚：

```text
观点来源：Houming818
整理解释：Codex Review
当前状态：理论假设，尚未被 SPR-037 的 toy proof 直接证明
```

你提出的问题是：

```text
既然说可控流形，
那梯度信息从哪里来？

梯度是否一定要表现为普通神经网络那样的参数更新？
```

这非常关键。

因为如果 TreeHeap 只是：

```text
θ <- θ - η ∇θ L
```

也就是只更新 kernel 参数，那它看起来和普通 MLP / Transformer 的训练方式太接近。

但你提出了另一种可能：

```text
梯度也可以调整 heap 自身的平衡态。
```

比如一个很小的 heap state：

```text
[2.0, 1.0, 3.0]
```

梯度来了以后，不一定是修改某个外部参数。

它也可能让当前 heap 变得更平衡：

```text
[2.0, 1.0, 3.0]
-> [2.0, 1.5, 2.5]
-> [2.0, 1.8, 2.2]
```

这不是：

```text
改函数参数
```

而更像：

```text
调 heap state 的平衡性
```

## 两种梯度：参数梯度与状态梯度

因此 TreeHeap 里至少要区分两类梯度。

第一类是普通参数梯度：

```text
θ <- θ - η ∇θ L
```

这里更新的是：

```text
kernel 参数
compose 参数
read 参数
write 参数
relation field 参数
```

这和普通深度学习类似。

第二类是 Houming818 提出的 heap 平衡梯度：

```text
H <- H - η ∇H E(H)
```

这里更新的不是外部函数参数，而是当前 heap state：

```text
arr[1]
arr[2]
arr[3]
...
```

每个 `arr[i]` 可以是一个向量。

它们可以在能量函数的驱动下移动。

## 一个最小例子

假设我们定义左右平衡能量：

```text
E_balance = (left - right)^2
```

当前状态是：

```text
root  = 2.0
left  = 1.0
right = 3.0
```

左右差很大：

```text
left - right = -2.0
```

能量高。

如果只对 heap state 做梯度下降，系统会推动：

```text
left 变大
right 变小
```

于是得到：

```text
[2.0, 1.0, 3.0]
-> [2.0, 1.5, 2.5]
```

这个过程更像物理里的松弛：

```text
系统沿能量下降方向进入更稳定状态。
```

它不是先知道一个“目标 heap”，然后对目标 heap 求导。

它只需要知道：

```text
当前 heap 的能量高不高。
```

## 这是否绕开了“目标 heap 可导”的问题

部分绕开了。

更准确地说：

```text
不需要目标 heap 本身可导。
```

但仍然需要一个可计算、可微分的能量函数：

```text
E(H)
```

例如：

```text
E_balance(H)              左右是否平衡
E_parent_child(H)         父子是否一致
E_relation_match(H, W)    heap 是否贴合世界/关系场
E_entropy(P)              概率容器是否过早或过晚坍缩
E_path_smooth(H)          路径上的状态是否连续
```

总能量可以写成：

```text
E_total(H)
  = E_balance(H)
  + E_parent_child(H)
  + E_relation_match(H, W)
  + E_entropy(P)
```

然后做：

```text
H <- H - η ∇H E_total(H)
```

这就把可导要求从：

```text
目标结构必须可导
```

转移成：

```text
当前状态的能量函数必须可导
```

这个差别很大。

## 这对 TreeHeap 为什么重要

如果这个方向成立，TreeHeap 的学习就不只有一种：

```text
参数学习：让 kernel 函数变强
状态松弛：让 heap 自身进入平衡态
```

用一句话说：

```text
普通神经网络更像改函数。
TreeHeap 还可能改结构状态。
```

这会让“可控流形”变得更像一个真实动力系统：

```text
kernel 参数决定能量地形
heap state 在能量地形上滑动
概率容器在合适时刻坍缩
最后形成稳定结构
```

也就是说，SPR-037 现在测的是：

```text
手动控制变量能不能改变 fold 质量。
```

Houming818 的补充指向下一层：

```text
梯度能不能不是只改控制变量，
而是推动 heap state 自己进入更好的平衡态。
```

## 这个补充目前还没有证明

需要强调：

```text
SPR-037 的实验没有证明 heap state relaxation。
```

SPR-037 只证明了：

```text
手动扫 relation_weight / order_weight 时，
fold 质量存在一个可观测控制面。
```

Houming818 这里提出的是下一步 claim 候选：

```text
TreeHeap 不只有参数梯度路径，
还可能存在 heap state 平衡梯度路径。
这种路径可以在目标结构不可导时，
通过可导能量函数完成结构松弛。
```

这应该进入后续实验，而不是混进当前结论。

一个最小 proof 可以是：

```text
1. 固定 kernel 参数
2. 初始化一个不平衡 heap state
3. 定义 balance / parent-child / relation 三类能量
4. 只更新 H，不更新 θ
5. 观察 heap 是否收敛到更稳定、可读、可坍缩的结构
```

如果这个实验通过，TreeHeap 会多出一条很有自己味道的学习路径：

```text
不是只训练参数，
而是让 heap 自己松弛到稳定结构。
```

## 为什么这比直接生成更好

假设我们直接让模型生成：

```text
the cat is running for a car
```

一开始可能输出很乱。

如果只有最终结果，我们只能说：

```text
模型不行。
```

但如果有控制面，我们可以问更细的问题：

```text
relation_weight 太低了吗？
order_weight 太高了吗？
collapse 太早了吗？
noise 太大了吗？
某个 subheap 没有被正确分割吗？
kernel 缺少共轭/镜像/分解操作吗？
```

这就从“黑箱失败”变成“可诊断失败”。

产品工程最需要的不是一次神迹，而是可诊断、可修补、可复现。

## 这次 toy proof 怎么做

我没有直接跑 WMT。

这次只做一个最小 proof：

```text
给定几句短句和弱 block 目标，
看 kernel 控制量能不能把 fold 从乱态推向稳定块。
```

短句包括：

```text
the cat is running for a car
a dog is chasing the ball
the book that i bought yesterday is expensive
some kids are playing in the park
```

注意，这里不是要证明完整语法。

我们只给一些弱 block：

```text
the cat
is running
a car
for a car
the book
i bought yesterday
that i bought yesterday
is expensive
```

这些 block 相当于“产品上希望看到的稳定局部结构”。

## kernel 的控制量

这次 kernel 只有两个主要旋钮。

### 1. relation_weight

表示 kernel 多相信“词之间的关系场”。

比如：

```text
the -> cat
is -> running
a -> car
book -> relative clause
```

如果 `relation_weight` 高，相关词更容易被合并。

### 2. order_weight

表示 kernel 多相信线性邻近。

比如：

```text
the cat
is running
a car
```

这些词本来就在句子里靠得近。

如果 `order_weight` 高，邻近词更容易合并。

## 数学形式

每一步 fold 时，kernel 都要决定两个块 `A` 和 `B` 要不要合并。

这次的打分函数是：

```text
score(A, B)
  = relation_weight * relation(A, B)
  + order_weight    * order(A, B)
  - balance_penalty
  + noise
```

其中：

```text
relation(A, B)
```

表示两个块在关系场里有多接近。

```text
order(A, B)
```

表示两个块在原始句子顺序里有多接近。

```text
balance_penalty
```

防止一开始就把很不均衡的大块小块乱合。

```text
noise
```

模拟不稳定扰动。

## 实验变量

我们扫描：

```text
relation_weight in {0, 0.25, 0.5, 1, 2, 4}
order_weight    in {0, 0.25, 0.5, 1, 2, 4}
seeds = 64
```

评价指标是 block F1：

```text
预测出来的 block
和我们给定的弱 target block
有多少重合。
```

这不是 BLEU。

这也不是翻译质量。

它只是问：

```text
fold 出来的局部结构是否接近目标块？
```

## 实验结果

结果如下：

| 指标 | 数值 |
|---|---:|
| low-control mean F1 | 0.0828 |
| best mean F1 | 0.8148 |
| high-sum-control mean F1 | 0.8148 |
| diagonal gain | 0.7319 |
| product cells | 22 |
| pilot pass | true |

最重要的是对角线：

| relation_weight | order_weight | mean F1 |
|---:|---:|---:|
| 0.00 | 0.00 | 0.0828 |
| 0.25 | 0.25 | 0.4036 |
| 0.50 | 0.50 | 0.6398 |
| 1.00 | 1.00 | 0.7603 |
| 2.00 | 2.00 | 0.8119 |
| 4.00 | 4.00 | 0.8148 |

这个形状很重要。

它不是随机跳一下。

它显示：

```text
控制量很弱 -> 输出接近乱态
控制量增强 -> fold 结构明显变好
控制量继续增强 -> 进入平台期
```

这正是“可控流形”的最小证据。

## 一个具体 trace

对句子：

```text
the book that i bought yesterday is expensive
```

某次较好的 fold trace 是：

```text
the + book
i + bought
is + expensive
i bought + yesterday
that + i bought yesterday
the book + that i bought yesterday
整句合并
```

这很接近我们想看的结构：

```text
the book
i bought yesterday
that i bought yesterday
the book that i bought yesterday
is expensive
```

注意，这不是完整语法树。

但它说明 kernel 已经能把一些局部块先稳定下来。

这就是产品功能的早期形态：

```text
先不要完美理解整句，
先把局部稳定块折出来。
```

## 这证明了什么

这次 claim 是：

```text
S1-MANIFOLD-C01:
If TreeHeap fold is driven by kernel controls over a latent relation field,
product-like structure should emerge as a measurable control surface.
Increasing relevant control variables should move output from noisy blocks
toward stable target blocks on a toy relation task.
```

状态：

```text
supported pilot
```

它证明的是：

```text
在一个透明 toy relation field 上，
TreeHeap fold 可以被 kernel 控制量调节，
并且结构质量会沿控制面明显提高。
```

换句话说：

```text
我们可以把 TreeHeap 的失败变成可观测、可调试的失败。
```

这对工程很重要。

## 这没有证明什么

它没有证明：

```text
TreeHeap 已经理解语言
TreeHeap 已经能翻译
TreeHeap 胜过 Transformer
relation field 能无监督自动学出来
这两个旋钮就是最终旋钮
```

尤其是：

```text
relation field 这次是 toy 构造的。
```

这意味着下一步必须把 toy relation field 换成真实数据估计出来的 relation field。

比如：

```text
共现窗口
masked token restoration
弱依存关系
contrastive phrase pairs
短句人工弱标注
```

## 对 TreeHeap 路线的意义

现在我更赞同你的判断：

```text
代数逻辑和产品逻辑不能分太开。
```

但也不能直接从代数跳到 WMT。

中间要有一层：

```text
TreeHeap Structure Lens
```

它应该能显示：

```text
当前 token/block 的邻近关系
当前 fold trace
每个 merge 的 energy
每个 stop/left/right 的概率
哪些结构稳定
哪些结构还在叠加
哪些控制量改变后结构变好
```

也就是说，产品上先做一个“结构透镜”。

不是先做最终翻译器。

## 下一步

我建议下一步不是继续加 toy trick。

而是把这个控制面放到真实数据上。

最小版本：

```text
输入真实短句
从语料共现或 masked restoration 估计 relation field
用 TreeHeap kernel fold
扫 relation/order/collapse 控制量
看 block F1、稳定性、能量是否形成可控面
```

如果真实数据也有类似曲面：

```text
低控制乱
中控制变好
高控制平台
```

那我们就有了继续推进 S1 的依据。

如果没有，也很好：

```text
说明 toy relation field 太人工，
或者 kernel 缺少关键算子，
或者真实语言 fold 不是这个控制方向。
```

这就是 ARA 的价值。

## 一句话总结

SPR-037 的结论是：

```text
TreeHeap 不能只证明自己有代数操作。
它还必须证明这些操作能被控制，
并且控制过程能让产品可见结构逐步涌现。
```

这次 toy proof 给了一个正信号：

```text
low-control F1 = 0.0828
best F1       = 0.8148
diagonal gain = 0.7319
```

所以当前更清晰的路线是：

```text
先建立可控结构透镜，
再用真实数据学习 relation field，
最后才谈生成和翻译。
```

May the Code be with us.

> **ARA**: [controllable manifold](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/controllable_manifold.md) / [claims](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/claims.md) / [experiment script](https://github.com/houming818/sametime/blob/main/ara/s1-echo/src/s1_controllable_manifold_probe.py) / [evidence](https://github.com/houming818/sametime/tree/main/ara/s1-echo/evidence/s1_controllable_manifold_probe)
