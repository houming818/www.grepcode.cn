---
title: "TreeHeap 当前理论状态与目标"
date: 2026-09-20
lastmod: 2026-09-28
author: Houming818 & Trinity (Codex)
description: "TreeHeap 的非编号理论基线：集中维护当前认可的基本假设、总体架构、组件合同、数学约束、开放问题与下一阶段目标。"
keywords: [TreeHeap, 当前理论, 总体架构, embedding, UNFOLD, FOLD, READ, Decoder, 概率背景场, 多分辨率, 私有协议]
tags: [TreeHeap, Theory, Architecture, OpenResearch]
url: /treeheap-theory.html
aliases: [/treeheap-glossary.html]
ShowToc: true
TocOpen: true
---

# 本页的职责

TreeHeap 的公开记录分成两类。

1. **数字编号 Blog** 保存研究路线：问题怎样出现、做过什么实验、哪些尝试失败、证据怎样改变判断。
2. **本页** 保存当下状态：我们现在采用什么理论、各组件应满足什么合同、完整系统的目标是什么、还缺哪些关键结构。

本页不是实验年表，也不追求保存每一次中间观点。历史过程从 [SPR 数字序列](/spr/) 阅读；2026 年 8 月的完整架构快照见 [TreeHeap 001 论文](/treeheap-paper/001-treeheap-emergent-protocol.html)。当数字 Blog 产生足够证据改变理论时，再更新本页。

# 当前总判断

TreeHeap 的目标不是把一组向量摆成树形，也不是为 Transformer 换一种索引。它试图建立一种具有以下性质的生成模型状态：

1. token 从语料背景中形成可计算的概率表示；
2. 状态在 root、parent、leaf 之间具有明确的分辨率关系；
3. 递归组合保持数据类型和量纲自洽；
4. coarse 层表达较稳定的共同约束，fine 层保留尚未坍缩的可能性；
5. READ 根据生成任务选择所需分辨率；
6. Encoder、READ 与 Decoder 通过端到端训练形成内部协议；
7. 整套系统能在消费级硬件上训练、保存、重载和继续生长。

我们现在认为，合理的研究顺序是：**先定义 UNFOLD 和 Embedding 所在的状态空间，再要求 FOLD 在同一状态族中闭合，最后训练 READ 与 Decoder 使用它。**

# 当前目标架构

```text
语料观测
  |
  v
token 背景概率场
  |
  v
root-to-leaf 概率 Embedding / UNFOLD
  |
  v
句中 occurrence 状态 + 顺序信息
  |
  v
同一状态族上的递归 FOLD
  |
  v
root / parent / leaf 多分辨率状态
  |
  v
分辨率感知 READ
  |
  v
Decoder 概率场
  |
  v
具体生成序列
```

这张图是目标合同，不表示所有边已经实现。当前核心缺口是中间三段：type 级 Embedding 怎样成为 occurrence 级状态；FOLD 怎样在概率状态中同时保持闭合与顺序；READ 怎样读取这种状态并与 Decoder 形成协议。

# 一、语言状态的物理含义

## Token ID 不是语义

Token ID 只是离散编号。编号之间的数值距离没有天然语言意义，所以不能依靠 ID 加减构造语义。

TreeHeap 采用的起点是：一个 token 的意义，至少部分表现为它对候选空间施加的概率约束。外围语料越充分，条件分布越能排除不相干候选。Embedding 因而不只是任意坐标，还应承载可组合的概率关系。

## 背景概率场

对 token 类型 `x`，先从语料构造背景状态：

```text
b_x = P(context | token=x)
```

这里的 `context` 可以由邻近 token、方向、距离、位置或更高阶结构定义。背景场不是最终答案，它是 token 进入 TreeHeap 前可观测的统计环境。

## Type 与 occurrence

必须区分：

- `token type`：词表中的抽象类型；
- `token occurrence`：某一句、某个位置上实际出现的 token。

背景场主要定义 type 的先验位置。Encoder 还必须把句内上下文和顺序注入 occurrence。否则一词多义、指代和组合语义无法仅靠静态 Embedding 解决。

# 二、Embedding 与 UNFOLD

## Embedding 是构造过程

当前理论不把 Embedding 只定义成随机初始化的 lookup table。一个 token 从 root 携带单位质量开始，在每个节点经过概率 gate：

```text
m_left  = m_parent * (1 - g_v(x))
m_right = m_parent * g_v(x)
```

递归到 leaf 后得到：

```text
p_x = [p_1, p_2, ..., p_L]
p_i >= 0
sum_i p_i = 1
```

这个 leaf 概率向量是 token 的一种 Embedding。它同时保存了从 root 到 leaf 的逐层路径概率，因此天然带有多分辨率结构。

## 节点局部坐标

每个节点面对的是当前子群，而不是整个词表。节点可以根据局部背景特征建立自己的主轴、阈值和温度：

```text
score_v(x) = axis_v dot feature(x) - threshold_v
g_v(x) = sigmoid(score_v(x) / temperature_v)
```

主轴决定在当前区域观察哪个方向，阈值决定怎样分割，温度决定路由是接近硬选择还是保留两侧概率。

## 分叉与互斥

相似性只能提供聚合力，不能保证空间被充分使用。Embedding 还需要互斥或容量压力，避免所有 token 落入少数路径。这个压力应参与学习，但不应把某个固定流量直接指定给左右分支。

理论目标是：分支由数据关系产生，同时有足够的竞争避免路径坍缩。

## 背景先于增量安装

高频、稳定的 token 可以先形成背景；随后低频 token、BPE 组合和新词读取已有节点统计，再更新背景。这样，Embedding 是可以逐步生长的，而不是每次扩词表都从头随机摆放。

动态加入新 token 后怎样避免整体坐标漂移，仍是开放问题。

# 三、多分辨率与不确定性

## coarse 与 fine

`coarse` 状态覆盖更大范围，表达较少但较稳定的约束；`fine` 状态覆盖更小范围，保留更多局部差异。

它们不是简单的“大向量”和“小向量”，也不是数值能量的高低。分辨率由状态能区分多少结构、还保留多少候选来定义。

## 当前的概率性假设

我们当前采用的理论方向是：

```text
coarse：较稳定的共同约束
fine：较多尚未决定的可能性
```

因此，语言生成中的随机性不必全部由 Decoder 最后人工加入。部分随机性可以来自 fine 状态尚未坍缩的概率质量。READ 决定当前任务需要展开到哪种分辨率，Decoder 再把它变成词表分布。

这不是说 coarse 的数值熵在任何条件下都必须更低。真正需要定义和测量的是条件不确定性：在给定输入、层级和任务以后，每层还剩多少可区分的可能性。

## 深度不等于有效容量

树的 leaf 数随深度增长，但有效容量只有在多个分支被真实使用时才增长。如果路由全部坍缩成一条链，深树仍接近低维结构。

有效分辨率至少取决于：

- 每层分支的使用情况；
- 条件路由熵；
- 有效 leaf 数；
- token 邻域是否稳定；
- 不同层对目标信息的保留程度。

# 四、统一状态类型

FOLD、READ 和 Decoder 要能共同工作，leaf 与 parent 不能各自使用无法比较的数据结构。当前理论需要一个统一的状态合同：

```text
TreeState {
  common   // 当前尺度可稳定保留的共同成分
  detail   // 区分更细状态所需的残差信息
  mass     // 概率质量或证据量
  address  // 节点、深度与路径
  order    // 序列方向或位置关系
  support  // 当前状态覆盖的 occurrence 范围
}
```

字段是否最终都要显式存储尚未确定，但它们代表必须有去处的信息。

## 量纲与闭合

如果 leaf 是归一化概率，parent 也必须明确是概率、概率与质量的组合，或另一种声明过的状态，不能在递归中无说明地把概率、hidden vector 和残差混在一起。

所谓闭合，是指：

```text
state_left, state_right in S
FOLD(state_left, state_right) in S
```

闭合只保证输出仍属于同一规则空间，不保证语义正确，也不保证可逆。

# 五、FOLD：从细状态形成 parent

## 概率合并基线

在相同 leaf 空间中，最清楚的闭合合并是质量加权混合：

```text
m_parent = m_left + m_right

p_parent =
  (m_left * p_left + m_right * p_right)
  / m_parent
```

它保持归一化，也能解释 parent 是两个子分布的混合。

## 交换性问题

上述公式满足：

```text
FOLD(a, b) = FOLD(b, a)
```

语言序列通常不满足交换律，所以纯平均只能作为无序概率基线。完整 FOLD 必须显式加入顺序、方向或非交换变换，同时仍保持状态合同。

候选形式可以写为：

```text
parent = Normalize(
  common(left, right)
  + ordered_interaction(left, right)
  + retained_detail(left, right)
)
```

这里不是要求 parent 无损保存所有输入，而是要求它对后续任务具有充分信息。

## 可逆性不是唯一目标

可逆 FOLD 可以证明信息没有数值丢失，但可能只是把原输入搬进 detail。不可逆压缩也可能保留完成任务所需的充分统计量。

因此当前目标从“所有层都能恢复整句”调整为：

1. coarse 状态保留任务需要的稳定约束；
2. detail 保存必要而非全部的差异；
3. READ 可以按需组合二者；
4. 消融任何必要通道时，任务行为出现可解释变化。

# 六、通信、READ 与 Decoder

## 通信不是 FOLD

XOR-Butterfly 或其他稀疏通信负责让远距离 occurrence 交换信息。它解决信息能否到达，不决定 token 怎样 Embedding，也不决定两个状态怎样形成 parent。

## READ

READ 接收 Decoder query，并从不同深度选择或混合状态：

```text
read_context = READ(query, tree_states)
```

一个合格的 READ 应明确：候选节点、路由概率、残差使用、归一化、停止条件和无旁路约束。

READ 的目标不是机械走到 leaf，也不是强迫每层等量贡献，而是在当前生成步骤选择足够的分辨率。

## Decoder

Decoder 把已生成前缀与 READ context 变成词表 logits：

```text
logits_t = Decoder(prefix_<t, read_context)
P(token_t) = softmax(logits_t)
```

Decoder 不需要恢复一个人类命名的“主视角”。它需要学会读取 Encoder 实际形成的状态协议。

## 私有协议

Encoder、READ 与 Decoder 可以不共享参数，但必须共享训练因果链：最终 loss 的梯度能到达生成 TreeHeap 状态的组件，Decoder 不能绕开输入状态完成任务。

私有协议成立至少要求：

1. 输入变化导致状态与输出变化；
2. 状态干预产生可预测的输出干预；
3. 保存、重载后协议保持；
4. Decoder 无法只靠目标前缀达到同样效果；
5. 多层状态的作用可被独立测量。

# 七、训练原则

## 最终任务与结构目标

最终生成 loss 负责回答“模型能否完成任务”。结构 loss 只负责创造可学习条件，不能代替最终任务。

候选目标包括：

- token 或序列 NLL；
- Embedding 的对比与邻域目标；
- 防止路由坍缩的分支使用约束；
- 顺序辨识目标；
- 状态闭合、归一化和数值稳定约束；
- 输入因果、重复率、非空率和长度等生成门禁。

总 loss 下降不能单独证明多分辨率语义形成。每一项结构目标都必须说明它保护什么性质，以及移除它会发生什么。

## 梯度职责

```text
生成 loss
  -> Decoder
  -> READ
  -> FOLD / communication
  -> occurrence state
  -> Embedding / node parameters
```

这条链路是否真实存在，需要梯度审计而不是架构图推断。若某个组件使用冻结统计，也要明确它从什么阶段获得信息。

# 八、当前理论边界

现在可以把以下内容作为设计基线：

1. Embedding 应是可构造、可扩展的概率状态，而不只是随机地址；
2. root-to-leaf UNFOLD 同时产生路径与多分辨率表示；
3. 节点需要局部观察方向，整树不应只有一个全局线性分割；
4. 有效分辨率取决于分支使用，不等于名义深度；
5. FOLD 必须在统一状态族中闭合并处理顺序；
6. coarse 与 fine 应表达不同程度的约束和未决可能性；
7. READ 负责按任务选择分辨率；
8. Encoder、READ 与 Decoder 的协议只能由端到端因果证据确认。

以下仍是开放问题，不能写成结论：

1. 背景场的最佳特征是什么；
2. 局部主轴、阈值与树拓扑是否存在规范解；
3. 新 token 加入时怎样避免旧 Embedding 漂移；
4. 如何构造既保序、又保持概率闭合的 FOLD；
5. detail 应保存多少，怎样避免退化为原文旁路；
6. coarse 稳定、fine 随机的假设怎样被逐层测量；
7. READ 的最小充分接口是什么；
8. 该结构相对普通 Transformer 的质量、计算与内存优势是否成立。

# 九、下一阶段目标

## 目标一：固定统一状态合同

为 leaf、parent、root 与 READ context 定义同一套字段、shape、归一化、单位和序列化方式。任何候选 F 都必须接受这个合同检验。

## 目标二：完成保序且闭合的 FOLD

先解决最小双元问题：`AB` 与 `BA` 必须不同，parent 仍处于声明的状态空间，并且梯度有限。之后再扩展到递归深度与长序列。

## 目标三：把 type Embedding 接入 occurrence Encoder

让背景先验参与句内状态，但允许上下文改变静态路径，验证多义词和组合结构能否形成不同 occurrence 状态。

## 目标四：定义分辨率曲线

逐层记录条件路由熵、有效 leaf、目标互信息代理、顺序辨识率和生成差异，判断 coarse/fine 假设是否真的出现。

## 目标五：串联 READ 与 Decoder

关闭旁路，在相同训练合同下比较单层读取、多层读取、概率 READ 和残差读取，确认模型实际使用了哪些状态。

## 目标六：消费级硬件闭环

在 24GB 级 GPU 上完成可恢复训练、固定评测、checkpoint handoff 与本地推理。更大硬件可以用于验证尺度规律，但不能成为架构成立的前提。

# 维护规则

1. 数字 Blog 记录过程，本页只保留当前采用的理论；
2. 新实验不会自动进入本页，只有足以改变组件定义或目标时才更新；
3. 每个组件必须说明输入、输出、参数、训练信号和未解决条件；
4. 同名不同对象必须拆名，尤其是路由 F、概率 FOLD 与隐态 FOLD；
5. 架构图必须画出尚未接通的边，不能把目标链伪装成现状；
6. 被新证据替换的理论先在数字 Blog 留下原因，再修订本页；
7. 本页不替代 ARA，所有可审计结论仍以 Claim 与 evidence 为准。

## 当前版本

**2026-09-28：** 建立“数字 Blog 保存研究路线、非编号页保存当前理论”的双层文档结构；补全 Embedding/UNFOLD、多分辨率概率、统一状态、保序 FOLD、READ/Decoder 协议与下一阶段六项目标。

这份页面回答的不是“我们一路做过什么”，而是“如果今天重新打开代码，我们认为 TreeHeap 应当是什么，以及下一步必须把哪条边接起来”。
