---
title: "[SPR-093] 让 root 真正携带条件信息：条件残差与证据 FOLD"
date: 2026-10-01
lastmod: 2026-10-01
weight: 93
author: Houming818 & Trinity (Codex)
description: "A20 在固定递归合同中把全局语料先验与 token 条件信息分开，并用概率质量加权的 common/detail FOLD 增强 root 信息；本文给出算法、toy、控制实验、正式结果与证据边界。"
keywords: [TreeHeap, SPR, Root, 条件残差, 证据FOLD, FOLD, READ, 多分辨率, 概率质量, ARA]
tags: [SPR, TreeHeap, ConditionalResidual, EvidenceFold, RecursiveREAD, ARA]
---

# 先说结论

上一轮 A19 已经证明，共享参数的十层递归 `FOLD -> root -> READ` 可以训练，也确实会随着 READ
深度逐步改变输出。但它暴露了一个更重要的问题：最好的 `16D` 模型仍然略差于一个完全不看
目标 token 的全局语料先验。

换句话说，旧模型虽然“递归得很认真”，root 里真正属于当前 token 的信息却很弱。

A20 没有给 root 乘一个人为放大常数，而是做了两项结构变更：

1. 编码端不再反复搬运全语料公共背景，只编码当前 token 相对背景的**条件残差**；
2. FOLD 不再无条件平均左右 child，而是按它们的概率质量分别计算**公共证据**和**差异证据**。

正式实验完成后，最强的 `16D evidence_fold` 得到：

| 指标 | A19 `16D` | A20 `16D evidence_fold` |
|---|---:|---:|
| sealed-test NLL | 5.572473 | **5.467703** |
| PPL | 263.084 | **236.915** |
| root shuffle damage | 0.068362 | **0.186255** |
| root effective rank | 3.758 | **8.327** |
| root 平均非对角 cosine | 0.9717 | **0.6829** |

A20 首次在这条递归 context-field codec 航线上胜过了显式全局先验：

$$
5.555696-5.467703=0.087993
$$

这支持一个窄结论：**新的 FOLD 让 root 携带了更强的 token 条件信息。** 它还不证明 root 已经
形成语言语义，也不证明 TreeHeap 已经能够生成或翻译文本。

# A19 到底哪里不够

A19 的任务是：给定目标 token \(t\) 的 1,024 维上下文概率场 \(p(c\mid t)\)，把它逐层压缩成
一个低维 root，再通过十层 READ 恢复这 1,024 个 context coordinate 的概率。

它的最好结果看起来比均匀分布好很多：

| 参考对象 | Test NLL |
|---|---:|
| 1,024 维均匀分布 | 6.931472 |
| A19 `16D` 递归 codec | 5.572473 |
| 不读取 token 的全局 context prior | **5.555696** |

问题就在第三行。只要语料里有高频 context，任何模型都可以靠全局词频取得不错的 NLL；它不
需要知道当前目标是 `bank`、`push` 还是别的 token。

A19 的 root-shuffle 干预进一步确认了这一点。把不同 token 的 root 随机交换以后，NLL 只恶化
`0.068362`；同时，root 之间的平均 cosine 高达 `0.9717`。这些 root 几乎都指向相同方向。

因此 A19 实际混合了两种信息：

$$
\underbrace{\log p_{global}(c)}_{\text{所有 token 共享的语料背景}}
+
\underbrace{r_t(c)}_{\text{当前 token 的条件差异}}
$$

共同背景很强，条件差异很弱。模型可以主要学习第一项，并在递归地址上继续降低 NLL，却不必
把足够多的第二项送到 root。

# A20 的第一项变更：只压缩条件残差

A20 把目标 token 的条件分布改写为：

$$
r_t(c)=\log p(c\mid t)-\log p_{global}(c)
$$

其中：

- \(p(c\mid t)\) 是看见目标 token \(t\) 后，context \(c\) 出现的条件概率；
- \(p_{global}(c)\) 是不看目标 token 时，整个语料中的 context 先验；
- \(r_t(c)\) 只描述当前 token 相对公共背景增加或减少了多少证据。

Decoder 输出时再把公共背景加回来：

$$
\operatorname{logit}_t(c)
=\log p_{global}(c)+\widehat r_t(c)
$$

这里的 \(\widehat r_t(c)\) 必须由 `root -> recursive READ` 给出。

这个设计建立了一个很干净的零点：如果 root 没有携带任何 token 条件信息，就令

$$
\widehat r_t(c)=0
$$

模型便精确退回全局先验。于是，“胜过全局先验”不再是事后补做的审计，而成为模型必须跨过
的结构门槛。

## 一个四坐标 toy

假设全语料背景是：

$$
p_{global}=(0.40,0.30,0.15,0.15)
$$

而 token `bank` 的上下文分布是：

$$
p(c\mid bank)=(0.20,0.10,0.35,0.35)
$$

直接压缩第二个数组时，前两个高频坐标仍然占据大量表示能力。条件残差则是：

$$
r_{bank}=\left(
\log\frac{0.20}{0.40},
\log\frac{0.10}{0.30},
\log\frac{0.35}{0.15},
\log\frac{0.35}{0.15}
\right)
$$

它明确告诉 FOLD：前两个坐标应当被抑制，后两个坐标应当被增强。root 不必重新记忆每个 token
都共有的语言背景，只需保存“bank 相对背景有什么不同”。

正式实现还并行输入有符号平方根差：

$$
s_t(c)=\operatorname{sign}(\Delta_t(c))\sqrt{|\Delta_t(c)|},
\qquad
\Delta_t(c)=p(c\mid t)-p_{global}(c)
$$

所以每个 context coordinate 的 leaf feature 是二维的：对数比值提供相对证据，有符号平方根
保留概率差的方向，并减小大概率值对数值尺度的支配。

# A20 的第二项变更：证据 FOLD

旧 FOLD 的基本骨架接近平均：

$$
h_p\approx \frac{h_l+h_r}{2}+\text{learned correction}
$$

但 context tree 的左右 child 往往并不具有相同概率质量。如果左侧覆盖当前 token 的 80% 概率，
右侧只有 20%，无条件平均会把小分支放大，也会把大分支压低。

A20 先根据 child 的真实质量计算权重：

$$
a_l=\frac{m_l}{m_l+m_r},\qquad
a_r=\frac{m_r}{m_l+m_r}
$$

再把 parent 候选拆成两部分。

公共证据：

$$
m=a_lh_l+a_rh_r
$$

差异证据：

$$
d=\sqrt{a_la_r}(h_l-h_r)
$$

最后由每个 hidden dimension 自己选择更需要公共量还是差异量：

$$
h_p=\operatorname{RMSNorm}
\left(
g_m\odot W_mm+g_d\odot W_dd
\right)
$$

其中 \(g_m,g_d\) 来自可训练 softmax gate，并满足每一维：

$$
g_m+g_d=1
$$

这个公式没有固定的“递归放大系数”。信号能否进入 root，取决于概率质量、左右差异和可训练
变换，而不是每上升一层就机械地乘一个常数。

## 为什么差异项带有平方根

若左右质量分别是 \(0.8\) 和 \(0.2\)，则：

$$
\sqrt{a_la_r}=\sqrt{0.8\times0.2}=0.4
$$

如果某一边几乎没有质量，例如 \(a_r\to0\)，那么：

$$
\sqrt{a_la_r}\to0
$$

此时“左右差异”缺少双边证据，不应被当作强对比向上传播。只有左右都获得了支持，contrast
通道才会自然增强。这是由当前概率质量导出的尺度，不是手工选择的固定增益。

# 三个实验臂分别回答什么

A20 在相同参数量、数据、更新次数和随机种子下比较三个实验臂：

| 实验臂 | 条件残差 | 证据 FOLD | 多深度辅助 loss | 用途 |
|---|---:|---:|---:|---|
| `residual_a19` | 是 | 否 | 否 | 测量只改变输入/输出基准的效果 |
| `evidence_fold` | 是 | 是 | 否 | 测量质量感知 common/detail FOLD 的增量 |
| `evidence_multiscale` | 是 | 是 | 是 | 检查直接向多个 READ 深度提供梯度是否更好 |

`evidence_multiscale` 的辅助监督作用在 READ 深度 `2/4/6/8`，权重固定为 `0.25`。它不是新的
模型容量，只是改变梯度从哪些分辨率进入共享参数。

# 实验合同

正式实验在 ARA 中预注册后执行：

| 项目 | 固定值 |
|---|---:|
| 语料统计 | A14 的 100 万行 byte-identical count artifact |
| target rows | 512 |
| context coordinates | 1,024 |
| 递归层数 | 10 |
| hidden dimensions | 4 / 8 / 16 |
| 每臂训练 | 200 个完整 epoch |
| split seed | 20260924 |
| model seed | 20261001 |
| 最大参数量 | 3,297 |

质量指标只作观察，不触发提前停止。只有 OOM、CUDA 错误、NaN/Inf、证据损坏或 reload 失败
可以终止任务。全部九个正式实验都跑满预算、数值有限，并通过 checkpoint 精确重载。

需要强调：1,024 个 context coordinate 的顺序仍是固定实验拓扑。A20 没有证明这个顺序最优，
也没有学习新的树拓扑。

# 正式结果

全局先验 Test NLL 为 `5.555696`，PPL 为 `258.707`。

| 实验臂 | 维度 | 参数 | Test NLL | 相对全局先验收益 | root shuffle damage |
|---|---:|---:|---:|---:|---:|
| `residual_a19` | 4 | 249 | 5.547637 | 0.008059 | 0.022554 |
| `residual_a19` | 8 | 881 | 5.527285 | 0.028411 | 0.082830 |
| `residual_a19` | 16 | 3,297 | 5.500450 | 0.055246 | 0.154666 |
| `evidence_fold` | 4 | 249 | 5.541173 | 0.014523 | 0.036372 |
| `evidence_fold` | 8 | 881 | 5.511612 | 0.044084 | 0.140482 |
| `evidence_fold` | 16 | 3,297 | **5.467703** | **0.087993** | **0.186255** |
| `evidence_multiscale` | 4 | 249 | 5.542355 | 0.013341 | 0.028007 |
| `evidence_multiscale` | 8 | 881 | 5.512790 | 0.042906 | 0.121891 |
| `evidence_multiscale` | 16 | 3,297 | 5.477596 | 0.078100 | 0.179016 |

三个实验臂都随 `4 -> 8 -> 16` 获得更好的 NLL。证据 FOLD 在每个维度都优于保留 A19 FOLD
的对照臂，因此收益不能只归因于换成条件残差坐标。

{{< claim id="S1-CONDITIONAL-RESIDUAL-FOLD-A20-C01" status="supported" >}}
预注册主张得到支持：`evidence_multiscale` 至少在一个正式维度上跑满预算、保持有限、精确
reload、胜过无输入全局先验，且具有正的 root-shuffle damage 和非平坦 READ-depth curve。
{{< /claim >}}

# 我们怎样知道提升真的经过 root

只看 NLL 还不够。A20 同时做了三种结构干预。

## 1. 打乱 root 身份

将 token A 的 root 交给 token B 解码。如果 root 只保存所有 token 共享的公共背景，这个交换不
应明显影响结果。

`16D evidence_fold` 的 NLL 从 `5.467703` 恶化到 `5.653958`：

$$
\Delta_{shuffle}=5.653958-5.467703=0.186255
$$

而 A19 同类干预只有 `0.068362`。root 身份的因果作用扩大到约原来的 `2.72` 倍。

## 2. 关闭分支 READ

关闭分支 READ 后，root 只能对所有 1,024 个坐标施加相同残差。softmax 对统一常数平移不敏感，
因此结果精确退回：

$$
NLL_{branchless}=5.555696
$$

这说明收益来自“token 条件 root 与递归地址 READ 的组合”，不是输出层偷偷复制了一个平坦偏置。

## 3. 测量 root 几何

| 指标 | A19 `16D` | A20 `16D evidence_fold` | 含义 |
|---|---:|---:|---|
| effective rank | 3.758 | 8.327 | root 使用了更多独立变化方向 |
| mean off-diagonal cosine | 0.9717 | 0.6829 | 不同 token 的 root 不再高度共线 |

这些指标支持“root 更有区分度”，但不能单独证明这些方向具有语言语义。随机码也可以提高 rank；
因此它们必须和 sealed-test、shuffle 以及 branchless 控制一起读取。

{{< evidence grade="E2" source="A20 formal seed 20261001" >}}
A20 建立的是机制参与性证据：root 身份、条件残差和递归 READ 对真实语料 context-field 重建
具有可测量的因果作用。单 seed 的组件实验尚不足以形成跨任务架构优势结论。
{{< /evidence >}}

# 多深度监督没有成为最优解

预注册 Claim 选择 `evidence_multiscale` 作为主臂，是因为我们担心十层反向传播不能充分把 credit
送到 root。它确实让 READ 深度曲线更平滑：中间深度较少出现先恶化、后恢复的现象。

但最终深度上，普通 `evidence_fold` 反而更好：

$$
5.467703 < 5.477596
$$

这意味着固定权重 `0.25` 的中间层目标可能限制了最终层的最优表示。当前最合理的工程选择是：

- 保留条件残差和证据 FOLD；
- 不把固定多深度 loss 升级为默认算法；
- 后续只把它作为曲线整形、curriculum 或自适应权重候选。

这也再次说明，READ 深度曲线不必单调。中间分辨率暂时变差，不等于最终递归计算无效，更不能
作为提前停止训练的理由。

# 这次结果解决了什么

A20 回答了 A19 留下的具体问题：

> 不依靠固定放大常数，怎样让 token 条件信号更有效地到达 root？

当前答案是：

1. 把公共语料背景放在 Decoder 基线中，不让 root 重复搬运；
2. 把 root 的任务改成压缩条件残差；
3. FOLD 按 child 概率质量组合 common/detail；
4. 用 root shuffle 和无分支 READ 检查信息是否真的走过 root。

这使 `16D` 模型相对 A19 改善 `0.104770` NLL，并从“略差于全局先验”推进到“明确胜过全局
先验”。它是一个真实的结构进展。

# 这次结果没有解决什么

A20 仍然只是 context-field codec，不应越界解释为完整语言模型。它没有证明：

- root 可以无损恢复全部 leaf；
- context coordinate 的固定顺序就是合理拓扑；
- root 的几何方向等于可解释语义；
- 算法能够编码句中 occurrence，而不只是 token type；
- Decoder 能生成连续文本、完成翻译或事实问答；
- TreeHeap 在质量、功耗或内存上优于 Transformer；
- `16D` 是最优维度；
- 单 seed 结果能跨语料、跨任务复现。

还有一个距离必须正面保留。直接保存每个 token 的完整概率场时，诊断 NLL 为 `5.116258`；A20
最优结果仍然是 `5.467703`。两者相差：

$$
5.467703-5.116258=0.351445
$$

递归瓶颈已经开始传递条件信息，但距离完整条件场仍有明显失真。

# 下一步

下一轮不应立刻堆更大的隐藏维度。更有信息量的动作是：

1. **多 seed 复现**：确认 `evidence_fold > residual_a19` 不是单次初始化结果；
2. **拓扑置换实验**：固定数据和参数预算，比较原坐标顺序、随机排列和学习排序；
3. **失真归因**：分别测量 FOLD 压缩、root 容量和 READ 展开造成的误差；
4. **句中 occurrence**：让相同 token 在不同上下文形成不同条件残差，检查 root 是否随语境改变；
5. **接入统一 TreeState**：把本实验的 `common/detail/mass` 合同接到句子 Encoder 与 Decoder，
   而不是继续留在独立 context-field 探针中。

# 复现入口

ARA 预注册、实现与证据位于：

```text
ara/s1-echo/logic/conditional_residual_evidence_fold_a20.md
ara/s1-echo/src/s1_conditional_residual_evidence_fold_a20.py
ara/s1-echo/evidence/s1_conditional_residual_evidence_fold_a20/
```

正式证据使用 `seed=20261001`。九个正式 checkpoint 均完成 SHA-256 记录、有限值检查、完整预算
检查和精确 reload。A20 不是终点，但它把一个模糊问题变成了可计算的结构答案：**root 的信息
不应靠增益硬推上去，而应先定义清楚什么值得被 root 保存。**

> **License: GPLv3**
