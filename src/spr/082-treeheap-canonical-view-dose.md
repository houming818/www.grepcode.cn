---
title: "[SPR-082] 比例还是剂量：TreeHeap 视角协议的四臂因果实验"
date: 2026-08-05
lastmod: 2026-08-05
weight: 82
author: Houming818 & Codex Review
description: "用四个等起点实验臂拆分原序比例、Identity 绝对剂量与额外训练量，说明 TreeHeap 跨视角协议怎样被训练信号改变。"
tags: [SPR, TreeHeap, Butterfly, PrivateProtocol, CanonicalView, NLL, JensenShannon, ARA]
---

# 比例还是剂量

SPR-081 得到了一个醒目的现象：在固定训练预算里加入 20% 原序视角后，Butterfly 路径与 Identity 路径的输出分布迅速靠近，但 Native Butterfly 的 NLL 略微变差。

当时有两种解释，而且它们被混在了一起：

1. **比例解释**：模型关心 Identity 在全部样本中的占比；
2. **剂量解释**：模型关心训练期间实际看过多少个 Identity token。

这两种解释并不相同。把一杯糖水从 20% 稀释到 10%，既改变了浓度，也可能改变了糖的总量。若同时改变两个量，我们不能知道味道变化究竟来自哪一个。

因此，C06 不再扫描更多比例，而是用四个受控实验臂，把比例、绝对剂量和额外算力拆开。

> **先给结论：C06 的主 Claim 没有通过预注册门槛，但得到了一条很强的局部证据。Identity 的绝对 token 剂量强烈控制跨视角一致性；同时，Butterfly 剂量与两种视角的相互作用仍然不可忽略。**

## 1. 两种视角是什么

输入 token 状态记为 $H^{(0)}$。TreeHeap 的 Native 路径先经过 XOR Butterfly 的多层地址折叠：

$$
H_B=B_{D-1}\circ\cdots\circ B_1\circ B_0(H^{(0)})
$$

Identity 路径不执行 Butterfly 地址变换：

$$
H_I=H^{(0)}
$$

二者随后进入同一套 FOLD、READ 和 Decoder：

$$
P_B=D(\operatorname{READ}(\operatorname{FOLD}(H_B)))
$$

$$
P_I=D(\operatorname{READ}(\operatorname{FOLD}(H_I)))
$$

$P_B$ 和 $P_I$ 都是下一个 token 的概率桶。它们不是两个独立模型，而是同一个模型面对两套内部坐标时给出的答案。

如果二者接近，说明共享的 FOLD/Decoder 能用较一致的协议读取两种坐标；如果相差很大，说明模型更专门地适应了其中一条路径。

## 2. 四个实验臂

四个实验臂从同一个 checkpoint 出发，使用相同语料顺序、优化器配置和随机种子。区别只有追加训练的路径构成。

| 实验臂 | 含义 | Butterfly 剂量 | Identity 剂量 | Identity 比例 |
|---|---|---:|---:|---:|
| A | 原始 Butterfly 基线 | 6,308,579 | 0 | 0% |
| S | 用 Identity 替换部分 Butterfly | 5,035,947 | 1,272,632 | 20.17% |
| BB | 保留 A，再追加 Butterfly | 7,581,211 | 0 | 0% |
| BI | 保留 A，再追加 Identity | 6,308,579 | 1,272,632 | 16.79% |

表中的“剂量”是路径参与优化的相对更新量。最关键的比较有三个。

### 2.1 A 对 S：历史比例实验

总预算不变，但拿走约 20% Butterfly，换成同等数量 Identity。它同时改变 Butterfly 剂量和 Identity 比例，因此只能发现现象，不能单独解释原因。

### 2.2 BB 对 BI：等算力对照

两臂都在 A 的基础上追加相同数量训练。BB 追加 Butterfly，BI 追加 Identity。如果 BI 与 BB 不同，差异不能简单归因于“只是多训练了一会儿”。

### 2.3 S 对 BI：等 Identity 绝对剂量

S 和 BI 都看到了 1,272,632 个 Identity token，但比例不同。这个比较专门回答：跨视角一致性更像由比例决定，还是由 Identity 的绝对观察次数决定？

## 3. 工程审计：先修正更新次数错误

最初 smoke 暴露了一个重要问题：为了组合基础 batch 与追加 batch，代码执行了两次 `optimizer.step()`。同一数据量下，对照臂出现 42 次更新，增强臂却出现 83 次更新。

这会破坏因果比较，因为模型不仅看到了不同视角，还获得了更多参数更新机会。

正式实验前，我们取消了错误任务，把基础损失和 replay 损失按 token 数加权，在同一次反向传播中完成一次更新：

$$
L=\frac{n_B L_B+n_R L_R}{n_B+n_R}
$$

其中 $n_B,n_R$ 分别是基础路径与追加路径的有效 token 数。修正后四臂全部完成 6054 次正式参数更新。

这个插曲值得记录：**样本数相同、token 数相同，并不自动意味着优化过程相同。** 对照实验还必须核对反向传播次数和 `optimizer.step()` 次数。

## 4. 怎样读体检指标

### 4.1 Native NLL

Native NLL 衡量模型走正式 Butterfly 路径时，对正确 token 分配了多少概率。越低越好。若正确 token 的概率为 $p_y$，单个位置的损失为：

$$
\operatorname{NLL}=-\log p_y
$$

平均 NLL 降低，说明正式任务的概率预测更准确。

### 4.2 跨视角 JS

Jensen--Shannon divergence 衡量 $P_B$ 与 $P_I$ 两个概率桶的距离。先定义：

$$
M=\frac{P_B+P_I}{2}
$$

再计算：

$$
JS(P_B,P_I)=\frac{1}{2}KL(P_B\Vert M)+\frac{1}{2}KL(P_I\Vert M)
$$

JS 越低，两条路径越像在使用同一套输出协议。但 JS 低不保证答案正确，因为两条路径也可能一起犯错，所以必须同时看 Native NLL。

### 4.3 Source shuffle 损伤

把输入词序打乱后重新计算 NLL。如果 NLL 明显恶化，说明模型没有完全忽略输入。

### 4.4 Recovery

S 因为拿走 Butterfly 剂量而损失了一部分 Native 质量。BI 保留 Butterfly 剂量并加入同样多的 Identity。Recovery 衡量 BI 找回了多少损失：

$$
\operatorname{Recovery}=\frac{NLL_S-NLL_{BI}}{NLL_S-NLL_A}
$$

预注册门槛为 50%。达到门槛，才支持“保留 Butterfly 剂量能恢复大部分 Native 损失”。

## 5. 正式结果

| 实验臂 | Native NLL ↓ | 跨视角 JS ↓ |
|---|---:|---:|
| A：Butterfly 基线 | **3.272799** | 0.242087 |
| S：替换 20% | 3.282513 | **0.102573** |
| BB：额外 Butterfly | 3.275903 | 0.242107 |
| BI：额外 Identity | 3.278716 | 0.104578 |

其他关键结果：

| 判据 | 结果 | 门槛 | 状态 |
|---|---:|---:|---|
| Native recovery | 39.1% | 至少 50% | **未通过** |
| Identity 特异 JS 改善：BB - BI | 0.137528 | 至少 0.05 | 通过 |
| 等算力 Native 代价：BI - BB | +0.002812 | 不高于 0.015 | 通过 |
| Source shuffle 因果门 | 明显损伤 | 必须非零 | 通过 |
| 结构替换因果门 | 明显损伤 | 必须非零 | 通过 |

## 6. 结果到底说明什么

### 6.1 不是“多训练就会统一协议”

BB 比 A 多训练了同样的追加剂量，但 JS 几乎没有变化：

~~~text
A  JS = 0.242087
BB JS = 0.242107
~~~

因此，跨视角 JS 的下降不是额外计算量自动带来的。BI 只把追加路径换成 Identity，JS 便降到：

~~~text
BI JS = 0.104578
~~~

这说明 Identity 信号具有明显的视角特异性。它确实在改变共享读取协议。

### 6.2 绝对 Identity 剂量是强解释变量

S 与 BI 的 Identity 绝对剂量相同，但比例不同。二者的 JS 却非常接近：

~~~text
S  JS = 0.102573
BI JS = 0.104578
差值  = 0.002006
~~~

这比“比例决定一切”更接近一个剂量规律：在当前 checkpoint、当前训练区间附近，当模型累计看见约 127.3 万个 Identity token 时，它会把两条路径的输出概率拉到相似距离。

但这里只有一个 seed 和一个剂量点。我们还不能把它写成普遍定律。

### 6.3 绝对剂量不是全部答案

如果一切只由 Identity 剂量决定，那么 BI 保留完整 Butterfly 剂量以后，应该找回 S 丢掉的大部分 Native 质量。

实际 recovery 只有 39.1%，没有达到预注册的 50%。因此纯剂量解释被否定。较合理的当前模型是：

~~~text
Identity 绝对剂量
  -> 强烈决定跨视角协议靠近多少

Butterfly / Identity 比例与梯度相互作用
  -> 共同决定 Native 路径最终停在哪里
~~~

训练既有“看了多少次”的累计效应，也有“同一阶段两种信号怎样混合”的干涉效应。

### 6.4 C06 为什么只能判为未支持

C06 的主 Claim 要求 recovery 不低于 50%。实际只有 39.1%，所以必须按实验前的合同写成 **not supported as registered**。

这不是整个实验失败。它准确地排除了一个过强说法，同时支持了更窄的结论：

> 在当前训练区间，Identity 绝对剂量对 TreeHeap 跨视角输出一致性具有强而特异的影响；但保持 Butterfly 剂量并不足以消除全部 Native 代价。

## 7. Dreams 告诉了我们什么

人工 Dreams 没有出现统一变好的趋势。

- 部分句子的措辞更稳定；
- 部分句子的局部关系有所改善；
- 另一些句子仍有重复、事实漏失或角色错误；
- 低 JS 没有自动转化为肉眼可见的全面翻译提升。

因此 Dreams 在本轮只作为临床观察，不作为主结论。数值结果说明协议发生了变化；它尚未说明变化后的协议已经更懂语言。

## 8. 下一步怎样做

不应该再重复一次 0%、20%、40%、60% 的固定预算比例扫描。下一步需要建立**绝对剂量反应曲线**：

| 追加 Identity 剂量 | 等算力 Butterfly 对照 | 主要观察 |
|---:|---:|---|
| 5% | 5% | JS 是否已经快速下降 |
| 10% | 10% | 剂量拐点在哪里 |
| 20% | 20% | 能否复现 C06 |

每个点都必须从同一 checkpoint 启动、使用同一语料顺序、保持 `optimizer.step()` 数一致，并保存完整 checkpoint 与 NLL/JS 曲线。还需要补充多个 seed，同时画 Native NLL 与 JS 的 Pareto 曲线。

这样才能回答：协议统一是否存在饱和点，以及能否在更小 Native 代价下取得大部分 JS 收益。

## 9. 当前结论

SPR-081 发现“少量原序视角会强烈改变协议”；SPR-082 则进一步说明，这个现象不能简单归因于比例，也不能简单归因于多训练。

当前最可靠的表述是：

> TreeHeap 的共享 FOLD/Decoder 协议对训练视角的绝对剂量高度敏感。相同 Identity 剂量在不同混合比例下产生了几乎相同的跨视角 JS；然而 Native 质量只恢复 39.1%，说明 Butterfly 剂量、混合比例和梯度相互作用仍共同参与协议形成。

它不是终点，但它让下一步从“继续加数据看看”变成了一个可以测量的剂量响应问题。

完整 Claim、代码与 Evidence 已公开在 [SameTime 仓库](https://github.com/houming818/sametime)。

---

**License:** GPLv3。本文公开实验合同、失败门槛、实现修正与结果；任何人都可以复现、审计或提供相反证据。
