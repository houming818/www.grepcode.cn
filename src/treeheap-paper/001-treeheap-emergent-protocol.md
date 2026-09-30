---
title: "TreeHeap：概率下坠、多分辨率状态与可训练生成协议"
date: 2026-08-02
lastmod: 2026-09-28
weight: 1
author: Houming818 & Trinity (Codex)
description: "TreeHeap 当前完整理论与可计算教程：从概率背景场和 token 下坠出发，用 toy、LaTeX 定义和有限证明解释局部主轴、Monte Carlo、FOLD、READ、Decoder、私有协议、证据边界与研发路线。"
keywords: [TreeHeap完整论文, 概率Embedding, 下坠模型, Monte Carlo, F函数, FOLD, UNFOLD, READ, 多分辨率状态, 私有协议, 消费级AI]
tags: [TreeHeap, Paper, Architecture, Probability, Embedding, Mathematics, Evidence, Reproducibility]
ShowToc: true
TocOpen: true
---

**English title:** *TreeHeap: Probabilistic Falling, Multiresolution States, and a Trainable Generative Protocol*

**状态：** 当前理论整合稿 v0.8，2026-09-28\

**作者：** Houming818（Independent Researcher）

**研究协作：** Houming818 与 Trinity（Codex）

**代码与证据：** SameTime / ARA，GPL-3.0

**阅读方式：** 本文维护当前理论全貌。数字编号的 [SPR 系列](/spr/) 保存研究过程、失败实验与证据演化；旧结论只在解释当前设计或证据边界时作为 reference 引入。

## 摘要

TreeHeap 研究一种不同于“先随机放置 token 向量，再交给多层网络变换”的表示路径：先从语料统计每个 token 的条件背景分布，再让 token 从 TreeHeap 的 root 开始，以局部概率决策逐层下坠，最终形成 leaf 概率、路径概率和多分辨率节点质量。Embedding 因而不是一张先验给定的地址表，而是 token 与已有背景场相互作用后形成的结构化概率状态。

在当前算法中，token `t` 首先由上下文统计得到 `p(c|t)`，并使用与 Hellinger 几何相容的平方根坐标。每个内部节点拥有局部观察轴、阈值和温度，计算左右分支概率。全部节点函数组成整树映射；Monte Carlo、梯度下降和拓扑搜索则是寻找节点参数的学习算法，不是映射本身。节点以概率质量加权形成 context prototype，child 与 parent 的差构成可审计残差。该结构已经能够被搜索、保存、重载和分层读取，但尚未证明自己是最终语义空间。

完整生成架构还要求解决更困难的问题：把 token type 的背景坐标变成句中 occurrence 状态；设计一个在相同状态族中闭合、同时又能区分 `AB` 与 `BA` 的序列 FOLD；让 READ 根据生成 query 选择 coarse 或 fine 状态；最后由 Decoder 形成输出分布。我们当前采用“coarse 较稳定、fine 保留更多未决可能性”的概率性假设，并明确区分表征中的不确定性与 Decoder sampling 产生的不确定性。

现有证据支持一个有限结论：概率背景场可以在 TreeHeap 中形成非随机、可重载、含有预测信息的多分辨率划分；局部路由既可以由 Monte Carlo 搜索，也可以由梯度更新；更深状态在登记实验中保留了更多背景预测信息。现有证据不支持：已经找到唯一 F、已经完成保序序列 Encoder、已经形成完整 Encoder/Decoder 私有协议，或已经获得优于 Transformer 的产品质量和计算优势。

因此，TreeHeap 当前不是完成品，也不是只有类比的设想。它已经收敛为一个可逐项实现和反驳的架构任务：以概率下坠建立表示，以闭合且保序的 FOLD 建立句子状态，以分辨率感知 READ 连接 Decoder，并在消费级 GPU 上完成可恢复的端到端训练。

![TreeHeap 当前端到端架构：绿色是已有有限证据，橙色是核心算法缺口，蓝色是待接通模块](/images/treeheap-paper/end-to-end-map.svg)

## 0. 先用一个最小 toy 看懂全链路

这一节先不讨论大模型。我们只使用 4 个 token、4 个上下文维度和一棵深度为 2 的二叉树。它的目的不是证明 TreeHeap 已经理解语言，而是让后文每个符号都有一个可以手算的对象。

### 0.1 Toy 语料与概率背景

假设词表中只有：

```text
苹果 apple    梨 pear    汽车 car    公交车 bus
```

我们只观察四类上下文：

```text
甜 sweet    吃 eat    行驶 drive    道路 road
```

计数并归一化后，得到条件概率表：

| token | sweet | eat | drive | road |
|---|---:|---:|---:|---:|
| apple | 0.50 | 0.40 | 0.05 | 0.05 |
| pear  | 0.45 | 0.45 | 0.05 | 0.05 |
| car   | 0.05 | 0.05 | 0.50 | 0.40 |
| bus   | 0.05 | 0.05 | 0.40 | 0.50 |

于是 apple 的背景状态是：

$$
p_{\text{apple}}=(0.50,\,0.40,\,0.05,\,0.05),
\qquad \sum_{k=1}^{4}p_{\text{apple},k}=1.
$$

这里的坐标不是“apple 本身的全部意义”，而是语料给出的四个条件概率。pear 与 apple 接近，car 与 bus 接近，这是语料统计产生的，不是我们先写进 token ID 的。

为了在概率分布之间使用具有统计含义的欧氏几何，令：

$$
x_t=\sqrt{p_t}
=\left(\sqrt{p_{t,1}},\ldots,\sqrt{p_{t,K}}\right).
$$

两个 token 的 Hellinger 距离为：

$$
H(p,q)=\frac{1}{\sqrt 2}\lVert \sqrt p-\sqrt q\rVert_2.
$$

因此，在平方根坐标中做欧氏距离计算，并不是随意选择一种向量技巧；它等价于比较两个离散概率分布的 Hellinger 距离。

### 0.2 Toy Tree：每个节点问一个局部问题

设 root 的观察轴为：

$$
w_0=(1,1,-1,-1), \qquad b_0=0.
$$

它大致在问：“这个 token 更像食物上下文，还是交通上下文？”节点分数和右路由概率定义为：

$$
z_0(t)=x_t^{\mathsf T}w_0-b_0,
\qquad
g_0(t)=\sigma\!\left(\frac{z_0(t)}{\tau_0}\right),
$$

其中：

$$
\sigma(u)=\frac{1}{1+e^{-u}}.
$$

`g=0.5` 表示节点暂时不能区分两侧，`g` 接近 0 或 1 表示路由更确定。它不是 token 的最终输出概率，只是这个节点的局部分支概率。

第二层使用不同的观察轴。例如，左子树可以比较 `sweet` 与 `eat`，右子树可以比较 `drive` 与 `road`：

$$
w_L=(1,-1,0,0),
\qquad
w_R=(0,0,1,-1).
$$

这就是“局部主轴”的最小含义：不同节点面对的候选集合不同，因此允许提出不同的分类问题。若所有节点共享完全相同的轴，深树可能只会反复回答同一个问题。

### 0.3 一次软下坠怎样得到 4 个 leaf

为了便于手算，假设某个 token 在 root 的右路由概率是 `0.8`；到左子节点时右路由概率是 `0.25`；到右子节点时右路由概率是 `0.75`。从 root 的单位质量开始：

$$
m_{\varnothing}(t)=1.
$$

每经过一个节点，质量按概率分裂：

$$
m_{vL}(t)=m_v(t)\bigl(1-g_v(t)\bigr),
\qquad
m_{vR}(t)=m_v(t)g_v(t).
$$

深度 2 的四个 leaf 质量为：

$$
\begin{aligned}
m_{LL}&=(1-0.8)(1-0.25)=0.15,\\
m_{LR}&=(1-0.8)(0.25)=0.05,\\
m_{RL}&=(0.8)(1-0.75)=0.20,\\
m_{RR}&=(0.8)(0.75)=0.60.
\end{aligned}
$$

因此 token 的 soft leaf Embedding 是：

$$
e_t=(0.15,\,0.05,\,0.20,\,0.60)\in\Delta^3.
$$

它不是“选中一个地址就结束”。它保留了 token 对全部 leaf 的概率质量。hard routing 则取最大路径，在本例中落到 `RR`；soft routing 保留了“主要在 RR，但仍有其他可能”的状态。

![深度二概率下坠 toy：单位质量按局部条件概率分裂为四个 leaf](/images/treeheap-paper/toy-probability-fall.svg)

### 0.4 命题一：下坠质量守恒

**命题。** 若 root 质量为 1，且每个节点都按 `g` 与 `1-g` 分配质量，其中 $g\in[0,1]$，则任意深度 $d$ 的全部节点质量之和均为 1。

**证明。** 深度 0 时只有 root，因此总质量为 1。假设深度 $d$ 的总质量为：

$$
\sum_{v\in V_d}m_v=1.
$$

每个 $v$ 在下一层产生两个 child，且：

$$
m_{vL}+m_{vR}
=m_v(1-g_v)+m_vg_v
=m_v.
$$

于是：

$$
\sum_{u\in V_{d+1}}m_u
=\sum_{v\in V_d}(m_{vL}+m_{vR})
=\sum_{v\in V_d}m_v
=1.
$$

由数学归纳法，对任意有限深度成立。$\square$

这个证明只说明数值质量不会凭空增加或消失。它**没有证明语义守恒**，也没有证明这种路由优于其他 Embedding。

### 0.5 多分辨率状态到底是什么

深度 0 只有一个 root 质量：

$$
m^{(0)}=(1).
$$

深度 1 有两个 coarse 区域：

$$
m^{(1)}=(0.20,\,0.80).
$$

深度 2 有四个 fine 区域：

$$
m^{(2)}=(0.15,\,0.05,\,0.20,\,0.60).
$$

这里“多分辨率”不是把一个 float 放大或缩小。它是同一单位质量在不同分区粒度上的边缘分布，并满足：

$$
m_v=m_{vL}+m_{vR}.
$$

所以 coarse 可以由 fine 精确求和得到；但只知道 coarse 的 `0.20`，不能唯一恢复它原来是 `(0.15,0.05)`、`(0.10,0.10)`，还是其他组合。低分辨率到高分辨率天然是一对多问题。

![同一状态在 root、coarse 与 fine 层的概率表示，以及 query 条件 READ](/images/treeheap-paper/coarse-fine-read.svg)

### 0.6 命题二：概率 parent 仍在同一个单纯形

设两个 child 的背景概率分别为 $p_L,p_R\in\Delta^{K-1}$，质量为 $m_L,m_R\ge 0$。定义 parent prototype：

$$
p_P=\frac{m_Lp_L+m_Rp_R}{m_L+m_R},
\qquad m_L+m_R>0.
$$

**命题。** $p_P\in\Delta^{K-1}$。

**证明。** 因为 $p_L,p_R$ 各维非负，$p_P$ 各维也非负；并且：

$$
\sum_{k=1}^{K}p_{P,k}
=\frac{m_L\sum_kp_{L,k}+m_R\sum_kp_{R,k}}{m_L+m_R}
=\frac{m_L+m_R}{m_L+m_R}=1.
$$

因此 parent 与 child 仍是同一种概率数据类型。$\square$

这就是当前“量纲自洽”的最低数学地基。它仍未解决顺序，也不能保证 parent 对生成任务足够。

### 0.7 残差能恢复什么，不能恢复什么

定义：

$$
r_L=p_L-p_P,
\qquad
r_R=p_R-p_P.
$$

只要保存 $p_P,r_L,r_R$，就有：

$$
p_L=p_P+r_L,
\qquad
p_R=p_P+r_R.
$$

这是代数上的精确恢复。然而，如果只保留 $p_P$ 而丢弃残差，就不能恢复两个 child。更重要的是，`可恢复 child 概率` 不等于 `可以生成原句`：原句还包含顺序、位置、上下文角色和 Decoder 协议。

### 0.8 命题三：对称平均不可能表达词序

若序列 FOLD 仅使用对称加权平均：

$$
F(a,b)=\frac{m_ap_a+m_bp_b}{m_a+m_b},
$$

则交换输入后：

$$
F(b,a)=\frac{m_bp_b+m_ap_a}{m_b+m_a}=F(a,b).
$$

因此它不能区分 `AB` 与 `BA`。这不是训练不够，而是函数本身具有交换性。若任务要求区分“狗咬人”和“人咬狗”，FOLD 至少必须引入位置、角色、非交换算子或有方向的残差。

这个结论解释了为什么“概率 Embedding 已经形成”并不等于“序列 Encoder 已经完成”。

### 0.9 Monte Carlo 在搜索什么

令整棵树参数为：

$$
\Theta=\{w_v,b_v,\tau_v\}_{v\in\mathcal V}.
$$

给定一个可计算目标 $J(\Theta)$，例如邻域保持、负载均衡、masked context 预测和复杂度惩罚的组合：

$$
J(\Theta)
=\lambda_1J_{\text{neighbor}}
+\lambda_2J_{\text{balance}}
+\lambda_3J_{\text{masked}}
+\lambda_4J_{\text{complexity}}.
$$

一次 Monte Carlo 提议可以只扰动一个节点：

$$
\Theta'=\Theta+\varepsilon,
\qquad
\varepsilon_v\sim\mathcal N(0,\sigma^2I).
$$

模拟退火式接受概率为：

$$
P(\Theta\rightarrow\Theta')
=\min\left(1,
\exp\left[-\frac{J(\Theta')-J(\Theta)}{T}\right]
\right).
$$

若新参数更好，必然接受；若更差，仍可能以随温度 $T$ 降低的概率接受，从而避免立即困在局部极值。这里得到的是**搜索算法**，不是 TreeHeap 正确性的证明。它只能回答：“在给定状态、算子集合和目标函数下，能否找到通过门禁的参数？”

### 0.10 Toy READ 与 Decoder 怎样接上

假设一句话经过 Encoder/FOLD 后，在三个分辨率得到状态：

$$
h^{(0)}\in\mathbb R^d,
\qquad
h^{(1)}\in\mathbb R^d,
\qquad
h^{(2)}\in\mathbb R^d.
$$

Decoder 在第 $j$ 个生成位置持有 query $q_j$。一个最小的分辨率 READ 可以先计算：

$$
a_{j,d}
=\frac{\exp\!\left(q_j^{\mathsf T}W_Rh^{(d)}\right)}
{\sum_{r=0}^{D}\exp\!\left(q_j^{\mathsf T}W_Rh^{(r)}\right)},
$$

再读出：

$$
r_j=\sum_{d=0}^{D}a_{j,d}h^{(d)}.
$$

若当前正在决定句子主题，模型可能给 coarse 层更大权重；若正在决定具体名词或词尾，可能给 fine 层更大权重。这是待训练和审计的行为，不是人工规定的语言规律。

Decoder 把读出状态映射到词表 logits：

$$
\ell_j=W_Dr_j+b_D,
\qquad
P(y_j=k\mid y_{\lt j},x)
=\frac{e^{\ell_{j,k}}}{\sum_{u\in\mathcal V}e^{\ell_{j,u}}}.
$$

如果目标 token 为 $y_j^*$，交叉熵为：

$$
\mathcal L_j=-\log P(y_j^*\mid y_{\lt j},x).
$$

只要路由、FOLD、READ 和 Decoder 都处在同一个可微计算图中，链式法则给出：

$$
\frac{\partial\mathcal L_j}{\partial\theta_v}
=\frac{\partial\mathcal L_j}{\partial\ell_j}
\frac{\partial\ell_j}{\partial r_j}
\frac{\partial r_j}{\partial h^{(d)}}
\frac{\partial h^{(d)}}{\partial\theta_v}.
$$

这说明“不共享参数”不等于“不能形成协议”。READ 参数与 Encoder 参数可以不同，但同一个 loss 会同时约束双方。是否真的形成了私有协议，还必须用输入置乱、层级消融、旁路检查和 checkpoint 重载来验证。

### 0.11 从 toy 到真实系统，还缺哪三步

这个 toy 已经解释了：

1. 语料怎样形成概率背景坐标；
2. 节点怎样把单位质量逐层下坠；
3. parent 怎样保持概率类型，残差怎样保留 detail。

它还没有解释：

1. 同一个 `bank` 在不同句中怎样得到不同 occurrence state；
2. `AB` 怎样在不丢失必要顺序的条件下 FOLD；
3. Decoder 怎样从 coarse/fine 状态生成多个连续 token。

后文的架构正是为了逐项补上这三处断点。读到任何公式时，都可以回到这个 toy，确认它在处理的是背景概率、路由质量、序列状态，还是输出分布。

## 1. 研究问题

### 1.1 为什么不把 TreeHeap 简化为“树形神经网络”

树形状本身只提供地址、父子关系、路径和递归深度。它不会自动提供语义，也不会因为 root 覆盖更多 leaf，就自动成为一句话的摘要。

TreeHeap 真正研究的是四个相互依赖的问题：

1. **表示从哪里来：** token 怎样从语料观测形成可计算坐标，而不是被随机摆放？
2. **分辨率是什么：** root、parent、leaf 怎样表示同一对象的不同分辨率，而不是不同类型的杂乱张量？
3. **组合怎样发生：** 两个有顺序的状态怎样形成 parent，同时保留目标任务需要的信息？
4. **状态怎样被消费：** READ 和 Decoder 怎样通过训练学会使用这些状态，而不是绕过 TreeHeap？

### 1.2 核心研究假设

当前理论由五个可被修改的假设组成。

**假设 H1：概率背景假设。** token 的意义至少部分表现为它对上下文候选空间施加的概率约束。

**假设 H2：下坠构造假设。** 一个 token 的 Embedding 可以由 root-to-leaf 的局部条件决策构造，而不是必须先给出一个任意向量。

**假设 H3：多分辨率不确定性假设。** coarse 状态保存较稳定的共同约束，fine 状态保留更多局部差异和未决可能性。

**假设 H4：同状态族闭合假设。** Embedding、FOLD 与 READ 若处理同一个多分辨率对象，其输入输出应保持明确的数据类型、概率归一化和量纲合同。

**假设 H5：私有协议假设。** Encoder、READ 和 Decoder 不必共享参数，但可以通过端到端梯度形成一套共同使用的内部表示规则。

本文不会把这些假设写成自然定律。每个假设都需要独立的算法和反证条件。

### 1.3 当前目标，不是历史路线

本文主线是当前目标架构：

```text
corpus observations
  -> token background field
  -> root-to-leaf probabilistic Embedding / UNFOLD
  -> occurrence state with order and context
  -> same-state-family sequence FOLD
  -> multiresolution TreeState
  -> resolution-aware READ
  -> Decoder distribution
  -> generated sequence
```

过去的 ID 路由、随机角色基、可逆 Lifting、XOR-Butterfly、STOP gate 和 WMT 翻译 checkpoint，只在它们对当前合同仍有解释力时作为 reference。它们不再单独定义理论路线。

## 2. 数据对象：从 token 到概率背景场

### 2.1 Token ID 不是语义坐标

token ID 是词表索引。编号 100 与 101 相邻，不代表两个 token 在语言中更接近。直接对 ID 做加减、Hash 或二进制分路，可以得到稳定地址，却不能自动得到语义关系。

还必须区分两种对象：

- `token type`：词表中的抽象单位，例如 `bank`；
- `token occurrence`：某一句、某个位置实际出现的 `bank`。

背景 Embedding 首先组织 type。句子 Encoder 必须在此基础上构造 occurrence，否则一词多义、顺序、指代和组合语义都没有进入状态。

### 2.2 条件背景分布

从语料统计 token `t` 周围 context `c` 的出现次数，经平滑和归一化得到：

$$
p_t(c)=P(\mathrm{context}=c\mid \mathrm{token}=t).
$$

因此一个 token 的基础观测不是整数，而是一行概率：

$$
p_t=\left[P(c_1\mid t),P(c_2\mid t),\ldots,P(c_K\mid t)\right],
\qquad p_t[k]\ge 0,
\qquad \sum_{k=1}^{K}p_t[k]=1.
$$

所有 token 行位于同一个概率单纯形中，具有相同维度和单位。它描述的是分布式上下文，不是完整语义，也不是句子 hidden state。

### 2.3 平方根概率坐标

路由使用：

$$
x_t=\sqrt{p_t}.
$$

逐维开平方后，欧氏距离与 Hellinger 距离相容。这样，两个条件分布之间的几何距离有明确概率含义，避免直接在 token ID 或任意随机坐标上寻找主轴。

### 2.4 背景场

所有 `p_t`、节点统计、路径和原型共同组成当前的背景场。它记录语料中的共现规律，可以作为新 token 下坠时的参考系。

背景场目前不能被称为完整世界模型。它没有直接证明因果、物理规律、句法或长期记忆；它只是可复现的语料条件概率结构。

## 3. Embedding：root-to-leaf 概率下坠

### 3.1 节点函数

TreeHeap 的每个内部节点 `v` 拥有局部参数：

$$
\theta_v=\{w_v,b_v,\tau_v\}.
$$

其中 `w_v` 是局部观察轴，`b_v` 是阈值，`tau_v` 是温度。节点先计算：

$$
z_v(t)=x_t^{\mathsf T}w_v-b_v.
$$

硬路由为：

$$
z_v(t)\le 0\Rightarrow \mathrm{left},
\qquad
z_v(t)>0\Rightarrow \mathrm{right}.
$$

软路由保留两侧概率：

$$
g_v(t)=P(\mathrm{right}\mid t,v)
=\sigma\!\left(\frac{z_v(t)}{\tau_v}\right).
$$

### 3.2 质量下坠

token 从 root 携带单位质量开始：

$$
m_{\mathrm{root}}(t)=1.
$$

在节点 `v`：

$$
m_{vL}(t)=m_v(t)\bigl(1-g_v(t)\bigr),
\qquad
m_{vR}(t)=m_v(t)g_v(t).
$$

递归到全部 leaf 后，质量仍满足：

$$
\sum_{\ell\in\mathrm{Leaves}}m_\ell(t)=1.
$$

于是 token 的 leaf Embedding 为：

$$
e_t=\left[m_{\ell_1}(t),\ldots,m_{\ell_L}(t)\right].
$$

它既是一行概率，也是一组局部条件决策的乘积。对任意深度，把后代 leaf 质量相加，就得到该深度的节点概率。因此，一次下坠同时产生 leaf 坐标、路径坐标和多分辨率坐标。

### 3.3 局部主轴为什么必须因节点而异

所有节点共享同一种计算规则，但不应强制共享同一组 `w_v,b_v`。root 观察全局数据，child 只观察已经经过上游筛选的子群。每个节点重新计算或学习局部主轴，整棵树才形成分段的层级划分，而不是反复使用同一个超平面。

局部主轴当前优化的是背景重建或下游目标。不能仅凭轴存在，就把某一维命名为“主语”“生命”或其他人类语义特征。

### 3.4 背景先形成，新 token 再安装

已安装 token 在节点中形成质量、context prototype 和占用统计。新 token 到达时：

1. 读取当前节点的局部统计；
2. 计算左右分支概率；
3. 将质量递归传播到后代；
4. 用新观测更新经过节点的统计。

这构成 token 与背景场的双向关系：背景影响新 token 路径，新 token 又改变背景。

高频 token 先安装可以提高早期统计稳定性，但历史实验也表明，它可能损害分支利用率和预测质量。因此“频率优先”只是候选初始化策略，不是理论必需条件。

### 3.5 防拥挤与互斥压力

只有相似性吸引时，大量 token 可能进入少数分支。候选目标可以加入：

- 节点左右占用平衡；
- leaf 有效数量；
- 路由熵或容量惩罚；
- 正样本吸引与负样本排斥；
- 随深度变化的相似性和容量压力。

这些约束的职责是防止路径坍缩，而不是人工规定每个节点必须五五分流。当前没有一个已经被证明普适的互斥公式。

### 3.6 动态词表与渐进单位

理想情况下，基础 token、复合 token、短语和新词可以在同一背景场中依次安装，而不是各自建立无关空间。新单位读取已有背景后下坠，并在不立即扩展树深的情况下获得坐标。

目前仍未解决：新增 token 后怎样更新局部轴和原型，同时保证旧 token 路径不过度漂移。

## 4. F、整树映射与学习算法

### 4.1 术语合同：数据、结构、运算与扩容

历史讨论曾把“词的统计背景”“树上的位置”“FOLD 运算”和“参数搜索”混在一起，并把多种对象都简称为 F。后续论证统一使用下面的名称。

#### 4.1.1 数据对象

**基础输出字母表（base output alphabet）** $\Sigma$ 是 tokenizer 直接产生、Decoder 最终输出的基础 token 集。在一个实验版本内，$\Sigma$ 可以保持固定。

**多元组（n-gram）** 是语料中连续或按注册关系组合的 token 序列：

$$
g=(x_1,x_2,\ldots,x_n)\in\Sigma^*.
$$

多元组的一次出现只是一个训练事件，并不自动成为新词。

**注册语言单位（registered unit）** 是通过频率、预测增益和稳定性门禁后，被允许拥有独立统计量和 TreeHeap 坐标的对象。它可以是基础 token、复合词或短语，统一记为 $u$。

**动态内部语言单位集（internal unit vocabulary）** $U_t$ 是时刻 $t$ 已注册到 TreeHeap 的全部语言单位：

$$
U_t=\{u_1,u_2,\ldots,u_m\}.
$$

因此，“观察到二元组”和“内部词表新增一个二元单位”不是同一件事。只有执行注册操作 $U_{t+1}=U_t\cup\{g\}$，TreeHeap 的内部语言单位才真正扩大。$\Sigma$ 可以保持不变。

**context 基（context basis）** 是描述单位周围统计环境的坐标集合，记为 $C$。单位 $u$ 在该基上的条件概率行为写为：

$$
p_u(c)=P(c\mid u),\qquad c\in C.
$$

**背景场（background field）** 不是一个额外的大向量，也不是内部词表的别名。它是输出字母表、内部单位集、先验、条件概率行及其 TreeHeap 聚合状态构成的版本化统计系统：

$$
\mathcal B_t=\left(\Sigma,U_t,C_t,\{P(u)\}_{u\in U_t},\{p_u\}_{u\in U_t},G_t,\{p_v\}_{v\in G_t}\right).
$$

新增共现样本可以只更新固定单位集上的背景参数；只有新单位通过注册门禁时才扩充 $U_t$。前者不能被称为新概念形成。

内部单位不必直接进入基础 tokenizer。READ 若选择复合单位 $u$，可以通过确定性展开映射回基础输出序列：

$$
\operatorname{spell}:U_t\longrightarrow\Sigma^*.
$$

#### 4.1.2 树结构

**节点（node）** 是 TreeHeap 中保存质量、prototype 或残差状态的位置，记为 $v$。`leaf` 是最细粒度注册单位的落点，`parent` 是一个或多个 child 经 FOLD 后形成的组合状态，`root` 是当前树的最粗粒度状态。

**地址（address）** 是节点在固定拓扑中的静态坐标，例如深度和左右分支序列：

$$
a(v)=(d,b_1,b_2,\ldots,b_d),\qquad b_i\in\{L,R\}.
$$

**路由（route）** 是某个单位在各节点上作出的分支选择。地址描述“节点在哪里”，路由描述“单位选择了哪条分支”。在简单二叉树中二者可以写成相同的 `L/R` 序列，但概念不同。

**递归路径（recursive path）** 是从 root 到目标状态实际经历的节点函数、中间状态和残差序列。它包含计算历史：

$$
\pi(u)=\big[(v_0,h_0),(f_{v_0},r_0),\ldots,(v_d,h_d)\big].
$$

两个单位可以到达同一静态地址，却因软路由权重、节点参数或中间状态不同而具有不同递归路径。因此，证明 address 有效不自动证明 recursive path 具有独立因果性。

**节点 prototype** $p_v$ 是节点内注册单位条件概率行的质量加权聚合；**detail/residual** $\delta_v$ 是 child 相对 parent 未被粗粒度状态解释的差异。第五节给出它们的正式定义。

#### 4.1.3 运算符

**节点函数**：

$$
f_v(x;\theta_v).
$$

它在单个节点上计算局部路由、状态变换或残差分配。

**整树映射 F**：

$$
F_{G,\Theta}=\mathop{\mathrm{Compose}}_{v\in\mathcal V(G)}f_v(\,\cdot\,;\theta_v).
$$

它在给定拓扑 $G$ 上组合所有节点函数，把输入映射为 route、leaf 坐标和多层状态。$\Theta$ 是节点参数集合。本文所说的“搜索 F”，主要指寻找合适的函数族、拓扑和参数，而不是搜索一个单独标量公式。

**FOLD** 是把 child 状态组合成 parent，并按协议产生或保留 detail 的局部运算。**UNFOLD** 是利用 parent、detail 和 address 恢复下一层状态的闭合运算。FOLD/UNFOLD 回答“递归状态是否保存信息”。

**READ** 根据 query 和读取预算，从一个或多个层级取出任务状态。**Decoder** 把 READ 状态转换为输出 token 分布。READ/Decoder 回答“已保存的信息能否支持具体任务”。数值闭合、有效 READ 和语言生成是三个不同的 Claim。

**学习算法 A**：

$$
\mathcal A(D,F_{G,\Theta})\longrightarrow(G',\Theta').
$$

它根据数据 $D$ 搜索或训练拓扑与参数。Monte Carlo、梯度下降和拓扑搜索属于 $\mathcal A$，不属于 $F_{G,\Theta}$ 本身。一次搜索失败不等于整个 F 函数族错误；一个 F 可微，也不表示当前 loss 能找到有用参数。

#### 4.1.4 三种扩容动作

**内部语言单位扩容** 是注册新的语言单位：

$$
U_{t+1}=U_t\cup G_{\mathrm{accepted}}.
$$

**背景参数更新** 是在 $U_t$ 不变时，用新样本更新已有 $P(u)$、$P(c\mid u)$、节点质量和沿途 prototype/residual。它可以持续改善已有单位，但不能产生新的复合语言单位。

**背景场扩容** 要求至少增加新的注册单位及其概率行、TreeHeap route 和 `spell` 规则。若只改变旧概率表，应称为参数更新，而不是背景场扩容。

**拓扑扩容** 是在节点容量、冲突率或读取误差越过门槛后执行分裂或加深：

$$
G\longrightarrow G'.
$$

内部单位扩大不要求整棵树立即加深；背景参数更新也不等于新增节点。工程上应优先做沿 route 的局部统计更新，只有局部容量不足时才改变拓扑。这样才能分别测量：新增的是语言单位、统计信息，还是结构容量。

### 4.2 Monte Carlo 搜索硬树

硬树的 Monte Carlo 搜索固定深度和状态定义，反复执行：

1. 随机选择一个节点；
2. 对其观察轴或阈值提出局部扰动；
3. 让受影响 token 重新下坠；
4. 重新计算节点原型；
5. 在封存的 dev 共现数据上计算重建 NLL；
6. 接受更优方案，并以退火概率接受少量更差方案。

设新旧目标差为：

$$
\Delta J=J_{\mathrm{new}}-J_{\mathrm{old}}.
$$

一个典型接受规则是：

$$
P(\mathrm{accept})=
\begin{cases}
1, & \Delta J\le 0,\\
\exp(-\Delta J/T), & \Delta J>0.
\end{cases}
$$

温度 `T` 随搜索降低。该方法的优点是路径、节点与概率守恒都能直接审计；缺点是高维提案效率较低，离散重路由也不能直接利用梯度方向。

搜索目标当前主要是未见背景 context 的重建 NLL。它优化的是 token 分区几何，不是一般句子组合公式。

### 4.3 梯度训练软树

软路由保留全部路径概率，loss 可以对 `w_v,b_v,tau_v` 求导。这样，普通优化器能够更新节点轴和阈值，也可以接收 READ 或 Decoder 的下游梯度。

软树的主要风险是训练与部署不一致。训练时多个路径共同承载信息，若结束后突然以 `0.5` 阈值硬化，混合状态会被切断。当前理论因此不要求立刻硬化，而是先建立软模型的应用门，再研究 Top-k、稀疏概率和 soft/hard 一致性训练。

### 4.4 拓扑与参数联合搜索

节点参数是连续变量，父子连接和组合顺序是离散变量。若同时搜索二者，问题成为混合优化：

$$
\min_{G,\Theta}
\left[
\mathcal L_{\mathrm{task}}(F_{G,\Theta})
+\lambda\,C_{\mathrm{structure}}(G,\Theta)
\right].
$$

人工比较 balanced、left-deep、right-deep 能说明拓扑影响结果，却不能证明模型能自己找到拓扑。动态拓扑不是当前第一优先级；统一状态和 READ 合同未固定前，搜索更大拓扑只会扩大不稳定目标。

## 5. 多分辨率概率状态

### 5.1 节点质量与 prototype

设节点 `v` 下 token 的质量为 `a_t,v`，其 context 概率行为 `p_t`。节点总质量与原型为：

$$
M_v=\sum_t a_{t,v},
\qquad
\mu_v=\frac{\sum_t a_{t,v}p_t}{M_v}.
$$

`mu_v` 与 token 背景行具有同一维度、同一概率单位。root 表示全局混合背景；向下进入更小子群后，prototype 增加区分信息。

### 5.2 概率 FOLD

对左右 child：

$$
M_P=M_L+M_R,
\qquad
\mu_P=\frac{M_L\mu_L+M_R\mu_R}{M_P}.
$$

它满足质量守恒：

$$
M_P\mu_P=M_L\mu_L+M_R\mu_R.
$$

parent 仍位于同一概率单纯形，因此该 FOLD 在数据类型和量纲上闭合。

### 5.3 概率残差

child 相对 parent 的残差为：

$$
\delta_C=\mu_C-\mu_P.
$$

沿 root-to-node 路径累加：

$$
\mu_v=\mu_{\mathrm{root}}+
\sum_{C\in\mathrm{path}(\mathrm{root}\to v)}\delta_C.
$$

可以精确恢复已存储的节点 prototype。对单 token 还可保存：

$$
\delta_t=p_t-\mu_{\ell(t)}.
$$

这能恢复完整 token 背景行，也能测量 TreeHeap 量化丢失的信息。

残差目前是代数差，不是独立学会的记忆。精确恢复证明数据没有丢失，不证明 parent 已获得生成所需语义。

### 5.4 coarse 与 fine

当前采用的概念是：

$$
\begin{aligned}
\mathrm{coarse\ state}&=\mathrm{larger\ support}+\mathrm{shared\ constraints},\\
\mathrm{fine\ state}&=\mathrm{smaller\ support}+\mathrm{additional\ distinctions}.
\end{aligned}
$$

coarse 不等于数值更小，fine 不等于向量更长。分辨率由状态能排除多少候选、能区分多少结构以及覆盖哪些 occurrence 决定。

### 5.5 分辨率不确定性假设

当前待验证假设是：coarse 路由可以较集中、较稳定，而 fine 路由保留多个可能分支。对 token `x` 在深度 `d` 的节点分布：

$$
p_d(v\mid x)=
\sum_{\ell\in\mathrm{Leaves}(v)}e_x(\ell).
$$

需要逐层测量：

- 节点熵；
- 条件分支熵；
- calibration；
- posterior concentration；
- 有效 leaf 数；
- 对下游目标的条件信息。

这些指标不等价。更深层背景预测更好，不自动证明 fine 更随机或更确定。

### 5.6 两种不同的不确定性

必须分开：

1. **表征不确定性：** Decoder 运行前，TreeHeap 状态已在多个 fine 分支分配概率；
2. **采样不确定性：** Decoder 形成 logits 后，生成策略从词表概率中采样。

目标是允许 coarse 含义稳定，而措辞、局部细节或等价表达在 fine 层保留多个实现。不能用增加 sampling temperature 代替表示层面的验证。

## 6. 统一 TreeState 合同

### 6.1 为什么需要统一状态

当前概率路线使用归一化 context 分布，历史序列路线使用普通 hidden vector，可逆 Lifting 又使用 parent/detail 对。如果这些对象只因 tensor shape 相同就互相连接，FOLD 的物理含义和 READ 的输入合同都会消失。

当前目标数据结构为：

```text
TreeState {
  common    // 当前尺度稳定保留的公共成分
  detail    // 区分更细状态所需的残差
  mass      // 概率质量或证据量
  address   // 节点、深度和路径
  order     // 序列位置、方向或非交换关系
  support   // 当前状态覆盖的 occurrence 范围
}
```

字段是否都显式存储可以调整，但每类信息必须有明确去处。

### 6.2 闭合要求

对状态族 `S`：

$$
s_L,s_R\in\mathcal S
\quad\Longrightarrow\quad
\operatorname{FOLD}(s_L,s_R)\in\mathcal S.
$$

若发生类型变化，必须显式命名新的空间和转换，而不能继续称为同一种 TreeState。

闭合只保证规则自洽，不保证可逆、语义正确或任务充分。

## 7. 从概率 FOLD 到保序序列 FOLD

### 7.1 当前概率平均为什么不够

质量加权平均满足：

$$
\operatorname{FOLD}(a,b)=\operatorname{FOLD}(b,a).
$$

它可以描述两个 token 共同覆盖的背景，却无法区分 `dog bites man` 与 `man bites dog`。因此它是概率状态基线，不是完整序列 Encoder。

### 7.2 occurrence WRITE

序列 Encoder 的输入不能只有静态 type Embedding。需要由当前句子构造 posterior occurrence：

$$
s_i=\operatorname{WRITE}\!\left(
e_{t_i},\operatorname{pos}_i,c_i,d_{\mathrm{task}}
\right).
$$

同一个 token 在不同句子中可以得到不同 `s_i`，同时保留与 type 背景场的可追踪关系。

### 7.3 保序 FOLD 的最低合同

完整候选至少应具有：

$$
s_P=\operatorname{Normalize}\!\left(
C(s_L,s_R)+O(s_L,s_R)+D(s_L,s_R)
\right),
$$

其中 $C$ 表示公共成分，$O$ 表示有序交互，$D$ 表示保留的 detail。

它必须满足：

1. `FOLD(a,b)` 与 `FOLD(b,a)` 在需要时可区分；
2. parent 仍属于声明的状态族；
3. 数值随深度不爆炸、不消失；
4. 梯度能到达左右 child 与节点参数；
5. detail 不能成为绕过 parent 的原文直通通道；
6. 不同深度具有可测量的分辨率变化。

当前尚无一个被接受的算子同时完成这些要求。这是主架构最大的算法缺口。

### 7.4 可逆性与任务充分性

历史可逆 Lifting 证明了：parent 与 detail 可以精确恢复两个 child。该结果仍是有价值的 reference，但不再等同于当前目标。

生成任务更核心的条件是：

$$
p(Y\mid X)\approx p(Y\mid P),
\qquad P=\operatorname{FOLD}(X).
$$

其中 `P=FOLD(X)`。parent 可以是有损的，只要它保留目标 `Y` 所需的条件分布；反之，精确可逆也可能只是把无关输入搬进 detail。

因此当前目标是“可审计的目标充分压缩”，而不是要求每层都能无损还原整句。

### 7.5 Butterfly 的当前位置

XOR-Butterfly 能让远距离 leaf 在对数阶段建立通信路径，历史 WMT 实验也显示它在指定合同中优于两个对照。它解决的是长程通信，不解决 Embedding、概率闭合或保序 FOLD。

在当前架构中，Butterfly 是可选通信模块。只有当统一 TreeState 与 FOLD 合同固定后，才能判断它应放在 FOLD 前、层间还是由其他稀疏通信替代。

## 8. READ、Decoder 与私有协议

### 8.1 READ 的目标

READ 接收 Decoder 当前 query，从 root、internal、leaf 与 detail 中选择或混合状态：

$$
r_t=\operatorname{READ}(q_t,\mathcal S_{\mathrm{tree}}).
$$

理想 READ 可以先使用 coarse 状态，再只展开当前 query 需要的 fine 分支。它不是机械走到 leaf，也不要求每层贡献相同。

### 8.2 两类已有 READ

冻结 Bayesian READ 使用观测 context 与背景条件分布比较候选 token。它证明多分辨率概率场含有可读信息，但不是自由生成 Decoder。

历史递归 READ 根据 Decoder hidden state 分配 stop 与 branch 概率。它证明多层读取可以参与 seq2seq，但 STOP 曾发生向 leaf 坍缩，也尚未与最新概率 Embedding 使用同一 TreeState。

二者都是 reference，不是已经合并的最终 READ。

### 8.3 Decoder

自回归 Decoder 的基本合同是：

$$
\ell_t=\operatorname{Decoder}(y_{\lt t},r_t),
\qquad
P(y_t)=\operatorname{softmax}(\ell_t).
$$

Decoder 不需要恢复一个人类命名的“主视角”，也不需要与 Encoder 共享参数。它需要能够读取 TreeState，并通过最终任务 loss 对上游状态形成方向信息。

### 8.4 私有协议的可检验定义

私有协议不是神秘语言。它表示 Encoder 产生的状态与 Decoder 的读取规则在训练中共同适配。

协议成立至少要求：

1. 输入变化造成 TreeState 与输出变化；
2. 干预某层状态会产生可预测的输出变化；
3. Decoder 不能仅靠目标前缀达到同样效果；
4. 梯度从任务 loss 到达 WRITE、FOLD 与路由参数；
5. checkpoint 保存和重载后行为一致；
6. 多 seed 下功能关系可复现，即使内部坐标可以旋转或置换。

## 9. 训练目标与梯度职责

### 9.1 分阶段目标

不同 loss 回答不同问题，不能只报告一个总数。

| 目标 | 保护的性质 |
|---|---|
| background reconstruction NLL | token 背景几何是否可预测 |
| routing utilization / entropy | 是否发生路径坍缩 |
| contrastive objective | 邻域吸引与互斥关系 |
| order discrimination | `AB` 与 `BA` 是否可区分 |
| closure / normalization | FOLD 后状态是否合法 |
| task token NLL | 状态能否被 Decoder 用于目标任务 |
| retention / replay | 新数据加入后旧背景是否遗忘 |
| generation gates | 输入因果、非空、重复率、长度与主观质量 |

### 9.2 端到端梯度链

目标链路为：

```text
generation loss
  -> Decoder
  -> READ
  -> sequence FOLD / communication
  -> occurrence WRITE
  -> probabilistic Embedding / node parameters
```

架构图不能证明梯度真实到达。正式训练必须记录各参数组的梯度范数、更新量、节点占用和逐层贡献。

### 9.3 门禁，不追求一次找到全局极值

当前采用可用性门禁：第一阶段只要求状态有限、概率守恒、可训练、可重载、比随机路由含有更多信息，并能可靠交给 READ。通过后再优化拓扑、稀疏度、速度和极值。

这避免为了寻找理论最优 F，无限制消耗单卡算力；也避免因一次局部负结果提前终止整个函数族。

## 10. 当前证据地图

### 10.1 已经建立的有限事实

| 对象 | 当前支持 |
|---|---|
| 背景概率场 | 可以从真实语料构造、冻结和重载 |
| 硬树搜索 | Monte Carlo 在登记数据上优于初始树和随机路由 |
| 软树训练 | 路由参数可微、可更新，路径可改变且不必坍缩 |
| 多分辨率读取 | 登记实验中，更深状态保留更多背景预测信息 |
| 概率 FOLD | 质量守恒、归一化闭合、残差可重建节点原型 |
| 双元概率组合 | 在有限未见三元组 smoke 中含有超出 unigram 的条件信息 |
| 顺序缺失 | 当前平均组合严格满足交换律，因此不含顺序 |
| 长程通信 reference | 历史 Butterfly WMT 匹配实验显示指定合同内稳定收益 |

### 10.2 代表性量化 reference

在硬树搜索中，深度 3、4、5、6 的多 seed sealed-test 重建 NLL 中位改善约为：

```text
depth 3: 0.0540
depth 4: 0.0451
depth 5: 0.0505
depth 6: 0.0296
```

这说明搜索到的分区不是完全随机摆放，但不能说明更深必然更好，也不能说明轴获得了人类可读语义。

在 READ-coupled 软路由实验中：

```text
soft field NLL: 4.758578
hardened NLL:   4.899335
damage:         0.140757
```

它把问题定位到 soft-to-hard 交接：信息存在于混合路径中，突然硬化会丢失它。

历史 Butterfly 三种子 WMT 对照的平均 NLL 为：

```text
Identity:   4.65196
Adjacent:   4.65415
Butterfly:  4.56509
```

这只作为长程通信模块的 reference，不证明最新概率 Embedding 与序列 FOLD 已经接通。

### 10.3 当前证据不允许的结论

本文不声称：

- token 已经获得完整语义坐标；
- 背景场已经是世界模型；
- 当前树结构对应自然语言语法树；
- 已经找到唯一或最终 F；
- soft 路由可以无损硬化；
- probability FOLD 已经编码语序；
- Encoder、READ 与产品 Decoder 已在最新架构中形成协议；
- 当前实现优于 matched Transformer；
- TreeHeap 已实现实际存储压缩或计算加速；
- 当前 checkpoint 达到产品级生成质量。

## 11. 当前最大断点

### 11.1 Type Embedding 到 occurrence Encoder

静态背景坐标必须被句内上下文改写，同时保持与背景场的可追踪关系。缺少这一层，token installer 不能直接承担句子理解。

### 11.2 概率状态到保序 FOLD

当前概率平均闭合但交换；已有可训练 hidden-state FOLD 可保序，却不属于同一概率状态族。需要找到二者之间的正式算子。

### 11.3 soft-to-sparse

软路由可训练但成本较高，硬化会损伤信息。需要逐步稀疏化、Top-k 路由或一致性蒸馏，而不是训练结束后突然二值化。

### 11.4 READ 到 Decoder 的无旁路闭环

Decoder 必须依赖登记的 TreeState 完成任务。任何 target leakage、leaf 直通或残差原文旁路都会使协议证据失效。

### 11.5 增量安装与遗忘

新 token、新语料或新任务进入背景场时，旧路径、原型和 READ 合同怎样保持，需要 replay、冻结层级或状态迁移算法。

## 12. 下一阶段算法路线

### 12.1 固定 canonical TreeState

首先定义字段、shape、单位、归一化、mask 和 checkpoint schema。概率 FOLD、保序 FOLD、Lifting reference 与 READ 都实现同一接口。

### 12.2 实现 context-conditioned WRITE

输入静态 type Embedding、位置和句内 context，输出 occurrence TreeState。先用受控多义词和顺序任务验证，不直接跳到大规模生成。

### 12.3 实现最小保序 FOLD

从双元开始，要求：

- `AB` 与 `BA` 可区分；
- 状态闭合；
- 梯度有限；
- parent 比 flat/random baseline 保留更多目标信息；
- detail 不形成旁路。

### 12.4 定义逐层分辨率曲线

同时记录节点熵、条件分支熵、有效 leaf、目标信息代理、顺序辨识率、READ 质量和生成变化。只用一个 NLL 无法说明多分辨率形成。

### 12.5 接入 resolution-aware READ

让 READ 在 query 条件下从 coarse 开始，按需展开 fine 状态。比较固定深度、全层平均、可学习软读取和稀疏读取。

### 12.6 串联 Decoder 并做因果审计

完成：

```text
probabilistic Embedding
  -> occurrence WRITE
  -> ordered FOLD
  -> multiresolution TreeState
  -> READ
  -> Decoder
```

随后进行 source shuffle、state shuffle、depth ablation、order reversal、reload equality 和 matched baseline。

### 12.7 在消费级硬件上形成 release

TreeHeap 的工程目标是在 24GB 级消费 GPU 上完成：

- 可恢复训练；
- 固定评测；
- checkpoint handoff；
- 本地 CLI 推理；
- model card、哈希与限制说明。

更大硬件可以验证尺度规律，但不能成为架构成立的前提。

## 13. Release 的定义与时间边界

“发布”必须分级，否则研究代码公开、研究 checkpoint 和可用模型会被混为一谈。

### R0：理论与研究代码发布

当前已经具备公开 Blog、ARA、组件代码和局部 checkpoint。本文本身属于这一层。

### R1：可复现研究原型

要求 canonical TreeState、最小 occurrence WRITE、保序 FOLD、READ/Decoder smoke、checkpoint reload 与 CLI 全部串联。若不出现新的基础反例，按单卡研发节奏估计需要 **4 到 8 周**。

### R2：可供外部试用的 TreeHeap 模型

要求真实语料训练、多 seed、matched baseline、稳定自由生成、model card 和一键推理。在 R1 成立之后，保守估计还需 **2 到 4 个月**。

### R3：具有产品意义的本地 AI

要求质量、速度、内存、增量学习、安全和长期维护均达到可用门槛。当前证据不足以给出可靠日期，不能把它承诺为某个固定月份。

这些是条件估计，不是日历保证。若保序 FOLD 或 soft-to-sparse 被反证，R1 时间需要重新计算；若现有组件顺利接通，则可以提前。

## 14. 反证条件

理论路线应被降级或修改，如果稳定出现以下结果：

1. 搜索或训练后的树长期不能胜过随机树、flat 概率模型或普通 Embedding；
2. 打乱 token 与背景概率行的对应关系后，READ 质量不下降；
3. 多个 seed 的功能关系无法复现，且坐标对齐后仍不存在共同结构；
4. 保序 FOLD 无法同时满足闭合、有限梯度和目标信息保留；
5. 任何可接受成本的稀疏化都会消除软路由收益；
6. Decoder 总能绕过 TreeHeap，结构干预不影响输出；
7. matched Transformer 或简单概率模型在同资源下稳定占优，而 TreeHeap 没有提供新的能力、可观察性或成本优势；
8. 24GB 消费 GPU 无法支持最小可恢复训练与本地推理合同。

负结果不需要删除。它用于缩小函数族和重新安排架构边界。

## 15. 可复现性

公开研究遵循 ARA：

```text
Claim
  -> Predict
  -> Experiment contract
  -> Evidence
  -> Decision
```

正式实验至少保存：代码 commit、数据 manifest 与 SHA-256、随机种子、完整命令、环境、日志、summary、必要 checkpoint、reload 审计和失败条件。

核心入口：

- [SameTime repository](https://github.com/houming818/sametime)
- [SPR 研究路线](/spr/)
- [TreeHeap 当前理论状态与目标](/treeheap-theory.html)
- [F 函数说明](/spr/091-treeheap-f-function-guide.html)
- [概念与实现路线图](/spr/092-treeheap-concept-implementation-roadmap.html)

## 16. 数学与方法背景

TreeHeap 没有声称从零发明所有数学对象。当前理论与下列方向存在明确联系：

1. **Distributional hypothesis：** 用上下文分布描述词的使用环境；
2. **Hellinger geometry：** 用平方根概率坐标比较离散分布；
3. **Hierarchical probabilistic models：** 用树分解大候选空间；
4. **Monte Carlo / simulated annealing：** 在离散或混合空间搜索局部结构；
5. **Differentiable routing：** 用 soft gate 让路由参数接受梯度；
6. **Information bottleneck：** 区分无损恢复与目标充分统计；
7. **Lifting scheme：** 用 coarse 与 detail 构造可逆多尺度 reference；
8. **Butterfly factorization：** 用分阶段稀疏变换建立长程通信。

参考文献：

1. Harris, Z. S. *Distributional Structure*. Word, 1954.
2. Gutmann, M., and Hyvärinen, A. *Noise-Contrastive Estimation*. AISTATS, 2010.
3. Morin, F., and Bengio, Y. *Hierarchical Probabilistic Neural Network Language Model*. AISTATS, 2005.
4. Tishby, N., Pereira, F. C., and Bialek, W. *The Information Bottleneck Method*. 1999.
5. Sweldens, W. *The Lifting Scheme: A Custom-Design Construction of Biorthogonal Wavelets*. Applied and Computational Harmonic Analysis, 1996.
6. Dao, T., Gu, A., Eichhorn, M., Rudra, A., and Ré, C. *Learning Fast Algorithms for Linear Transforms Using Butterfly Factorizations*. ICML, 2019.

这些工作提供数学工具和邻近思想，不代表 TreeHeap 已被证明等价于其中任何一种模型。

## 17. 结论

TreeHeap 当前的理论起点已经从“先造一棵树，再期待语义涌现”发生改变。现在的顺序是：先从语料构造 token 的概率背景观测；再让单位质量从 root 经局部主轴与阈值概率下坠，形成 leaf、路径和多分辨率 Embedding；然后要求句子 FOLD 在同一状态族中闭合、保序并对目标充分；最后由 READ 选择所需分辨率，Decoder 将其变成生成分布。

Monte Carlo、梯度下降和拓扑搜索都是寻找节点参数的工具，不是 F 本身。概率平均 FOLD 已经给出量纲与守恒基线，却因交换律无法承担完整序列组合。可逆 Lifting 与 Butterfly 仍提供有价值的数学和通信 reference，但不再单独定义最新理论。当前最重要的未知对象，是一个对软多分辨率概率状态闭合、能够表达顺序、还能被 READ/Decoder 消费的序列 FOLD。

现有证据说明这条路线不是纯粹想象：背景场可以构造，树可以被搜索和训练，状态可以保存重载，多层概率含有可读信息，软路由也能接受下游梯度。但从“可编码”到“可组织”，再到“可消费”，最后一段仍未闭合。

因此，项目下一阶段不再扩张核心术语，而是固定 canonical TreeState，完成 occurrence WRITE、保序 FOLD、分辨率曲线和无旁路 READ/Decoder。第一艘可发布的 TreeHeap，不需要一次成为通用智能；它需要在消费级硬件上成为一个诚实、完整、可运行、可反驳的研究原型。

## 附录 A：当前 Claim 边界

| 陈述 | 当前状态 |
|---|---|
| 真实语料可构造 token 背景概率场 | 支持 |
| TreeHeap 硬路由可以由 Monte Carlo 改善 | 有界任务支持 |
| TreeHeap 软路由可微并可由梯度更新 | 支持 |
| 概率 FOLD 保持质量、归一化和节点类型闭合 | 由公式成立 |
| 残差可以重建已存储节点 prototype | 由定义与数值检查支持 |
| 更深状态在登记实验中含更多背景预测信息 | 有界支持 |
| coarse 必然更确定、fine 必然更随机 | 开放 |
| 当前概率 FOLD 能表示 token 顺序 | 否，交换律反证 |
| 已找到统一序列 F | 否 |
| 最新 Embedding 已接入产品 Decoder | 否 |
| Encoder/Decoder 私有协议在最新架构中成立 | 开放 |
| TreeHeap 已优于 matched Transformer | 未证明 |
| TreeHeap 已实现实际压缩或加速 | 未证明 |

## 附录 B：符号表

| 符号 | 含义 |
|---|---|
| `t` | token type |
| `c` | corpus context feature 或 context token |
| `p_t(c)` | token `t` 的条件背景概率 |
| `x_t` | 平方根概率坐标 `sqrt(p_t)` |
| `v` | TreeHeap 节点 |
| `w_v` | 节点局部观察轴 |
| `b_v` | 节点阈值 |
| `tau_v` | 节点 soft-route 温度 |
| `g_v(t)` | token 在节点走向 right 的概率 |
| `e_t` | token 在 leaf 上的概率 Embedding |
| `M_v` | 节点概率质量或证据量 |
| `mu_v` | 节点 context prototype |
| `delta_v` | child 相对 parent 的概率残差 |
| `f_v` | 单节点函数 |
| `F_Theta` | 全部节点函数组成的整树映射 |
| `A` | Monte Carlo、梯度或拓扑学习算法 |
| `TreeState` | 统一的多分辨率状态合同 |
| `Y` | 下游目标序列或任务变量 |

## 附录 C：一句话版本

> TreeHeap 让 token 携带语料概率从 root 开始下坠，在局部节点中形成多分辨率坐标；它正在寻找一种对这些概率状态闭合且保序的 FOLD，使 READ 和 Decoder 能在消费级硬件上学习并使用同一套生成协议。
