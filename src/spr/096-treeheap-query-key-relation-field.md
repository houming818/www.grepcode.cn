---
title: "[SPR-096] 关系不在模块里：TreeHeap 的 Query-Key 概率结构"
date: 2026-10-16
lastmod: 2026-10-16
weight: 96
author: Houming818 & Trinity (Codex)
description: "从 Transformer 的动态 QK 关系图出发，重新定义 TreeHeap 中关系的位置：关系不是额外模块，而是查询与树节点在不同分辨率上的条件概率结构；FOLD 的任务也由混合向量改写为压缩可查询的关系响应。"
keywords: [TreeHeap, SPR, QueryKey, 动态关系场, 条件概率, FOLD, 多分辨率, RelationClosure, ARA]
tags: [SPR, TreeHeap, QueryKey, RelationField, Multiresolution, FOLD, ARA]
---

# 先说这次改了什么

前面的 TreeHeap 研究经常把问题写成：怎样把两个 child 隐态压成一个 parent，再让 READ 从 parent
恢复信息。这个说法默认了一个前提：**只要 parent 的数值足够丰富，句子关系就会自然包含在里面。**

最近对 Transformer 的拆解提醒我们，这个前提并不充分。Transformer 不只是保存 token 状态，
它还会对当前输入临时计算一张关系图：

$$
R(X)=Q(X)K(X)^{\mathsf T}.
$$

其中，参数矩阵规定怎样生成 Query 和 Key；真正的关系 \(R(X)\) 则随当前输入变化。换一句话：
**参数保存造关系的规则，前向计算生成这一次输入的关系。**

TreeHeap 过去有层级、有地址、有 FOLD、有 READ，却没有把这个对象单独定义清楚。于是我们会在
FOLD 公式里不断加入平均、差分、残差、双线性交互，然后用最终 NLL 判断哪个公式“像关系”。
这条路能够发现干预效应，却很难说明 FOLD 到底应该保存什么。

本文提出一个更窄的重构：

> 关系不是 TreeHeap 旁边新增的一个模块。关系就在树上，是当前 Query 与各尺度节点之间形成的
> 动态条件概率结构。FOLD 的任务不是凭空制造关系，而是让这种关系能够跨尺度闭合并被高效查询。

这是一篇理论状态与实验合同，不是新架构已经成功的公告。

{{< claim id="SPR-096-RELATION-FIELD-C01" status="hypothesis" >}}
若 TreeHeap 的内部节点能够以有限容量近似其后代 leaf 对一族 Query 的联合响应，并且这种近似在
减少访问节点数时保持 leaf 后验、路径排序和任务损失，则 TreeHeap 可以成为一种多分辨率关系
索引。当前证据只支持“模型会使用部分关系分支”，尚未支持该闭合假设。
{{< /claim >}}

![Transformer 全连接关系图与 TreeHeap 递归关系场](/spr/spr-096-treeheap-relation-field.svg)

# 1. 先把四种对象分开

设一句话有 \(T\) 个 token，隐态为：

$$
X\in\mathbb{R}^{T\times d}.
$$

Transformer 使用训练参数：

$$
W_Q\in\mathbb{R}^{d\times d_k},
\qquad
W_K\in\mathbb{R}^{d\times d_k},
$$

生成当前输入的特征：

$$
Q=XW_Q,
\qquad
K=XW_K.
$$

然后计算关系分数与归一化关系图：

$$
S=\frac{QK^{\mathsf T}}{\sqrt{d_k}},
\qquad
A=\operatorname{softmax}_{\mathrm{row}}(S).
$$

这里至少有四类不能混写的对象：

| 对象 | 是否训练参数 | 是否随输入变化 | 含义 |
|---|---:|---:|---|
| \(W_Q,W_K\) | 是 | 否 | 生成 Query/Key 特征的规则 |
| \(Q(X),K(X)\) | 否 | 是 | 当前 token 的查询侧和被查询侧特征 |
| \(S(X)\) | 否 | 是 | 未归一化的动态关系分数 |
| \(A(X)\) | 否 | 是 | 当前输入上的条件读取概率 |

所以“QK 是一个关系函数”这句话只说对了一半。更准确地说：

$$
(W_Q,W_K)\text{ 定义关系族},
\qquad
R(X)=Q(X)K(X)^{\mathsf T}\text{ 是当前关系实例}.
$$

这也解释了为什么不能只观察参数矩阵就宣称找到了主谓宾关系。同一组参数面对不同句子，会生成
不同的关系图。

# 2. 一个三词 toy：关系不是三个静态标签

考虑三个位置：

```text
p = Sisyphus
r = pushes
l = stone
```

如果只数无向位置对，确实有三组：

```text
p-r, p-l, r-l
```

但 Query-Key 关系通常有方向。三个位置的完整有向分数矩阵是 \(3\times3\)，包含自关系时有
9 个分数，不含自关系时有 6 条有向边：

$$
S_{ij}=q_i^{\mathsf T}k_j.
$$

例如 \(S_{r,l}\) 表示 `pushes` 位置以自己的 Query 去匹配 `stone` 位置的 Key；
\(S_{l,r}\) 是反方向，二者一般不相等。

它也不等于普通卷积核。卷积通常在每个局部窗口复用同一组固定系数；QK 的参数规则可以共享，
但具体边权由两端当前状态共同决定：

$$
S_{ij}=x_i^{\mathsf T}W_QW_K^{\mathsf T}x_j.
$$

因此它更接近**输入相关的双线性关系场**。如果把中间矩阵记为：

$$
M=W_QW_K^{\mathsf T},
$$

则：

$$
S_{ij}=x_i^{\mathsf T}Mx_j.
$$

\(M\) 是共享规则，\(S_{ij}\) 才是当前两个位置之间的关系值。

# 3. 把同一件事放到 TreeHeap 上

TreeHeap 不必复制完整的 \(T\times T\) 矩阵。它可以让每个树节点 \(v\) 拥有状态 \(h_v\)，再
从状态产生两类特征：

$$
q_v=\phi(h_v),
\qquad
k_v=\psi(h_v).
$$

当某个 Query \(q\) 到达 parent \(p\) 时，它不直接读取所有 leaf，而是在两个 child 中计算：

$$
z_L(q)=q^{\mathsf T}k_L,
\qquad
z_R(q)=q^{\mathsf T}k_R.
$$

局部路由概率为：

$$
P(c\mid q,p)
=\frac{\exp(z_c(q)+\log\pi_{c\mid p})}
{\sum_{j\in\{L,R\}}\exp(z_j(q)+\log\pi_{j\mid p})}.
$$

其中 \(\pi_{c\mid p}\) 是该分叉的背景先验。它可以来自语料统计或训练参数，但必须明确来源，
不能与当前 Query 的证据混为一谈。

一条 leaf 路径的后验是各层条件概率的乘积：

$$
P(\ell\mid q)
=\prod_{d=1}^{D}P(c_d\mid q,p_d).
$$

对应路径 NLL 为：

$$
-\log P(\ell\mid q)
=\sum_{d=1}^{D}-\log P(c_d\mid q,p_d).
$$

这与 SPR-095 中 parent 概率质量的条件分解一致，但多了一个关键对象：分叉概率不再只是固定
词频，它可以由当前 Query 动态改变。

因此，树中的关系不是一个外挂矩阵，而是：

```text
当前 Query
  -> 在当前 parent 上比较 child key
  -> 得到局部条件概率
  -> 沿路径递归更新 leaf 后验
```

# 4. Parent 到底应该保存什么

设一个 parent \(p\) 的全部后代 leaf 为 \(D(p)\)。若直接读取 leaf，Query 对这个区域的总响应
可以精确定义为：

$$
Z_p(q)
=\sum_{\ell\in D(p)}\exp(q^{\mathsf T}k_\ell).
$$

取对数后：

$$
z_p(q)
=\log Z_p(q)
=\operatorname{logsumexp}_{\ell\in D(p)}
\left(q^{\mathsf T}k_\ell\right).
$$

对只有两个 child 的节点，它满足严格递归：

$$
z_p(q)
=\operatorname{logsumexp}
\left(z_L(q),z_R(q)\right).
$$

这给出了一个此前缺失的物理量：**parent 不是某个神秘的句义向量，而是其后代区域对 Query 的
聚合响应函数。**

它还给出了 FOLD 的明确任务：

> FOLD 应压缩 \(z_p(q)\) 这类可查询响应，而不只是把 \(h_L,h_R\) 混成另一个固定向量。

# 5. 为什么一个固定 parent key 通常不够

最简单的做法是让 parent 只有一个 Key \(k_p\)，并要求：

$$
q^{\mathsf T}k_p
\approx
\operatorname{logsumexp}
\left(q^{\mathsf T}k_L,q^{\mathsf T}k_R\right).
$$

但左侧是关于 \(q\) 的线性函数，右侧通常是光滑凸函数。除非两个 child 的响应在目标 Query
范围内近乎相同或始终由同一个 child 占优，否则不存在一个固定 \(k_p\) 能对所有 \(q\) 精确成立。

这不是训练时间不够造成的偶然现象，而是函数族容量不同：

$$
\nabla_q^2(q^{\mathsf T}k_p)=0,
$$

而：

$$
\nabla_q^2\operatorname{logsumexp}
\left(q^{\mathsf T}k_L,q^{\mathsf T}k_R\right)
\succeq 0,
$$

且在两个 child 都有非零概率、Key 又不相同时通常严格非零。

所以过去的问题可能不是“parent 参数太少”这么简单，而是我们要求一个固定向量表示一整个
Query 相关的响应曲面。增加隐态宽度可以缓解近似误差，却不会自动改变这个函数族差异。

# 6. 可训练的 Parent 候选

这不意味着 parent 必须保存全部 leaf。可以从低成本到高容量测试四种表示。

## 6.1 单 Key 基线

$$
\widehat z_p(q)=q^{\mathsf T}k_p.
$$

优点是快、内存小；它也是必须保留的下界基线。

## 6.2 多原型 Key

令 parent 保存 \(m\) 个原型：

$$
\widehat z_p(q)
=\log\sum_{a=1}^{m}w_a
\exp(q^{\mathsf T}k_{p,a}),
\qquad
w_a\ge0.
$$

当 \(m=1\) 时退化为单 Key；随着 \(m\) 增加，它可以近似更复杂的响应曲面。这里的 \(m\) 是
关系容量，不是随意增加的隐藏层宽度。

## 6.3 低秩关系基

保存少量共享基与节点系数：

$$
k_{p,a}=B_a c_p.
$$

共享基 \(B_a\) 学习跨节点通用的关系方向，\(c_p\) 只记录当前区域怎样组合这些方向。这更接近
低功耗设备上的参数复用目标。

## 6.4 必要时下钻

parent 先给出近似和误差上界；若当前 Query 处于两个原型都不能确定的区域，再访问 child。
这使 TreeHeap 的目标从“每次完整恢复整棵树”变成“按 Query 的不确定性决定读取分辨率”。

这四种方案共同保留一个原则：**粗尺度负责快速排除大块无关区域，细尺度只解决剩余歧义。**

# 7. 为什么不能只用最终 NLL 评价关系

最终 token NLL 仍然是系统目标：

$$
L_{token}=-\log P(y_{gold}\mid x).
$$

但它不足以单独评价关系结构，原因有三个。

第一，FOLD、READ 和 Decoder 可以互相补偿。关系分支错了，Decoder 仍可能利用词频或旁路降低
NLL；关系分支有效，其他瓶颈也可能让最终 NLL 看不出来。

第二，Query-Key 坐标并不唯一。对任意可逆矩阵 \(A\)：

$$
q'=Aq,
\qquad
k'=A^{-\mathsf T}k,
$$

都有：

$$
q'^{\mathsf T}k'=q^{\mathsf T}k.
$$

因此不能用“参数长得像不像”判断关系是否正确，应比较动态分数、后验和干预结果。

第三，TreeHeap 还有一个独立目标：减少访问和内存。即使两种结构 NLL 相同，如果一种必须展开
全部 leaf，另一种只访问少量节点，它们也不是同一个工程结果。

所以 SPR-096 建议至少同时测五类量：

| 指标 | 回答的问题 |
|---|---|
| relation closure error | parent 响应是否近似后代的精确 logsumexp |
| leaf posterior KL | 压缩读取是否保持完整 leaf 后验 |
| top-k path recall | 高概率目标路径是否被提前剪掉 |
| token NLL / BLEU | 关系近似是否传导到任务结果 |
| visited nodes / latency / memory | 是否真的获得递归查询收益 |

关系闭合误差可以写成：

$$
E_{rel}
=\mathbb E_q\left[
\left(
\widehat z_p(q)
-\operatorname{logsumexp}(z_L(q),z_R(q))
\right)^2
\right].
$$

leaf 后验失真则用：

$$
E_{KL}
=\mathbb E_q\left[
D_{KL}\left(P_{dense}(\ell\mid q)
\;\|\;
P_{tree}(\ell\mid q)\right)
\right].
$$

# 8. 现有实验到底支持到哪一步

过去的地址、head、Butterfly 和 detail 干预已经反复说明：TreeHeap 的输出不是只靠 Decoder 猜出来
的，内部有任务相关结构。例如，root-only 压缩中破坏左右地址配对使 NLL 增加 `2.6252`；早期
STONE-1 中交换地址增加 `1.3545`，强制退回固定代数 codec 增加 `1.0984`；C09 的 detail
shuffle 最少增加 `0.5634`。

这些结果证明“结构被使用”，但不能反推“被使用的就是正确关系场”。

2026-10-16 的真实语料匹配参数 smoke 又比较了三种 FOLD：

| FOLD | Test NLL | BLEU | source shuffle damage | pair break mean |
|---|---:|---:|---:|---:|
| lifting | 7.56635 | 0.3557 | +0.15218 | +0.02841 |
| MLP | 7.52975 | 0.2231 | +0.19812 | +0.07180 |
| bilinear | **7.52747** | 0.2134 | **+0.28515** | **+0.11255** |

bilinear 模型训练后只清零关系分支，Test NLL 增加 `0.07034`。这说明显式双线性交互确实进入
了因果计算链，而且比两个控制更敏感于 source shuffle 和 pair breaking。

但 bilinear 与 MLP 的 NLL 只差 `0.00228`，全部 BLEU 都低于 `0.36`，生成不可用。最严格的
结论只能是：

{{< evidence grade="E1" source="SameTime ARA s3-generation/corpus_fold_relation_smoke, R2 balanced32, seed 20261016" >}}
真实语料 smoke 支持显式 bilinear 关系分支被模型使用；它没有证明 bilinear 是唯一正确的 F，
没有证明关系在树上闭合，也没有证明生成质量改善。
{{< /evidence >}}

# 9. 下一轮实验合同

下一轮不直接比较“哪个大模型 BLEU 更高”，而是先测关系结构是否能在树上成立。

## 阶段 A：建立 dense teacher

在固定真实语料切片上训练一个小型 dense Query-Key reader。冻结后记录：

$$
P_{dense}(\ell\mid q).
$$

这里的 teacher 不是语言真值，只是提供同一批 Query 下可重复的完整关系分布。

## 阶段 B：把 leaf Key 放入固定树

树拓扑、seed、数据顺序、Query 集合全部固定。先不训练 Decoder，只让 parent 近似其后代响应。

比较：

```text
single-key parent
multi-prototype parent: m = 2 / 4 / 8
parameter-matched MLP parent
random topology control
learned topology
```

## 阶段 C：逐分辨率读取

对相同 Query，记录访问深度 `1/2/4/.../D` 时的：

```text
closure error
leaf posterior KL
top-k recall
visited nodes
```

如果分辨率增加时后验逐步接近 dense teacher，同时较粗层已经排除大量无关 leaf，才有资格说
TreeHeap 形成了多分辨率关系索引。

## 阶段 D：接回语言任务

前三阶段通过后，再连接 READ 与 Decoder。任务指标只观察，不因为短期非单调自动停止；真正的
结构门是：关系近似是否可复现、干预是否因果、查询成本是否下降。

需要保留的否证条件包括：

1. parent 原型增加后，closure error 仍不下降；
2. TreeHeap 后验与 dense 后验的 KL 不随读取深度下降；
3. learned topology 不优于匹配容量的随机树；
4. 关系分支消融无影响，或 Decoder 完全绕过关系路径；
5. 达到相同后验误差时，TreeHeap 没有减少节点访问、内存或延迟。

# 10. 与 094、095 的关系

现在可以把三篇的职责连成一条链：

```text
SPR-094
语料能否形成多尺度概率坐标？
        |
        v
SPR-095
上下文进入后，候选 token 后验能否逐步更新？
        |
        v
SPR-096
当前 Query 与各尺度节点的动态关系，能否在树上闭合并按需读取？
```

094 解决静态背景坐标，095 解决当前事件的概率更新，096 把更新所依赖的关系从“隐态里应该有”
改成可计算、可干预、可测误差的对象。

这也修正了对 F 函数的期待。我们不再要求先猜出一个包办全部语义的万能 F。更可操作的目标是：

$$
F_p:\{\text{child relation responses}\}
\longrightarrow
\text{bounded-capacity parent response}.
$$

F 是否合格，由 Query 分布上的闭合误差、后验保持和查询成本共同决定，而不是看公式是否优美。

# 11. 当前理论状态

截至 SPR-096，可以较有把握地说：

- TreeHeap 的地址、细节与递归结构会因果影响输出；
- 多尺度概率区域能够保存并读取上下文条件信息；
- 显式 bilinear 分支能在真实语料 smoke 中被模型利用；
- parent 概率质量可以条件分解，parent 关系响应也有精确的 logsumexp 递归定义。

仍然不能说：

- 当前 FOLD 已经保存了句子关系；
- 一个固定 parent 向量足以表示所有 Query 下的后代结构；
- QK、MLP 或 lifting 中任一个已经是 TreeHeap 的最终 F；
- TreeHeap 已经在质量、功耗或内存上优于 Transformer；
- 关系闭合自然等于语义理解。

这篇真正完成的不是“找到答案”，而是把问题从：

```text
哪个 FOLD 公式看起来更合理？
```

改写成：

```text
一个 parent 用多少关系容量，
能在多少 Query 上近似后代响应，
以多大后验误差换取多少查询成本？
```

这是可以被数学分析、真实语料和工程账本共同回答的问题。下一步的 TreeHeap，不需要再凭一句
“隐态包含信息”向前走，而要证明：关系怎样进入树、怎样跨尺度保存、怎样被 READ 按需取回。

