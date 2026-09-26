---
title: "[SPR-092] TreeHeap 概念与实现总表：从研究语言走向可执行架构"
date: 2026-09-26
lastmod: 2026-09-26
weight: 92
author: Houming818 & Trinity (Codex)
description: "TreeHeap 的重要研发路线图：逐项列出概念定义、现有算法、证据、尚未实现的接口、验收门槛与依赖顺序，防止概念扩张快于工程闭环。"
keywords: [TreeHeap, 研发路线图, F函数, TreeState, FOLD, UNFOLD, READ, Decoder, 残差, 多分辨率, 私有协议, ARA]
tags: [SPR, TreeHeap, Roadmap, Architecture, FFunction, ARA]
---

# 为什么需要这张表

TreeHeap 已经积累了很多原创概念：下坠、背景场、概率残差、多分辨率退火、信息泵、私有协议、
递归 READ、Butterfly，以及正在寻找的 F 函数。

概念丰富不是问题。问题在于，**一个概念被描述、写出公式、做成 toy、通过真实数据实验、接入
主训练链路，是五件不同的事**。如果不明确区分，我们很容易把“有名字”当成“有算法”，把
“能 Echo”当成“能理解”，或者把两个分别成功的组件误认为已经形成完整系统。

这篇文章建立一张长期维护的研发台账。今后审查任何概念，都回答六个问题：

1. 它精确定义了什么？
2. 当前代码实现了什么？
3. 证据来自 toy、真实语料还是完整训练？
4. 哪些强结论仍然没有证据？
5. 下一道可否证门槛是什么？
6. 它依赖哪些上游接口？

# 先说当前总判断

TreeHeap 不是没有算法。我们已经实现了概率背景场、硬/软路由、概率 FOLD、可逆 Lifting、
Bayesian READ、Butterfly 通信和真实 WMT seq2seq。

但这些算法目前分属于两条没有完全接通的路线：

```text
概率场路线：
语料 -> P(context|token) -> 路由分区
     -> 节点 prototype / 残差 -> Bayesian READ

生成路线：
句子 token -> FOLD / Lifting / Butterfly
          -> 多层 hidden state -> READ -> Decoder
```

前者能够组织和读取 token 的统计背景，后者能够训练和生成文本。**当前最重要的工程断点，是还
没有把概率场中学到的 F 变成句子 Encoder 真正执行的 FOLD，并让 Decoder 通过同一状态协议读取
它。**

# 成熟度怎样标记

本文使用六级成熟度。它不是论文通行评级，只用于项目内部管理。

| 等级 | 名称 | 判定标准 |
|---|---|---|
| M0 | 概念 | 有定义或直觉，但没有可执行算子 |
| M1 | Toy | 合成数据或极小样本上有代码 |
| M2 | 真实组件 | 在真实语料上可运行、可保存、可重载 |
| M3 | 因果组件 | 通过 matched baseline、shuffle、删除或替换干预 |
| M4 | 主链集成 | 接入真实 Encoder-READ-Decoder 串联训练 |
| M5 | 可交付 | 有稳定质量、资源审计、CLI、版本与回归测试 |

达到 M3 不等于模型整体达到 M3。每个组件必须单独评级。

# 概念与实现总表

## 一、输入与状态

| 概念 | 设计目标 | 当前实现与证据 | 成熟度 | 主要缺口 |
|---|---|---|---:|---|
| token 背景概率场 | 用 `P(context|token)` 表示 token 的语料背景 | A11-A16 已从真实 WMT 构造、冻结、重载并做未见数据 READ | M3 | 目前主要是 token type，不是句中 occurrence |
| embedding 安装 | 让 token 在可计算空间和树路径中落位 | 概率坐标、轴/阈值路由和 checkpoint 已实现 | M2 | 分区跨 seed 仍漂移；语义优势未胜随机码 |
| 上下文 occurrence 状态 | 同一个词在不同句子中形成不同状态和路径 | 受控多义词 proof 曾通过 | M1 | 尚未接入真实语料主 Encoder |
| 统一 `TreeState` | leaf、parent、root 使用同一数据合同 | 多个实验各自有 tensor/state 定义 | M0 | 没有一个主模型共享的正式结构与序列化格式 |
| 背景场持续更新 | 新语料加入时增量更新而不遗忘旧场 | 共现计数可以累计 | M1 | 路由、原型和下游 checkpoint 的在线迁移尚未实现 |

### `TreeState` 尚缺的正式定义

当前最需要落地的数据结构可以先收敛为：

```text
TreeState {
    common      当前分辨率的公共状态
    detail      相对 parent 的新增信息
    mass        概率质量或支持量
    address     当前递归地址
    support     该状态覆盖的 token / span 范围
}
```

字段名可以改变，但每一层必须回答：数据类型是否相同、单位是否相容、怎样序列化、怎样求梯度、
Decoder 能看到哪些字段。

## 二、WRITE 与路由

| 概念 | 设计目标 | 当前实现与证据 | 成熟度 | 主要缺口 |
|---|---|---|---:|---|
| 节点函数 `f_v` | 在节点上计算左右路由 | 独立轴 `w_v`、阈值 `b_v`、硬/软路由均已实现 | M3 | 只完成固定二叉拓扑内的路由 |
| 整树函数 `F_Theta` | 把节点规则组合为完整路径与层级状态 | A11-A14 可搜索硬树；A17-A18 可微训练软树 | M2 | 还不是句子级统一状态变换 |
| 局部主轴 | 每个节点观察不同的数据方向 | token-pair axis、扰动搜索和梯度轴已有实现 | M2 | 没有稳定解释轴代表什么语言特征 |
| 动态拓扑 | 学习 split、merge、连接次序和树形 | 人工枚举 left-deep/balanced/right-deep | M1 | 路由器尚不能可靠地学习拓扑动作 |
| STOP | 在合适分辨率终止递归 | 历史 STOP gate 曾训练并坍缩到 leaf | M1 | 没有满足资源与质量合同的停止算法 |
| 防饥饿/容量分配 | 防止所有 token 落入少数分支 | Sinkhorn、平衡损失、硬容量实验存在 | M2 | 人工均衡可能扭曲自然概率；尚未与主 F 统一 |

这里必须保留一个边界：**路径可区分不等于路径有语义。** token ID hash、位置编码和随机唯一
码都能产生稳定路径，也能完成 Echo。

## 三、FOLD、残差与多分辨率

| 概念 | 设计目标 | 当前实现与证据 | 成熟度 | 主要缺口 |
|---|---|---|---:|---|
| 概率 FOLD | child 概率质量守恒地组成 parent | 质量加权 prototype，浮点尺度闭合 | M3 数学 / M2 工程 | 主要用于 token 背景场，未成为句子 hidden-state FOLD |
| normalized-sum FOLD | 控制深度能量与量纲 | 已有真实生成与尺度审计 | M2 | 深度尺度漂移、权重含义仍未彻底隔离 |
| 可逆 Lifting | parent 保存公共量，detail 保存差异，可精确 UNFOLD | 闭合、真实语料和 WMT 机制证据均存在 | M3 | 还未与概率 F 和统一 `TreeState` 合并 |
| 残差编码 | 逐层记录 child 相对 parent 的新增信息 | `delta = child - parent` 和望远镜闭合已实现 | M2 | 没证明优于直接保存每层 prototype 或 flat table |
| 多分辨率 | 粗层保存公共背景，深层补充细节 | A16 深度曲线、Lifting 深度干预有正面结果 | M3 局部 | 尚未形成稳定、互补、可复用的语言层级 |
| 退火 | 随深度降低不确定性或组织搜索空间 | 目前有多种公式和诊断实验 | M1-M2 | 没有统一熵定义和主模型训练合同 |
| 缩句式层级 | 高层对应更短、更抽象的语言表达 | 压力协议和长度实验存在 | M1 | 没有可靠的层级语义目标或生成门 |

### 残差当前只能怎样表述

若定义：

$$\Delta_v=\mu_v-\mu_{parent(v)}$$

则路径闭合：

$$\mu_{leaf}=\mu_{root}+\sum_{v\in path}\Delta_v$$

是定义导致的望远镜求和。任意 hash 树也可以满足。它证明数值记账自洽，不证明路径语义，更不
证明残差是最优存储方式。

残差要升级到 M3，必须在相同存储量和计算量下，胜过：

- token-ID hash 树；
- 随机平衡树加同样残差；
- 直接保存每层 prototype；
- flat leaf prototype table；
- 原生树但逐层 shuffle 或删除残差。

评价使用 masked READ、生成质量和 rate-distortion，不能使用 Echo 作为主要证据。

## 四、READ 与 Decoder

| 概念 | 设计目标 | 当前实现与证据 | 成熟度 | 主要缺口 |
|---|---|---|---:|---|
| Bayesian READ | 不训练 Decoder，直接从冻结概率场推断 token | A16 在未见 WMT 上胜 path/row shuffle | M3 | 只适合条件概率场，不是通用神经 READ |
| parent-only READ | 只读 parent，关闭 leaf 旁路 | F21 一 seed 支持线性可读 | M2 | 尚未跨任务、跨 seed 复现 |
| 多层 READ | 同时读取多个深度 | 多个模型有实现 | M2 | 共享 READ 曾造成层间干扰，深层贡献不稳定 |
| 查询条件递归 READ | Decoder query 决定读哪条路径和哪一层 | 有概率 READ、Lifting route 等局部实现 | M2 | 尚未形成统一、可审计、胜过 flat 的算法 |
| Decoder 私有协议 | Encoder 和 Decoder 通过梯度形成内部约定 | WMT、Stone、Lifting 均出现机制证据 | M3 局部 | 没与概率 F/embedding 安装统一 |
| 无旁路生成 | 输出必须依赖递归 parent/detail，不能直接搜索 leaf | 部分实验关闭过旁路 | M2 | 尚无统一回归门，历史实现仍可能以其他方式旁路 |

Decoder 不需要和 F 共享同一组参数。但它们必须通过同一个 `TreeState` 接口串联，且 Decoder loss
能够在需要时回传到 F。否则所谓“私有协议”只存在于文字中。

## 五、长程通信与生成

| 概念 | 设计目标 | 当前实现与证据 | 成熟度 | 主要缺口 |
|---|---|---|---:|---|
| Butterfly | 用 `log2(N)` 局部阶段建立全地址感受野 | 合成任务和三 seed WMT 均有因果收益 | M4 | 尚未证明计算成本优于优化后的稠密基线 |
| Stone 训练管线 | 预训练、任务训练、proof、loss、report | 已有长任务、恢复、wake、checkpoint | M4 | 不同航段的状态合同仍不完全统一 |
| 双语 seq2seq | 英中/中英生成 | 14.17M 数据规模训练已运行 | M4 | 自由生成质量、重复、长度和产品门仍开放 |
| 世界模型/背景知识 | 隐态保存可迁移的条件规律 | next-token、masked READ 有窄证据 | M1-M2 | 没有独立事实召回、推理和迁移评测闭环 |
| 逻辑/缩句/抽象 | 高层状态承载语言结构而非 token bag | 仍以假设和局部探针为主 | M0-M1 | 没有明确监督目标、可逆目标或权威基线 |

## 六、训练、部署与资源目标

| 概念 | 设计目标 | 当前实现与证据 | 成熟度 | 主要缺口 |
|---|---|---|---:|---|
| 全链路 loss | 同时优化背景组织、FOLD、READ 和生成 | 各阶段 loss 分别存在 | M1 | 目标之间会冲突，尚无统一加权或约束优化 |
| soft-to-hard | 将可训练 soft field 转成低成本路径 | A18 已定位硬化损失 | M1 | 没有一致性训练、Top-k 或渐进稀疏化方案 |
| 统一 checkpoint | 一个 artifact 保存 embedding、F、READ、Decoder 合同 | 各模块均能各自保存 | M1 | 尚不能无歧义组合、升级和回滚 |
| 消费级训练 | 一张 3090 可完成主要研究与本地部署 | 多数实验确实运行于 3090 | M3 工程 | soft 全路径和大词表仍可能失去稀疏优势 |
| 稀疏运行时 | 推理只激活少量路径和节点 | 设计目标明确 | M0-M1 | 尚无真实吞吐、显存和 kernel 证明 |
| 可复现发布 | ARA、日志、哈希、博客、CLI | 已形成较完整流程 | M4 | 大 artifact 管理和跨仓状态仍需收敛 |

# 当前真正缺失的四个算法

许多未完成概念可以归并成四个算法缺口，而不是继续增加名词。

## 缺口一：统一状态变换

需要一个正式可执行的：

```text
FOLD(left: TreeState, right: TreeState)
    -> parent: TreeState
    -> left_detail: TreeState
    -> right_detail: TreeState
```

它必须同时满足有限、有界、量纲相容、可微、可重载，并能被真实 Decoder 使用。概率平均和
Lifting 都是候选组件，但尚未合成一个主实现。

## 缺口二：句中 occurrence 的 WRITE

当前背景场主要回答“bank 这个 token 通常出现在哪里”。主 Encoder 必须进一步回答：

```text
WRITE(token=bank, context=river)   != WRITE(token=bank, context=account)
```

如果没有这一层，F 再复杂也只是在组织词典，而不是编码句子。

## 缺口三：查询条件的递归 READ

需要一个 READ，根据 Decoder 当前 query，在 root、各层 detail 和局部 child 之间分配读取质量，
并保存完整 route trace。它必须胜过相同容量的 flat memory，而不只是证明某个节点可读。

## 缺口四：soft 到稀疏的连续交接

训练时的 soft path 有效，突然阈值硬化会损失信息。需要渐进温度、Top-k、稀疏门或显式一致性
目标，使模型在训练过程中逐步适应有限路径，而不是训练结束后被切断。

# 主研发路线

下面按依赖关系推进，而不是按概念出现时间推进。

## R0：冻结术语和基线

状态：**当前进行中。**

交付物：

- 统一使用 `f_v`、`F_Theta`、学习算法 `A`；
- 固定 hash tree、random balanced tree、flat table、ordinary embedding 基线；
- Echo 只作为机械测试，不作为语义证据。

完成门：每个后续 Claim 都明确比较对象、参数量、存储量和计算量。

## R1：建立 canonical `TreeState`

状态：**未实现，最高优先级。**

交付物：

- 一个共享的数据类与 checkpoint schema；
- 概率 FOLD 和 Lifting FOLD 都实现同一接口；
- depth、shape、mass、closure、gradient 自动测试；
- 不接 Decoder，先完成数学和工程合同。

完成门：深度阶梯全部有限、闭合、reload 一致，且两个候选算子可以被同一测试套件替换。

## R2：实现 context-conditioned WRITE

状态：**只有受控 proof。**

交付物：

- token type 背景作为 prior；
- 当前句子 context 形成 posterior occurrence state；
- 同词多义真实语料 probe；
- token-only、BoW、普通 embedding 基线。

完成门：同一 token 的不同上下文状态可分，shuffle 后优势消失，并在未见词汇组合上复现。

## R3：残差因果门

状态：**尚未执行 matched 对照。**

交付物：

- 有/无残差；
- 直接 prototype 与路径残差；
- hash/random/native tree；
- 每层 delete/shuffle；
- 相同 bit budget 的 rate-distortion 曲线。

完成门：残差在至少一个非 Echo、未见数据任务中，以相同预算稳定胜过直接表和 hash 对照。

## R4：READ-Decoder 无旁路闭环

状态：**组件存在，统一闭环未实现。**

交付物：

```text
occurrence WRITE
  -> canonical FOLD
  -> multiresolution TreeState
  -> query-conditioned READ
  -> Decoder
```

训练必须保存每层读取质量、梯度和干预结果。

完成门：关闭 leaf/flat bypass 后仍能在真实 seq2seq 或 masked generation 上学习；root、detail、route
替换分别造成预注册的质量下降。

## R5：soft-to-sparse 与动态拓扑

状态：**软路由可用，硬交接失败。**

交付物：

- soft、Top-k、straight-through、渐进温度四臂；
- 质量、激活节点数、显存和吞吐共同测量；
- 动态 split/merge/STOP 放在稀疏路由稳定以后。

完成门：稀疏版本保留 soft 质量，同时产生可测量的消费级硬件收益。

## R6：规模、产品与开放发布

状态：**等待 R4/R5。**

交付物：

- 固定小/中/大尺度阶梯；
- 真实 CLI 翻译、生成、masked read 与重复率；
- 3090 显存、功率、吞吐和恢复审计；
- checkpoint、数据 manifest、SHA-256 和 GPL 发布材料。

完成门：结果在多 seed、未见数据和 checkpoint reload 后稳定，且不依赖研究脚本中的隐藏旁路。

# 依赖图

```text
R0 术语与基线
 |
 v
R1 canonical TreeState
 |
 +---------> R2 context WRITE
 |                 |
 v                 v
R3 残差因果门 ----> R4 READ-Decoder 闭环
                         |
                         v
                 R5 soft-to-sparse / topology
                         |
                         v
                    R6 规模与产品
```

动态拓扑不是当前第一优先级。若状态类型和 READ 合同未固定，拓扑搜索只会在不稳定目标上扩大
搜索空间。

# 后续怎样逐项审查

以后检查表中任意一项，统一使用下面的模板：

```text
概念名称：
正式输入/输出：
当前代码路径：
当前证据路径：
最强已支持结论：
明确未支持结论：
matched baselines：
干预方法：
资源预算：
通过门：
失败后如何处理：
```

若一项无法填写“正式输入/输出”，它仍是 M0 概念；无法填写 matched baseline，它最多是 M2
组件；没有因果干预，不能升为 M3；没有进入统一主链，不能称为 TreeHeap 完整能力。

{{< claim id="SPR-092-ROADMAP" status="registered" >}}
TreeHeap 下一阶段停止扩张核心术语，优先完成 canonical TreeState、context-conditioned WRITE、
残差 matched controls 和无旁路 READ-Decoder 闭环。只有通过这些接口门和因果门的概念，才进入
动态拓扑、稀疏运行时与规模训练。
{{< /claim >}}

# 最后结论

TreeHeap 当前最稀缺的不是新概念，也不是更多训练时长，而是**把已有概念压缩成少数可替换、
可比较、可串联的算法接口**。

最短主线只有四个动作：

```text
WRITE -> FOLD -> READ -> DECODE
```

背景场、残差、Lifting、Butterfly 和私有协议，都必须明确自己在这四个动作中的位置。找不到位置的
概念暂存；占据相同位置的算法做 matched comparison；通过因果门的实现才进入下一层。

这张表不是给过去的工作判分，而是保护未来研发：我们仍然可以大胆提出问题，但每一个新词最终
都必须落成数据结构、函数签名、对照实验和可以失败的门。

> **License: GPLv3。路线图、Claim、证据边界与后续实验合同随 SameTime / TreeHeap 项目公开。**
