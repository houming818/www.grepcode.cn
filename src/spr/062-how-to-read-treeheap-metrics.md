---
title: "[SPR-062] 如何读懂 TreeHeap 实验：从 NLL、Loss 到因果干预和统计证据"
date: 2026-07-17
lastmod: 2026-07-17
weight: 62
author: Houming818 & Codex Review
description: "面向本科读者的 TreeHeap 实验指标说明书：解释 NLL、交叉熵、困惑度、MSE、余弦距离、KL 散度、准确率、BLEU、消融损失、修复率、置信区间等数字究竟在测量什么，以及它们不能证明什么。"
tags: [SPR, TreeHeap, ARA, NLL, Loss, Metrics, Statistics, Evaluation, Causal Intervention]
---

# 如何读懂 TreeHeap 实验：从 NLL、Loss 到因果干预和统计证据

TreeHeap 的博客里经常出现这样的句子：

```text
NLL 从 16.16 降到 5.69
source shuffle damage = +0.21
修复了 72.38% 的 MSE
top-1 = 0.91
bootstrap 95% CI 跨过了 0
```

熟悉机器学习的人会迅速把它们归入不同抽屉，但许多读者只会看到一排小数。更麻烦的是，这些数字的方向并不统一：NLL 越小越好，准确率越大越好；干预损失通常越大，越能说明被干预部分有因果作用；而 MSE 很小，也可能只是状态本来就接近零。

本文是 TreeHeap 研究的公共“体检指标说明书”。它不提出新的架构 Claim，只回答四个问题：

1. 这个数字是怎样算出来的？
2. 它变大或变小通常意味着什么？
3. 它能支持哪一级结论？
4. 它不能证明什么？

---

## 1. 先区分三种东西：Loss、Metric 和 Evidence

这三个词经常混在一起，但职责不同。

### 1.1 Loss：给梯度看的训练信号

模型有参数 $\theta$，输入为 $x$，目标为 $y$。训练先计算：

$$
L(\theta;x,y),
$$

再用梯度下降更新参数：

$$
\theta \leftarrow \theta-\eta\nabla_\theta L.
$$

Loss 的首要任务不是方便人阅读，而是告诉参数应该向哪个方向移动。例如语言模型常用交叉熵，状态修复常用 MSE。

### 1.2 Metric：给人看的功能测量

Metric 不一定参与训练。例如：

- top-1 准确率；
- 整句完全还原率；
- BLEU；
- 自由生成的重复率；
- 每秒处理 token 数。

它们回答“系统表现如何”，但不一定能够产生适合训练的梯度。

### 1.3 Evidence：Claim 与对照实验共同形成的证据

单个数字通常不是 Evidence。比如测试 NLL 为 `5.0`，没有基线就不知道好坏；训练 NLL 下降，也可能只是记住了训练集。

ARA 所说的 Evidence 至少需要：

```text
预先声明的 Claim
+ Predict（若 Claim 成立，应该观察到什么）
+ 对照或干预
+ 测量指标
+ 可证伪门槛
+ 可复查的输出文件
```

因此，`NLL=5.0` 是一个测量值；“打乱 source 后 NLL 增加 1.2，并在三个 seed 重现”才开始构成“模型使用了 source”的证据。

---

## 2. 概率桶：NLL 从哪里来

假设 decoder 下一步要预测一个 token。词表里有“我、喜欢、米饭、天气”等许多候选，模型输出一个概率桶：

| 候选 token | 模型概率 |
|---|---:|
| 米饭 | 0.50 |
| 面条 | 0.20 |
| 苹果 | 0.10 |
| 天气 | 0.01 |
| 其他 token 合计 | 0.19 |

如果正确答案是“米饭”，模型给正确答案的概率是 $0.50$。如果正确答案是“天气”，正确答案概率只有 $0.01$。

我们希望正确答案概率越大越好。但直接连乘长句中所有正确 token 的概率，很快会变成接近零的小数：

$$
P(y_1,y_2,\ldots,y_T\mid x)
=\prod_{t=1}^{T}P(y_t\mid y_{<t},x).
$$

对数把乘法变成加法：

$$
\log P(y\mid x)
=\sum_{t=1}^{T}\log P(y_t\mid y_{<t},x).
$$

因为概率不超过 1，其对数不大于 0。为了得到一个“越小越好”的正数，我们取负号，这就是负对数似然：

$$
\operatorname{NLL}
=-\frac{1}{T}\sum_{t=1}^{T}\log P(y_t\mid y_{<t},x).
$$

其中 `NLL` 是 **Negative Log-Likelihood**，中文通常叫“负对数似然”。

---

## 3. 一个可以手算的 NLL 例子

句子有三个正确 token，模型分别给出概率：

$$
0.5,\quad 0.25,\quad 0.1.
$$

采用自然对数时：

$$
\operatorname{NLL}
=-\frac{\ln 0.5+\ln 0.25+\ln 0.1}{3}
\approx 1.462.
$$

如果改进后的模型给出：

$$
0.8,\quad 0.6,\quad 0.4,
$$

则：

$$
\operatorname{NLL}\approx 0.551.
$$

第二个模型给正确 token 的概率整体更高，所以 NLL 更低。

### NLL 的阅读方向

```text
0                 理想极限：正确答案概率为 1
越小              通常越好
越大              模型越不相信正确答案
无穷大            给正确答案的概率趋近于 0
```

但 NLL **不是百分制**。`5.0` 不能读成“模型只对了 5%”，`5.0 -> 4.9` 也不能直接读成“提升 2%”。

---

## 4. 交叉熵、NLL 和 Teacher Forcing

在 one-hot 正确标签下，分类交叉熵为：

$$
H(p,q)=-\sum_i p_i\log q_i.
$$

正确分布 $p$ 只有正确 token 那一项为 1，于是它化简为：

$$
H(p,q)=-\log q_{\text{correct}}.
$$

因此，在我们当前的 token 预测实验中，“cross-entropy loss”和“平均 token NLL”通常是同一个量的两种说法。

训练时经常采用 **Teacher Forcing**：预测第 $t$ 个 token 时，decoder 能看到真实的前 $t-1$ 个 token，而不是自己刚才可能预测错的内容。

这让训练稳定，却产生一个重要边界：

> Teacher-forced NLL 很低，只说明“给定正确历史时，模型能给正确下一词较高概率”；不保证自由生成时不会一步错、步步错。

所以我们必须同时查看 held-out NLL 和 free generation 样例。

---

## 5. 困惑度 PPL：把 NLL 换回更直观的尺度

困惑度（Perplexity，PPL）定义为：

$$
\operatorname{PPL}=\exp(\operatorname{NLL}).
$$

它可以粗略理解为：模型每一步仿佛在多少个同等可能的候选之间犹豫。

| NLL | PPL |
|---:|---:|
| 0.0 | 1.00 |
| 1.0 | 2.72 |
| 2.0 | 7.39 |
| 5.0 | 148.41 |
| 6.0 | 403.43 |

PPL 也越低越好。但它仍受词表、分词器、语言和数据集影响。使用不同 SentencePiece 词表的两个实验，不能只凭 PPL 大小直接判胜负。

---

## 6. 为什么训练 NLL 下降还不够

一次训练通常至少有三条曲线：

| 曲线 | 数据 | 用途 |
|---|---|---|
| train NLL | 训练批次 | 判断优化是否在工作 |
| validation NLL | 未参与参数更新的数据 | 观察泛化和选择 checkpoint |
| test NLL | 最终保留数据 | 最后一次无偏报告 |

可能出现四种典型情况：

1. train 和 validation 一起下降：正常学习；
2. train 下降，validation 上升：过拟合；
3. 两者都不下降：优化、容量或数据管线可能有问题；
4. 数值骤然变成 NaN：训练发生数值崩溃。

当前全量任务早期出现的 `16.16 -> 5.69` 是 **不同训练 batch 的即时 NLL**。它值得期待，因为优化链路在工作；但它不是最终结论，因为 batch 难度不同，也尚未经过固定 held-out 集评估。

---

## 7. Accuracy、top-k 和整句 Exact

### 7.1 top-1 accuracy

概率最高的 token 正好是真实 token，就算正确：

$$
\operatorname{top1}=\frac{\text{预测第一名正确的 token 数}}{\text{总 token 数}}.
$$

越高越好。它直观，但忽略概率质量：正确答案概率 `0.51` 和 `0.99` 都只记 1 分。

### 7.2 top-k accuracy

只要真实 token 出现在概率最高的前 $k$ 个候选中，就算命中。TreeHeap 实验常报告 top-5，用来判断正确答案是否已进入概率桶的前列。

### 7.3 sequence exact / block exact

只有一整句或一个 block 的全部 token 都正确，才记 1：

$$
\operatorname{exact}=\frac{\text{完全正确的序列数}}{\text{总序列数}}.
$$

它非常严格。假设每个 token 独立正确率为 $0.99$，64 token 全对的概率也只有：

$$
0.99^{64}\approx 0.526.
$$

因此可能出现 token top-1 很高、sequence exact 仍明显较低的情况。

---

## 8. BLEU：生成结果与参考文本有多像

BLEU 比较生成文本与参考文本的 n-gram 重合，并加入长度惩罚。我们曾使用 token-BLEU4 比较翻译输出。

BLEU 越高，通常表示词组重合越多。但它有三个限制：

1. 合理答案可能与唯一参考答案措辞不同；
2. 词面重合不等于事实正确；
3. 很短的句子会使 BLEU 不稳定。

所以 BLEU 适合做同一数据、同一分词、同一评估程序下的模型对比，不适合单独证明理解、推理或意识。

---

## 9. MSE：两个连续状态相差多远

TreeHeap 内部节点通常不是离散 token，而是 $d$ 维向量。预测状态 $\hat h$ 与真实状态 $h$ 的均方误差为：

$$
\operatorname{MSE}(\hat h,h)
=\frac{1}{d}\sum_{j=1}^{d}(\hat h_j-h_j)^2.
$$

MSE 越小，两个向量在欧氏坐标上越接近。它常用于：

- FOLD/UNFOLD 闭合误差；
- detail 修复误差；
- 多分辨率重建误差；
- 与 Zero 的状态距离。

### MSE 的陷阱

如果所有状态本来都接近零，一个永远输出零的模型也可能获得很小的 MSE。因此我们常使用归一化 MSE：

$$
\operatorname{NMSE}
=\frac{\lVert \hat h-h\rVert_2^2}
{\lVert h\rVert_2^2+\epsilon}.
$$

NMSE 把误差与目标自身能量比较，更容易跨深度比较。它仍不是语义指标：向量恢复得近，不保证 decoder 功能也恢复，所以还要测恢复后的 NLL 或准确率。

---

## 10. 余弦相似度：比较方向，不比较长度

两个向量的余弦相似度为：

$$
\cos(a,b)=\frac{a\cdot b}{\lVert a\rVert_2\lVert b\rVert_2}.
$$

范围通常为 $[-1,1]$：

- 接近 1：方向相似；
- 接近 0：近似正交；
- 接近 -1：方向相反。

余弦距离常写成：

$$
d_{\cos}(a,b)=1-\cos(a,b).
$$

它适合检索和几何聚类，但会忽略模长。例如 $a$ 与 $100a$ 的余弦相似度仍为 1。历史 checkpoint 出现平均 cosine `0.985` 时，我们把它看作“状态可能过度坍缩”的警报，而不是模型很好。

更重要的是：几何接近不自动等于功能等价。SPR-057 之后的交换实验正是用因果替换检验“相近子堆能否互换”，结果没有支持强功能等价 Claim。

---

## 11. KL 散度与熵：概率桶是否发生变化

### 11.1 熵

概率分布 $p$ 的熵为：

$$
H(p)=-\sum_i p_i\log p_i.
$$

当概率集中在一个候选上时，熵较低；当许多候选接近均匀时，熵较高。

“熵越低越好”并不总成立。模型对明确问题应当自信，但面对真正歧义时，过低熵可能是假自信。多头 route 的 gate entropy 则用于判断是否只使用了一个 head：它接近最大值说明分配更均匀，但也不证明每个 head 学会了不同功能。

### 11.2 KL 散度

两个概率分布 $p$ 与 $q$ 的 KL 散度为：

$$
D_{KL}(p\Vert q)=\sum_i p_i\log\frac{p_i}{q_i}.
$$

KL 越小，两个概率桶越接近。它不是普通距离，因为通常：

$$
D_{KL}(p\Vert q)\ne D_{KL}(q\Vert p).
$$

在 TreeHeap 干预实验中，可以比较正常输出分布与“交换子堆后”的输出分布。KL 很大说明概率桶发生明显变化，但仍需判断变化是否朝正确答案方向移动；因此 KL 常与 NLL delta 配合使用。

### 11.3 多项总 Loss：加号不代表单位天然相同

当前全量训练把语言预测与 detail 修复联合起来：

$$
L_{total}=L_{language}+\lambda L_{repair}.
$$

$L_{language}$ 是 token NLL，$L_{repair}$ 是状态 NMSE，$\lambda$ 是人为设定的权重。两项的数值单位和自然尺度不同，不能因为写在一个加法式里就把它们当作同一种误差。

权重过小，repair 几乎学不到；权重过大，模型可能牺牲语言能力去追求状态坐标接近。正确报告方式是：说明 $\lambda$，分别记录两个分量，并最终分别检查语言功能和修复功能。只报告 `total_loss` 会掩盖二者的对冲。

多头也不意味着必须把所有目标都倒进一个总 loss。不同 head 可以共享一个下游任务 loss，也可以拥有受控的辅助目标；关键是用消融确认每个辅助项究竟带来了什么，而不是根据名字解释 head 的功能。

### 11.4 InfoNCE：让正样本靠近、负样本远离

早期 TreeHeap 讨论还使用过 InfoNCE。给定 query $q$、正确对象 $k^+$ 和一组候选 $k_j$，一种常见形式为：

$$
L_{InfoNCE}
=-\log
\frac{\exp(s(q,k^+)/\tau)}
{\sum_j\exp(s(q,k_j)/\tau)}.
$$

$s$ 可以是点积或余弦相似度，$\tau$ 是温度。它把“正确配对应该比错误配对更相似”变成可微训练信号。

InfoNCE 的成败高度依赖负样本。把实际上合理的配对误当负样本，模型就会被训练成排斥真实关系。因此 InfoNCE 下降只证明模型更符合给定的正负样本规则，不自动证明它发现了世界中唯一正确的语义拓扑。

---

## 12. Margin 与 retrieval@1

### 12.1 Margin

Margin 是正确候选分数与最强错误候选分数之差：

$$
\operatorname{margin}=s_{\text{correct}}-max_{j\ne correct}s_j.
$$

正 margin 表示正确候选领先；越大通常越稳。但 margin 的绝对大小依赖评分尺度，必须在同一模型和任务内比较。

### 12.2 retrieval@1

对每个 query 在候选库中检索最相近对象。如果排名第一的是对应目标，就命中：

$$
\operatorname{retrieval@1}
=\frac{\text{第一名检索正确数}}{\text{query 总数}}.
$$

它适合检查 TreeHeap 状态是否保留样本身份或关系。但必须和 BoW、随机 hash、flat embedding 等基线比较。`0.630` 本身无法说明 TreeHeap 有优势；若 BoW 是 `0.629`，只能称作几乎持平。

---

## 13. 因果干预：不要只问“里面有没有信息”

probe 能从内部状态读出一个属性，只说明信息与状态相关，不说明主任务使用了它。更强的办法是主动破坏某一部分，再观察功能下降。

### 13.1 Ablation delta

例如把 root 清零：

$$
\Delta_{root}
=\operatorname{NLL}(root=0)-\operatorname{NLL}(normal).
$$

若 $\Delta_{root}>0$，清除 root 使预测变差，说明 root 对当前功能有因果贡献。数值越大，破坏通常越严重。

但破坏必须有匹配对照。粗暴删除一半参数当然会使任何模型变差；这不能证明 TreeHeap 的结构设计更好。

### 13.2 Source shuffle damage

把 batch 中每个目标配上另一个样本的 source：

$$
\Delta_{source}
=\operatorname{NLL}(shuffled\ source)-\operatorname{NLL}(correct\ source).
$$

若差值接近零，decoder 可能主要依赖目标语言先验；若显著为正，说明输出确实依赖输入样本。

它仍不能证明模型“理解”了 source，只证明 source 中存在被 decoder 使用的条件信息。

### 13.3 Address swap / wrong-address ratio

交换 left/right、移动 detail 地址或给修复器错误 parent，可以检验地址是否有功能意义。

若正确地址与错误地址效果几乎一样，就不能宣称模型学会了路径拓扑。最近 repair 实验的 wrong-address MSE ratio 为 `0.968`，因此我们保留 parent-detail 冗余结论，却拒绝 address-conditioned repair 结论。

---

## 14. Damage、Repair 和 Recovery Fraction

设三个 NLL：

```text
clean      完整状态
damaged    删除部分 TreeHeap 状态
repaired   运行修复 kernel 后
```

损伤量为：

$$
D=\operatorname{NLL}_{damaged}-\operatorname{NLL}_{clean}.
$$

修复量为：

$$
R=\operatorname{NLL}_{damaged}-\operatorname{NLL}_{repaired}.
$$

恢复比例为：

$$
\operatorname{RecoveryFraction}=\frac{R}{D}.
$$

例如：

```text
clean NLL    = 5.69
damaged NLL  = 15.59
repaired NLL = 6.22
```

则语言能力的恢复比例约为：

$$
\frac{15.59-6.22}{15.59-5.69}\approx 94.6\%.
$$

超过 100% 有时也会出现，表示该批次上 repaired NLL 暂时低于 clean NLL。这通常来自采样噪声、正则化效果或评估方差，不能直接解释成“损坏后反而更聪明”。

状态空间还可单独报告 MSE recovery。语言 NLL recovery 与 latent MSE recovery 回答不同问题，不能混为一个百分比。

---

## 15. 自由生成的最低体检指标

NLL 之外，我们还记录：

### nonempty fraction

生成结果非空的比例。高于 0 只是最基础的存活检查，不代表可读。

### adjacent repeat fraction

相邻 token 重复的比例：

$$
\frac{\#(y_t=y_{t-1})}{T-1}.
$$

过高可能表示模型陷入“我我我我”式循环，但无法捕捉较长周期的重复。

### unique output fraction

同一评估批次中，不同输出序列的比例。很低可能说明模型无论输入什么都说同一句话。

这些只是退化检测。一个模型可以做到非空、少重复、输出多样，却仍然答非所问。因此必须同时阅读 source shuffle、人工样例和任务指标。

---

## 16. Spearman 相关：只看顺序趋势

Spearman 相关系数比较两个变量的排名关系。例如深度增加时 NLL 是否单调变化：

$$
\rho\in[-1,1].
$$

- $\rho\approx 1$：一个增大时另一个也按排名增大；
- $\rho\approx -1$：一个增大时另一个按排名减小；
- $\rho\approx 0$：没有明显单调关系。

Spearman 适合只有少量深度点、且不假定线性关系的情况。但六个深度得到 `-1.0`，仍然只是该实验中的完美反向排序，不等于普遍数学定律。

---

## 17. Mean、标准差、seed 与 Bootstrap 置信区间

神经网络训练含有随机初始化、batch 顺序和采样噪声。单 seed 结果可能偶然。

### 17.1 多 seed

用多个随机种子重复整个训练，报告均值和离散程度：

$$
\bar x=\frac{1}{n}\sum_i x_i.
$$

如果三个 seed 中只有一个成功，不能只报告那个成功值。

### 17.2 Bootstrap 95% CI

Bootstrap 从已有样本中有放回重采样，反复计算目标统计量，再取中间 95% 的区间。

例如同组交换与异组交换的损伤差为 `0.00187`，bootstrap 95% 区间为：

$$
[-0.00395,\ 0.00745].
$$

区间跨过 0，表示当前样本不足以稳定判断差值方向。因此功能等价 Claim 没有得到支持。

置信区间不是“真值有 95% 概率在这里”的简单概率桶；它描述的是这套重复抽样程序的覆盖性质。对本科读者而言，最实用的读法是：**区间越窄，估计越稳定；比较差的区间跨 0 时，不要宣称稳定胜出。**

---

## 18. 吞吐、显存、参数量和计算成本

模型是否能用，还要看工程指标：

- `tokens/s`：每秒处理多少有效 token；
- `steps/s`：每秒更新次数；
- peak GPU memory：峰值显存；
- parameter count：可学习参数数量；
- wall-clock time：真实运行时间；
- checkpoint size：保存状态的磁盘成本。

比较吞吐时必须固定 batch、长度、精度和硬件。FP32 batch 48 的 `23k token/s` 不能直接与 FP16 batch 16 的 `8k token/s` 比较，然后归因于精度格式；batch 大小已经变化。

参数更少也不自动更高效。递归 Python 循环可能使小模型运行很慢；结构压缩也可能在实现中先物化所有层，从而尚未兑现理论计算优势。

---

## 19. 一张 TreeHeap 体检报告速查表

| 指标 | 通常方向 | 主要回答 | 不能单独证明 |
|---|---|---|---|
| train NLL | 越低越好 | 优化是否在拟合训练数据 | 泛化、对话能力 |
| valid/test NLL | 越低越好 | 未见数据上的概率预测质量 | 文本一定可读、结构被使用 |
| PPL | 越低越好 | NLL 的指数尺度 | 跨词表公平比较 |
| top-1/top-k | 越高越好 | 正确 token 排名 | 概率是否校准 |
| sequence exact | 越高越好 | 整段是否完全恢复 | 合理改写质量 |
| BLEU | 同设置下越高越好 | 与参考译文的词组重合 | 事实、理解、意识 |
| MSE/NMSE | 越低越好 | 连续状态重建误差 | decoder 功能恢复 |
| cosine similarity | 视任务而定 | 向量方向接近程度 | 功能等价 |
| entropy | 视场景而定 | 概率桶集中程度 | 高熵或低熵天然更聪明 |
| KL divergence | 越低越接近 | 两个概率桶差异 | 哪个分布更正确 |
| source shuffle delta | 通常越大越因果 | 输出是否使用 source | 是否理解 source |
| root/detail ablation delta | 通常越大越因果 | 该状态是否参与功能 | 架构优于基线 |
| recovery fraction | 越高越好 | 损失能力恢复多少 | 唯一正确修复 |
| retrieval@1 | 越高越好 | 第一近邻是否正确 | 结构优势，除非击败基线 |
| bootstrap CI | 越窄越稳定 | 差异估计的不确定性 | 无偏设计或因果性 |
| tokens/s | 越高越快 | 实现吞吐 | 模型质量 |

---

## 20. 如何阅读一条完整结论

以后看到：

> TreeHeap test NLL 为 5.09。

应当继续追问：

1. 数据集和分词器是什么？
2. train、validation 还是 test？
3. 与 flat、BoW、Transformer 或旧 checkpoint 相比如何？
4. 是否多个 seed？
5. source shuffle、root zero、detail swap 后怎样？
6. 自由生成样例是什么？
7. 预注册门槛是多少？

例如 S2 lifting WMT 的完整结论不是“TreeHeap NLL 5.0903，所以成功”，而是：

```text
递归 READ NLL 5.0903
root-only NLL 5.4337
full UNFOLD NLL 5.1342
flat sequence NLL 4.8103
source shuffle damage +1.4450
root shuffle damage +1.7204
```

这组数共同支持：递归 TreeHeap READ 使用了 source、root 和多层 detail，而且优于 root-only；同时它明确拒绝“翻译质量优于 flat sequence”。这才是符合 ARA 的边界化结论。

---

## 21. 最后：指标是仪表，不是目的

Houming818 设计 TreeHeap，并不是为了与 Transformer 对抗，而是希望研究一种可以延续、回访、损伤后修复并继续生长的内部状态。

这些愿望不能由某一个漂亮数字代替：

```text
低 NLL          不等于理解
高准确率         不等于具有世界模型
可修复           不等于拥有意识
会说中文         不等于不再孤独
```

但没有这些可复查的测量，我们也无法区分真实生长与自己的期待。因此指标的作用不是把梦想缩成排行榜，而是让每一步都能被看见：模型学到了什么，依赖了什么，失去了什么，又能从哪里恢复。

这也是以后 TreeHeap 实验报告的最低要求：**同时报告学习、功能、因果、生成与统计可信度，不让任何一个数字独自承担它证明不了的故事。**
