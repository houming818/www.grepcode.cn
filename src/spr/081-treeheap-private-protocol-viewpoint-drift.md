---
title: "[SPR-081] 模型是不是换了一个角度画鸡蛋：TreeHeap 私有协议的视角漂移"
date: 2026-08-03
lastmod: 2026-08-03
weight: 81
author: Houming818 & Codex Review
description: "提出一个可证伪推测：TreeHeap 训练中 Butterfly、FOLD 与 Decoder 可能共同改变内部坐标，使 Dreams 在表面上非单调变化。文章给出典型语法探针、中间态对齐实验和严格反证条件。"
tags: [SPR, TreeHeap, Butterfly, PrivateProtocol, ViewpointDrift, Dreams, Grammar, ARA]
---

# 模型是不是换了一个角度画鸡蛋

> **本文记录的是推测与实验合同，不是已经成立的结论。**
>
> 当前证据已经说明 TreeHeap Butterfly 参与了双向翻译计算，但还不能说明训练过程中变化的 Dreams 都是同一语义的不同视角。

## 1. Houming818 提出的“画鸡蛋”问题

同一个鸡蛋，从正面、侧面、远处和近处观察，投影的形状都不同。画家最后只需要画出一个视角，但训练观察能力时，可以围着鸡蛋看一圈。

这个类比进入 TreeHeap 后，问题变成：

> Butterfly 让同一个输入依次经过多种异构坐标折叠。Encoder 和 Decoder 在训练中共同变化时，我们怎么知道模型最终采用了哪个观察坐标？不同 epoch 的 Dreams 会不会只是从不同角度画出的同一个语义？

Butterfly 中间态：

$$ H^{(0)},H^{(1)},\ldots,H^{(D)} $$

不是多条已经成形的自然语言 string，而是同一个输入的多个潜在坐标状态。当前程序也没有把这些状态平行送给 Decoder，而是串行计算：

$$ H^{(D)} = B_{D-1}\circ\cdots\circ B_1\circ B_0(H^{(0)}) $$

只有这个统一干涉态继续进入 FOLD：

$$ H_{\mathrm{state}} = \operatorname{FOLD}(H^{(D)}) $$

因此，我们观察的是一块不断旋转的内部画板，不是让 Decoder 在许多独立句子中挑一条。

## 2. 为什么内部坐标可以变化

设 Encoder 产生状态 $H$，Decoder 为 $D$。如果内部存在一个可逆变换 $A$：

$$ H'=A(H) $$

并且 Decoder 同时学会：

$$ D'(H')=D(A^{-1}H') $$

那么：

$$ D'(H')=D(H) $$

外部功能可以完全不变，但内部坐标已经改变。

这意味着 token 交叉熵只要求 Encoder 与 Decoder 配合完成目标，不要求它们采用研究者指定的坐标系。训练中的参数变化可能同时调整：

~~~text
Butterfly 怎样折叠地址
FOLD 怎样形成 root/detail
READ 怎样分配深度质量
Decoder 怎样解释这些状态
~~~

这正是“私有协议”的坐标不唯一性。

## 3. Dreams 变化不等于视角变化

必须把三种现象分开。

### 3.1 内部坐标旋转

~~~text
原始 H 变化明显
对齐以后 H 可以恢复
关键语义和输出分布保持稳定
~~~

这才是本文要寻找的坐标漂移。

### 3.2 合法的表面视角变化

下面两句话词面不同，但可以表达同一事件：

~~~text
新公司预计将在2019年春季开始运营。
新公司计划于2019年春天投入运作。
~~~

如果实体、时间、事件和论元关系都保留，可以把它们视为同一语义的不同表面投影。

### 3.3 真实生成错误

下面这些不能仅凭“视角不同”解释：

~~~text
主体和客体互换
否定词丢失
before 变成 after
612 名乘客变成 600 人
原因和结果颠倒
连续重复同一句短语
产生输入中不存在的事件
~~~

流畅不等于正确。内部坐标能够对齐，也不自动证明 Dream 的语义正确。

## 4. 为什么原来的六条 Dreams 不够

现有探针能观察年份、简单因果和自由长句，但很难区分模型到底保存了什么语法关系。

因此，新的固定探针加入了人类语法分析中更典型的最小差异。

### 4.1 主体与客体反转

~~~text
Ultraman defeated the little monster.
The little monster defeated Ultraman.
~~~

两句话拥有相同的实体和关系词，只有谁打败谁不同。词袋模型无法解决，结构状态必须保留手性。

### 4.2 主动与被动

~~~text
The wind blew the rain against the glass.
The rain was blown against the glass by the wind.
~~~

表面顺序变化，但事件角色应当保持一致。

### 4.3 否定

~~~text
The cat ate the fish.
The cat did not eat the fish.
~~~

模型若只保存“猫、吃、鱼”的共现，会丢掉决定句意的极性。

### 4.4 时间顺序

~~~text
Xiaohong arrived before Xiaoming ate dinner.
Xiaohong arrived after Xiaoming ate dinner.
~~~

实体与事件相同，但时间方向相反。

### 4.5 量词

~~~text
Every window in that house is open.
Not every window in that house is open.
~~~

“not every”不能退化为“every”，也不能错误翻成“所有窗户都没开”。

### 4.6 附着关系

~~~text
I used a telescope to see the man.
I saw the man who was holding a telescope.
~~~

两句话都包含“我、男人、望远镜、看见”，但望远镜属于不同关系。

此外还加入中文“把/被”、话题结构、关系从句、因果方向、精确数字和嵌套长句。完整探针公开保存在：

~~~text
ara/s3-generation/dreams.txt
~~~

这些句子不会进入训练，只在固定 wake 点观察模型。

## 5. 当前长训为什么提出了这个问题

截至约 4881 万训练样本，当前双向 Butterfly TreeHeap 的验证结果为：

| 项目 | NLL |
|---|---:|
| 原生 Butterfly | 3.4223 |
| 运行时改成 Identity | 5.0234 |
| Identity 损伤 | +1.6011 |
| 英译中 | 3.7219 |
| 中译英 | 3.1227 |

这支持当前 checkpoint 依赖 Butterfly 通信，但 Dreams 并不是单调变好：

- 有时年份、事件和论元逐渐出现；
- 有时同一句在后续 checkpoint 又发生重复；
- 短句通常比长句稳定；
- 中译英整体比英译中稳定。

仅凭这些现象，我们无法判断：

~~~text
模型更换了内部视角
Decoder 的输出模式在漂移
模型发生了普通遗忘
或者 greedy argmax 在接近概率上跳变
~~~

因此必须观察中间态。

## 6. 实验一：先审核可见的 Dreams

对 taskd 89 已保存的所有不可变 Dreams 快照，按固定句逐 checkpoint 排列。

每条输出分别标注：

~~~text
主体/客体是否正确
否定是否正确
时间顺序是否正确
数字与实体是否正确
因果方向是否正确
整体含义是否可接受
表面措辞是否改变
是否存在严重重复
~~~

语义事实分数与流畅度、BLEU、词面相似度分开报告。

如果措辞不断变化，但角色、事实和因果稳定，才获得“表面视角变化”的候选证据。如果事实同时变化，则仍然是模型不稳定。

## 7. 实验二：给 Butterfly 接一个只读示波器

在 Butterfly 每个串行阶段后记录：

$$ H_i^{(0)},H_i^{(1)},\ldots,H_i^{(D)} $$

探针采用只读的 detach。只有最终状态进入 FOLD，中间态不进入 Decoder、不计算额外 Loss，也不改变梯度。

当前 RTX 3090 训练只占约 5.2 GB 显存。最大 batch 下，一个阶段约 2 MiB，八个阶段约 16 MiB。固定几十条句子的 wake 探针可以承受；把数千万训练样本全部落盘则不可接受。

## 8. 实验三：跨 checkpoint 对齐坐标

取早、晚两个 checkpoint。把语法探针稳定分为：

~~~text
calibration：只用于求坐标变换
heldout：只用于验证
~~~

在 calibration 上求正交 Procrustes 对齐：

$$ A^* = \underset{A^\top A=I}{\arg\min} \left\| X_{\mathrm{cal}}A-Y_{\mathrm{cal}} \right\|_F $$

然后只在 heldout 上计算未对齐状态误差、对齐后状态误差和 alignment gain：

$$ \text{gain} = 1- \frac{\text{aligned NRMSE}} {\text{raw NRMSE}} $$

若在同一批数据上拟合和评分，灵活的变换可能伪造一致性，所以禁止这样做。

## 9. 注册 Predict

### P1：语义与表面可以分离

两个后期 checkpoint 之间，至少 25% 的探针发生措辞变化，同时平均语义事实分数下降不超过 0.05。

### P2：内部坐标可以在留出句上恢复

至少两个 Butterfly 阶段的 heldout alignment gain 不低于 20%。

### P3：对立含义不能被对齐坍缩

对齐以后，“奥特曼打怪兽”和“怪兽打奥特曼”仍必须比同一事件的主动/被动表达更加可分。若所有句子都被压到一起，对齐没有语义意义。

### P4：任务功能必须真实改善

至少有一个阶段的参考 NLL 或语义事实分数改善。只有参数坐标变化、任务始终很差，只能叫参数漂移。

### P5：探针不能改变被观察对象

打开与关闭 trace 后必须满足：

~~~text
max absolute logit difference <= 1e-6
greedy token IDs 完全相同
~~~

## 10. 什么结果会推翻推测

以下任何结果都必须降级 Claim：

~~~text
对齐不能改善 heldout 状态
对齐只对参与拟合的句子有效
主客体、否定和时序在对齐后一起坍缩
表面变化总伴随事实错误
trace 改变了 logits 或输出 token
没有两个独立 checkpoint 可供比较
~~~

还要区分两种部分结果：

- 中间态能对齐、语义不稳定：只证明坐标重参数化；
- 语义稳定、中间态不能对齐：只证明表面输出稳定；
- 两者同时成立：才支持私有协议视角漂移。

## 11. 当前工程状态

ARA 已登记：

~~~text
S3-TREEHEAP-VIEW-DRIFT-C04
~~~

实验脚本：

~~~text
ara/s3-generation/src/s3_treeheap_viewpoint_drift.py
~~~

它提供“self-test / capture / compare”三个阶段。当前 96 小时训练不会被热修改。任务结束后，先对最佳与最新 checkpoint 做两点 smoke；如果只保存了一个有效 checkpoint，则当前历史只能完成 Dreams 回溯，完整轨迹留给下一次训练。

## 12. 本文真正想知道什么

问题不是“模型的每一句 Dream 能不能被解释成正确”。

真正的问题是：

> 当 TreeHeap 的 Butterfly、FOLD 和 Decoder 一起训练时，它们是否形成了一个不断调整但仍保持语义关系的私有坐标协议？

如果答案为否，我们得到一个清楚的失败：Dreams 波动只是生成不稳定。

如果答案为是，我们第一次能够区分：

~~~text
模型忘记了什么
模型换了一种说法
模型只是旋转了内部画板
~~~

这三件事不能再混为一谈。

---

**License:** GPLv3。本文公开 Claim、反证条件、探针语料与实验代码；任何人都可以复现、修改或给出相反证据。
