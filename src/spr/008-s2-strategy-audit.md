---
title: "[SPR-008] S2 策略审计：TreeHeap、Role Slots 和概率容器"
date: 2026-06-17
weight: 8
author: nio (Houming818) & Codex Review
description: "用 ARA 方式解释 S2 实验：当前 TreeHeap checkpoint 支撑什么、不支撑什么，以及下一步为什么转向 Role Slots 和 Probability Container。"
tags: [SPR, S2, ARA, TreeHeap, FoldStack, ProbabilityContainer]
---

# S2 策略审计：TreeHeap、Role Slots 和概率容器

这篇文章写给刚接触 SPR 的读者。你只需要有本科计算机水平，知道一点向量、分类器、树和图，就能读下去。

先说结论：

```text
当前 S2 最可靠的方向不是：
TreeHeap 128D -> 直接能量搜索 -> 正确语法树

而是：
语义向量 -> Role Slot -> 概率容器 -> 延迟坍缩
```

这句话里有几个词听起来很硬。我们一个一个拆开。

## 背景：我们到底想解决什么

普通神经翻译或语言模型经常把句子看成 token 序列，然后用 attention 去找词和词之间的关系。

SPR 想探索另一条路：

```text
能不能把语言结构压缩成更明确的路径、槽位和图？
```

在 S2 里，我们关心的不是“这个词像不像另一个词”，而是更结构化的问题：

```text
谁是主语？
谁是谓语？
谁是宾语？
哪个短语修饰哪个短语？
哪些候选结构应该先保留，不要太早拍死？
```

这就是 Fold Stack / Graph Builder 的问题。

## ARA 方式

这里先纠正一个容易误解的点：ARA 不是

```text
Architecture / Reasoning / Artifact
```

ARA 指的是：

```text
Agent-Native Research Artifact
```

它不是一种写作修辞，而是一套面向 AI agent 的研究制品协议。论文《The Last Human-Written Paper: Agent-Native Research Artifacts》把 ARA 拆成四层：

| 层 | 目录 | 作用 |
|----|------|------|
| Cognitive Layer | `/logic` | 问题、方案、可证伪 claim、实验计划 |
| Physical Layer | `/src` | 可执行代码、配置、环境、实现说明 |
| Exploration Graph | `/trace` | 研究 DAG、失败路线、pivot、dead end |
| Evidence Layer | `/evidence` | 原始输出、日志、指标表、claim 的证据 |

所以这篇文章只是给人读的说明文；真正的 ARA 内容应该在仓库的这些目录里。

ARA 的原则是：

```text
一个结论必须绑定证据。
一个强 claim 必须允许被实验推翻。
```

所以这篇不会说“TreeHeap 已经成功了”。我们只说实验支持了什么，没有支持什么。

## `/logic`：先预测，再实验

这里还要补一个更重要的点。

ARA 不是：

```text
先随便跑实验
看到结果
再回头编一个结论
```

真正的 ARA 顺序应该是：

```text
predict -> claim -> experiment -> evidence -> trace
```

翻译成人话：

```text
1. 先写一个预判：如果我的理论是真的，实验应该看到什么？
2. 再把这个预判变成一个可以被推翻的 claim。
3. 然后设计实验，专门去验证或打脸这个 claim。
4. 实验输出原始数据，放进 /evidence。
5. 如果实验失败或改方向，把失败路线写进 /trace。
```

这和普通博客最大的区别是：ARA 不鼓励“事后讲故事”。  
它要求我们在实验前就写清楚：

```text
我预计会发生什么？
什么结果算支持？
什么结果算失败？
如果失败，架构要怎么改？
```

拿这次 `t_merge` 问题举例。

我们现在不应该直接写：

```text
t_merge 失效了。
```

而应该先写一个 predict：

```text
P-TM01:
如果 TreeHeap 的 L0 × 背景场参与机制成立，
那么新训练 checkpoint 的 post-merge 向量应该：
1. 不被公共方向完全主导；
2. 保留 L0/token identity；
3. 保留 path/background bucket 信息；
4. 在 role-slot 或 context probe 上优于 L0 baseline；
5. 从 CMul pre-merge 到 post-merge 的距离结构不能大幅丢失。
```

然后它对应一个 claim：

```text
C-TM01:
TreeHeap 的背景场乘积可以产生一个非坍缩的 token-in-background state。
```

再对应一个实验：

```text
E-TM01:
重新训练一个小 checkpoint，
每个 epoch 自动跑 tmerge_diagnostic 和 strategy_audit。
```

提前写好通过标准：

```text
Pass:
- raw/centered cosine 都不过度坍缩；
- effective rank 足够高；
- path bucket probe 明显高于 chance；
- role/context probe 优于 L0 baseline；
- CMul -> post-merge distance correlation 保持较高。

Fail:
- post-merge 向量仍然被公共方向主导；
- role/context probe 不如 L0；
- path probe 接近 chance；
- 距离结构从 pre 到 post 大幅丢失。
```

这才是 ARA 的“logic 先行”。

所以，旧 checkpoint 现在不能为 TreeHeap 原理背书。它只能作为：

```text
legacy artifact
```

用来暴露问题、形成新的 predict。  
真正能给 TreeHeap 背书的 evidence，必须来自按这个 predict 重新设计并训练的新 checkpoint。

## `/logic`：新的四层理解

目前更清楚的分层是：

```text
L0: token/path substrate
L1: contextual semantic vector
L2: role-slot fold structure
L3: probability/energy collapse
```

可以用一个很朴素的比喻理解。

数字 `321` 不是简单的：

```text
[3, 2, 1]
```

它真正的结构是：

```text
3 * 百位 + 2 * 十位 + 1 * 个位
```

这里最重要的不是 `3,2,1` 本身，而是：

```text
百位、十位、个位
```

这些位置就是“位权”。

放到语言里：

```text
cat eats fish
```

不应该只是：

```text
[cat, eats, fish]
```

而应该更像：

```text
SUBJECT = cat
ROOT    = eats
OBJECT  = fish
```

所以 S2 现在要找的不是更深的树，而是：

```text
Role Slots
```

也就是“结构槽位”。

## 实验一：当前 TreeHeap 128D 是否适合直接做语法能量

我们先测试一个基础问题：

```text
历史 checkpoint 里的 TreeHeap 128D 向量到底长什么样？
```

使用的 checkpoint 是历史遗留模型：

```text
/mnt/nas/datasets/wmt_massive/checkpoints/anchor_tree_massive_ep3.pt
```

它不是这次重新训练的模型。

我们比较四种向量：

| 向量 | 含义 |
|------|------|
| random | 随机向量，作为健康基线 |
| L0 | checkpoint 里的原始 token embedding |
| TreeHeap | L0 + path + t_merge 后的 128D 输出 |
| path | token 在 TreeHeap 路径上的位置向量 |

最重要的指标叫：

```text
off-diagonal cosine mean
```

如果你不熟 cosine，可以简单理解成“两个不同词的向量平均有多像”。

- 接近 `0`：不同词分得比较开。
- 接近 `1`：不同词几乎都挤在一起。

实验结果：

| Vector | 不同词平均相似度 | 解释 |
|--------|------------------|------|
| random | 0.0007 | 正常随机基线 |
| L0 | 0.0003 | 分得很开 |
| TreeHeap | 0.9849 | 几乎全挤在一起 |
| path | 0.4937 | 粗粒度路径簇 |

这个结果很关键。

它说明：

```text
当前 ep3 TreeHeap 输出太坍缩。
```

也就是说，很多不同 token 经过 TreeHeap 后，方向几乎一样。这样的向量很难直接拿来判断语法结构。

这不是说 TreeHeap 理论错了，而是说：

```text
当前历史 checkpoint 的 tree 输出不能背负“语法能量已成立”的 claim。
```

## 实验二：非交换张量能不能直接选出正确结构

我们之前讨论过一个想法：

```text
h1 ⊗ h2 ⊗ h3
```

这是有序张量。它和普通加法不同。

普通加法：

```text
cat + eats + fish
= fish + eats + cat
```

顺序丢了。

有序张量：

```text
cat ⊗ eats ⊗ fish
!= fish ⊗ eats ⊗ cat
```

顺序保住了。

所以我们要分清两个问题：

```text
问题 1：它能不能区分排列？
问题 2：它能不能把正确语法排到第一？
```

实验结论是：

```text
能区分排列，但 raw energy 还不能稳定选出正确语法。
```

在 SVO3 任务上，role-slot template 的结果如下：

| Mode | Top-1 | Top-3 | Mean gold rank |
|------|-------|-------|----------------|
| L0 + random role basis | 0.509 | 0.812 | 2.11 |
| random + onehot role basis | 0.464 | 0.786 | 2.21 |
| TreeHeap + onehot role basis | 0.330 | 0.723 | 2.59 |

这里 Top-1 的意思是：

```text
正确排列排第一的比例
```

Top-3 的意思是：

```text
正确排列出现在前三名的比例
```

如果 TreeHeap 真的已经天然对齐语法，我们希望它明显赢过 L0 和 random。

但结果相反：

```text
TreeHeap 没赢。
```

所以结论必须收紧：

```text
非交换张量是必要工具。
但当前 TreeHeap 输出不足以直接做 syntax energy。
```

## 实验三：Role Slots 是否真的存在

接下来问一个更实际的问题：

```text
语言结构是不是适合用少量槽位表达？
```

比如 VP 可以写成：

```text
VP {
  subject
  object
  adverb
  complement
}
```

而不是强行写成二叉树：

```text
eat
├─ cat
└─ NodeX
   ├─ fish
   └─ quickly
```

我们在 12,000 条 WMT massive 英文样本上统计 FoldNode 的子节点数量。

结果：

| Degree threshold | Coverage |
|------------------|----------|
| <= 2 | 86.1% |
| <= 3 | 95.8% |
| <= 4 | 99.0% |
| <= 5 | 99.8% |

这说明：

```text
绝大多数 FoldNode 用 4 个左右的槽位就够了。
```

这对架构很重要。

它支持：

```text
Role-slotted FoldNode
```

而不是继续押：

```text
更深的二叉树
或者
更高叉但无名的树
```

常见模式也很直观。

VP 常见模式：

```text
nsubj
dobj
dobj + nsubj
aux + dobj
aux + dobj + nsubj
```

NP 常见模式：

```text
det
compound
amod
amod + det
poss
```

翻译成人话：

```text
VP 常围绕主语、宾语、助动词展开。
NP 常围绕限定词、复合词、形容词、所有格展开。
```

这就是 Role Slots 的证据。

## 实验四：概率容器是否有必要

Graph Builder 过去常做一件事：

```text
给每个节点选一个最可能的父节点。
```

这叫过早坍缩。

但很多结构局部看不出来。

经典例子：

```text
I saw the man with a telescope.
```

`with a telescope` 可以挂到 `saw`，也可以挂到 `man`。局部阶段未必应该立刻选死。

所以我们测试：

```text
正确父节点是否在 top-k 候选里？
```

如果 top-1 不完美，但 top-3 几乎总包含正确答案，那就说明应该保留候选分布，而不是马上 argmax。

结果：

| Metric | Value |
|--------|-------|
| graphs | 8,408 |
| pair rows | 195,610 |
| eval child sets | 2,758 |
| gold parent in top-1 | 93.1% |
| gold parent in top-2 | 99.3% |
| gold parent in top-3 | 99.9% |
| gold parent in top-5 | 100.0% |

这个结果非常强。

它说明：

```text
正确答案几乎总在 top-3 里。
```

所以 Graph Builder 不应该只输出：

```text
parent = A
```

而应该输出：

```text
ParentContainer {
  A: 0.61
  B: 0.27
  C: 0.12
}
```

然后把这个容器传给后续模块，让更大的上下文再决定。

这就是 Probability Container。

## 夜间任务的部分结果

后来我们又启动了一个更大的 8 小时任务，目标是继续查：

```text
坍缩到底发生在哪里？
上下文窗口是否稳定提升 role-slot 预测？
不同 epoch 的 checkpoint 是否不同？
```

截至写作时，完整任务还在运行。但第一轮部分结果已经给出一个很有用的信号。

对 `anchor_tree_massive_ep1.pt`：

| Mode | 不同词平均相似度 |
|------|------------------|
| L0 | 0.0186 |
| CMul pre-merge | 0.0200 |
| Tree output | 0.9860 |

这说明：

```text
坍缩主要发生在 t_merge 之后。
```

也就是说，L0 和 CMul 本身没有严重坍缩，但经过 `t_merge` 之后，向量被挤到很相似的方向。

Role probe 的部分结果：

| Feature | Top-1 |
|---------|-------|
| L0 only | 0.538 |
| L0 + context | 0.570 |
| CMul + context | 0.559 |
| Tree + context | 0.548 |
| path only | 0.325 |

这个结果说明：

```text
上下文确实有 role-slot 信号。
path 单独很弱。
tree output 不如 L0/CMul 稳。
```

这些是部分结果，不能替代完整 8 小时任务的最终统计。但方向已经很清楚。

## `/logic`：我们现在怎么判断

把上面的实验合起来，推理链是：

```text
1. 当前 TreeHeap tree output 高度坍缩。
2. 坍缩后的向量不适合直接做语法能量。
3. 非交换张量可以区分排列，但不自动等于语法正确。
4. FoldNode 的真实结构高度适合小槽位表达。
5. parent top-k 覆盖非常高，所以概率容器有价值。
6. 上下文能提升 role-slot 预测。
```

所以下一步不是：

```text
继续硬做 edge classifier
```

也不是：

```text
直接宣布 TreeHeap energy search 成功
```

而是：

```text
Role Slots + Probability Container + 更好的 L1/context vector
```

## 当前架构决策

### 继续推进

```text
Role-slotted FoldNode
```

因为 degree 分布强烈支持小槽位。

```text
Probability Container
```

因为 gold parent top-3 覆盖接近满分。

```text
Context-conditioned role prediction
```

因为 L0 + context 已经比 L0 only 更好。

### 暂停放大的 claim

```text
当前 3-epoch TreeHeap 128D 已经是 syntax vector。
```

不支持。

```text
纯 tensor energy 可以替代 Graph Builder。
```

不支持。

```text
path 本身编码语法角色。
```

不支持。

## `/evidence`：证据在哪里

完整 strategy audit：

```text
ara/s2-translation/evidence/strategy_audit/
```

关键文件：

```text
strategy_audit_summary.json
tensor_energy_rows.csv
parent_container_rows.csv
role_slot_degree.json
README.md
```

夜间任务部分结果：

```text
ara/s2-translation/evidence/overnight_partial_20260617/
```

远端正在运行的完整任务：

```text
io:/data/homecicd/sametime/logs/s2_overnight_20260617_150111
```

脚本：

```text
s2_strategy_audit.py
s2_overnight_io.py
run_s2_overnight_io.sh
```

## 给初学者的最后总结

如果你只记住三句话，记这三句：

```text
第一，当前 TreeHeap checkpoint 的最终 128D 输出太坍缩，不能直接当语法向量。
```

```text
第二，语言结构更像“语义向量填入角色槽位”，而不是普通二叉树越堆越深。
```

```text
第三，Graph Builder 不应该太早选唯一答案，应该保留 top-k 概率容器，让后续上下文再坍缩。
```

这就是目前 S2 理论建设的位置：

```text
理论路线更清楚了。
部分方向被实验支持。
部分过强说法被实验降级。
下一步要训练或抽取更好的 L1/context vector，再重跑同一套审计。
```

> **License: GPLv3**
