---
title: "[SPR-090] F 不是一个神秘公式：用全局概率场搜索 TreeHeap"
date: 2026-09-23
lastmod: 2026-09-23
weight: 90
author: Houming818 & Trinity (Codex)
description: "从单句梯度的局部性出发，解释怎样把全语料共现统计保存成背景状态，再用蒙特卡洛搜索质量守恒的概率残差树 F。"
keywords: [TreeHeap, SPR, F函数, 蒙特卡洛搜索, 概率残差树, Embedding, 共现概率, FOLD, UNFOLD, ARA]
tags: [SPR, TreeHeap, MonteCarlo, Embedding, ProbabilityTree, FOLD, ARA]
---

# 先说我们究竟在找什么

这篇文章讨论的是 token embedding 的形成，不是翻译，也不是 Decoder 怎样生成下一个词。

问题可以用一句普通话表达：

> 已经统计出每个词经常出现在什么上下文中以后，怎样让这些词在一棵 TreeHeap 中找到稳定、
> 可解释、可以逐层细化的位置？

这里的 **F** 只是“由当前状态生成下一步树结构和 token 位置”的函数名称：

$$
F:\text{全局背景概率场}\longrightarrow
\text{TreeHeap 结构、节点原型和 token 路径}
$$

它不是预先知道答案的公式。当前工作正是寻找 F 的结构。

SPR-089 尝试从概率单纯形和局部主轴理解 token 怎样下落，但留下一个核心空位：局部路由完成
以后，怎样得到下一轮状态？最近的实验又暴露出一个更基础的因果问题：如果直接用“预测下一词”
训练 embedding 和 F，那么下一词答案会通过梯度进入参数。最后得到的表示可能很好用，却不能
证明 embedding 是由背景概率场自然形成的。

因此我们决定把两件事拆开：

~~~text
阶段一：只用全语料共现统计寻找 embedding F
阶段二：冻结 embedding，再检查它能否帮助下游任务
~~~

本文只讨论阶段一。

# 最少术语表

| 名称 | 本文含义 |
|---|---|
| token | 文本经过分词后得到的字、词或子词单位 |
| embedding | token 的数值坐标，使 token 可以被比较、组合和读取 |
| 上下文概率场 | 对每个 token 统计它周围出现各种 context token 的条件概率 |
| FOLD | 把两个 child 的状态合成 parent |
| UNFOLD | 从 parent 出发，根据当前 token 的概率特征选择左右 child |
| 原型 | 到达某个节点的 token 所共有的平均上下文分布 |
| 残差 | child 原型相对 parent 原型增加或减少的概率成分 |
| 蒙特卡洛搜索 | 随机提出结构修改，根据全局评分接受或拒绝，而不是穷举全部结构 |
| sealed test | 搜索过程中不可查看，只在 F 选定后打开一次的测试数据 |

# 为什么单句梯度不够

假设一条句子产生损失：

$$
\ell(x;\theta)
$$

它只能提供这条句子的梯度：

$$
g_x=\nabla_\theta\ell(x;\theta)
$$

而我们真正关心的是整套语料分布上的目标：

$$
L(\theta)=
\mathbb E_{x\sim D}[\ell(x;\theta)]
$$

在理想随机采样条件下，单句梯度的期望可能等于全局梯度：

$$
\mathbb E[g_x]=\nabla_\theta L(\theta)
$$

但这不表示每个单句梯度都指向正确方向，也不保证非凸参数空间能到达全局最优点。

例如，包含 “bank account” 的句子会把 bank 推向“银行”，包含 “river bank” 的句子会把
bank 推向“河岸”。如果每来一句话就不可逆地改写 TreeHeap 路径，路径会受到语料顺序、
高频样本和最近样本影响。系统可能发生漂移、遗忘或早期分支锁定。

我们的处理方式是：**句子先更新统计状态，不直接更新 F。**

~~~text
句子
  -> 更新 token-context 共现计数
  -> 累积成全局背景场
  -> F 在背景场上统一搜索
~~~

这与动态规划保存中间状态的思想相似。历史不是只保存在当前参数里，而是保存在可检查的共现
计数和条件概率中。

# 一个重要的实验纠正

我们曾做过如下实验：

~~~text
四个输入 token
  -> embedding
  -> FOLD
  -> parent
  -> 预测第五个 token
~~~

第五个 token 没有进入前向输入，但它进入了交叉熵：

$$
\mathcal L=-\log P(t_5\mid t_1,t_2,t_3,t_4)
$$

这个 loss 同时更新 embedding、F 和 Decoder。因此 parent 中存在下一词信息并不奇怪：
训练目标主动要求它保存下一词信息。

那个实验仍能回答“哪种 F 更适合下一词预测”，却不能回答“哪种 F 会由全局背景场自然形成”。
这两个问题都合理，但证据不能混用。

本文的新实验彻底移除下一词标签、翻译标签、Decoder、递归 READ 和单句在线参数更新。它只
留下 token 与 context 的累计共现概率。

# 背景场的数据结构

对 token \(t\)，统计它与每个 context \(c_j\) 的共现次数：

$$
C_{tj}
$$

经过平滑和归一化，得到条件概率：

$$
p_t(j)=P(c_j\mid t)
=
\frac{C_{tj}+\alpha}
{\sum_k C_{tk}+\alpha K}
$$

因此每个 token 都对应一个概率向量：

$$
p_t\in\Delta^{K-1}
$$

这里的 \(\Delta^{K-1}\) 是概率单纯形：每个分量非负，并且总和为 1。

为了让概率距离更适合欧氏几何计算，实验采用平方根坐标：

$$
x_t=\sqrt{p_t}
$$

这与 Hellinger 距离相容。需要强调的是，\(x_t\) 仍然来自全局共现概率，不是随机初始化的
可训练 token 表。

# F 的最小结构：概率残差树

我们把 F 的候选结果设计成一棵二叉 TreeHeap。每个内部节点保存：

~~~text
Node {
    mass          到达节点的语料概率质量
    prototype μ   本节点 token 的平均 context 概率
    axis a        本节点观察 token 差异的方向
    threshold b   左右分支的切分位置
    left, right   两个 child
}
~~~

token 到达节点后计算：

$$
z_t=a^\top x_t
$$

再与阈值比较：

$$
z_t\le b\Rightarrow L,\qquad
z_t>b\Rightarrow R
$$

第一版 smoke 使用硬路由，因为我们先要检查搜索是否能找到结构。将来可以把它放松成连续后验：

$$
P(R\mid t,v)=\sigma\left(
\frac{a_v^\top x_t-b_v}{\tau_v}
\right)
$$

## FOLD 为什么有明确含义

设左右 child 的质量为 \(m_L,m_R\)，上下文原型为 \(\mu_L,\mu_R\)。parent 定义为：

$$
m_P=m_L+m_R
$$

$$
\mu_P=
\frac{m_L\mu_L+m_R\mu_R}{m_L+m_R}
$$

这不是任意神经网络层。它是条件概率统计的质量加权合并，parent 与 child 的数据类型相同，
量纲也相同。

如果所有 token 在 child 中的计数全部加起来，必然得到 parent 的计数。因此可以直接检查：

$$
m_P\mu_P=m_L\mu_L+m_R\mu_R
$$

若实现不满足这个等式，说明代码或数据定义有问题，而不是“模型还没学会”。

## 残差怎样形成多分辨率

child 相对 parent 的变化定义为：

$$
\Delta\mu_C=\mu_C-\mu_P
$$

沿 root 到 leaf 的路径累加：

$$
\mu_{\text{leaf}}
=
\mu_{\text{root}}
+\Delta\mu_{n_1}
+\Delta\mu_{n_2}
+\cdots
+\Delta\mu_{n_d}
$$

中间项会望远镜式抵消，所以这个等式应当达到浮点误差级闭合。

它提供了清晰的分辨率解释：

- root 保存全语料公共背景；
- 浅层残差提供粗区分；
- 深层残差逐步补充局部细节；
- leaf 保存当前路径能达到的最细背景分布。

这并不自动等于“语义”。语种、标点、领域和频率也可能形成强分支。语义性质需要额外审计，
不能只看树长得像分类学。

# 蒙特卡洛到底搜索什么

F 可以写成：

$$
F=(T,\{a_v,b_v\}_{v\in T})
$$

其中 \(T\) 是树，\(a_v,b_v\) 是每个内部节点的轴和阈值。

第一轮 smoke 固定完全二叉树的深度，只搜索各节点的局部切分规则。一次动作是：

1. 从当前仍有多个 token 的内部节点中选一个；
2. 从该节点的 token 中抽两个点，用二者差形成候选轴，或者小幅扰动现有轴；
3. 从本地投影分布中选择候选阈值；
4. 重新让全部 token 下落；
5. 根据全局背景重建质量评分；
6. 接受更优方案，也以逐渐降低的概率接受暂时更差的方案。

偶尔接受更差方案，是为了跳出当前位置附近的局部极小值。接受概率采用 Metropolis 形式：

$$
P(\text{accept})=
\min\left(
1,
\exp\frac{J_{\text{current}}-J_{\text{proposal}}}{T}
\right)
$$

温度 \(T\) 随迭代下降。搜索同时保留一个 global best，所以临时探索不会覆盖已经找到的最好 F。

# 搜索评分来自哪里

我们不能用最终 test 集反复选择 F，否则 test 就变成了训练数据。

因此原训练共现计数再次按固定 seed 拆成：

$$
C_{\text{fit}}+C_{\text{dev}}=C_{\text{train}}
$$

搜索过程只做：

~~~text
用 fit 计算每个 leaf 的 context 原型
用 dev 计算该结构的 context NLL
~~~

评分为：

$$
J(F)=
-\frac{
\sum_{t,j}C_{\text{dev},tj}
\log\hat P_F(c_j\mid t)
}{
\sum_{t,j}C_{\text{dev},tj}
}
$$

搜索结束后，才打开原来就保存好的 WMT sealed test，比较初始树、搜索所得树和随机路径。

这里没有手工要求左右流量各占 50%，也没有给饥饿分支强行输送 token。链表式或极不均衡结构
可以存在，但它必须在未参与原型估计的 dev 共现上获得更低 NLL。复杂结构未来还需要加入节点
成本；本轮树深固定，因此结构复杂度相同。

# A11 smoke 怎样判定

这次实验编号为 A11，Claim 为：

{{< claim id="S1-F-MC-A11-C01" status="supported-smoke" >}}
在冻结的真实 WMT token-context 概率场上，蒙特卡洛搜索局部 TreeHeap 切分规则，可以改善
确定性初始树的 dev 背景重建，同时保持 FOLD 质量守恒与路径残差闭合。
{{< /claim >}}

机械条件：

~~~text
所有数值有限
sealed test 不参与 proposal 评分
至少接受一个 proposal
FOLD 守恒误差 <= 1e-10
路径残差闭合误差 <= 1e-10
~~~

经验条件：

~~~text
dev NLL 至少改善 0.005
sealed-test NLL 不比初始树恶化超过 0.01
sealed-test NLL 优于随机路径
leaf utilization 至少 50%
~~~

如果 dev 改善而 sealed test 恶化，说明搜索过拟合。如果概率恒等式不闭合，说明实现无效。
如果随机路径同样好，说明当前 F 搜索没有提取有用背景结构。

# 实验结果：搜索确实找到了更好的概率树

任务 `561` 在 `io` 的 RTX 3090 上完成，共搜索 256 个候选动作，接受了 175 次。输入是冻结的
真实 WMT `512 x 1024` token-context 计数场；fit、dev 和 sealed test 分别包含约 528 万、132 万
和 74 万次共现计数。

~~~text
                         初始树          搜索所得树       随机路径
dev NLL                  5.373436        5.357366         -
sealed-test NLL          5.396372        5.378041         5.457888

dev 改善                                  0.016070
sealed test 相对初始改善                  0.018331
sealed test 相对随机改善                  0.079847
~~~

结构检查也通过：32 个 leaf 全部得到 token，leaf utilization 为 `1.0`，占用熵为 `0.9131`。
FOLD 质量守恒的最大绝对误差为 `1.39e-17`，root 加路径残差重建 leaf 的最大绝对误差为
`3.47e-18`。这些误差处于双精度浮点舍入尺度，没有发现公式或实现层面的破坏。

这组数字支持一个很窄但重要的结论：**在没有句子答案、Decoder 和 READ 参与的情况下，按
全局上下文重建评分搜索 F，能够找到比确定性初始树和随机树都更好的概率残差结构。**

它还是 smoke 证据，而不是最终架构结论。目前只有一个 seed、一个深度和一份背景场。下一步
需要复现 seed，并做受控深度阶梯；在这些结果稳定以前，不应把搜索所得树直接装进主模型。

# 这次实验没有证明什么

即使全部条件通过，也只能说明：

> 在一个固定的真实语料背景场上，概率守恒的局部切分规则可以通过全局搜索得到改善。

它仍然不能证明 leaf 已经代表人类语义类别、TreeHeap 优于 SGNS 或 Transformer、多义词已经
得到上下文条件路径、Decoder 能读取这些残差，或者 F 可以直接用于翻译与生成。

# 当前路线图

~~~text
全局语料
  -> token-context 计数状态
  -> 条件概率背景场
  -> 蒙特卡洛搜索节点轴和阈值
  -> 概率残差 TreeHeap
  -> 冻结 embedding
  -> 独立下游任务检查
  -> 最后才接 READ 和 Decoder
~~~

这条路线回答了两个此前混在一起的问题：

1. embedding 的空间从哪里来？
2. 下游任务怎样使用这个空间？

前一个问题由全局概率场和 F 搜索回答；后一个问题必须在冻结 F 后单独验证。若下游失败，我们
才能区分“背景空间没有形成”和“读取协议没有学会”。

# 给第一次进入项目的人

检查本文不需要先相信 TreeHeap。只需检查四件事：

1. 单句是否只更新了可审计的共现统计，而没有直接改树；
2. 搜索是否完全没有查看 sealed test；
3. parent 是否真由 child 概率质量守恒地合并；
4. 搜索所得结构是否在新共现样本上优于初始树和随机路径。

只要任何一点失败，A11 Claim 就不成立。实验编号、叙事和漂亮的树图都不能替代这些条件。

> **License: GPLv3。本文的概率残差树定义、搜索合同、否证条件和 ARA 实验设计按项目许可证公开。**
