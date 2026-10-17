---
title: "[SPR-096] R 就是 QK：TreeHeap 的树上关系场"
date: 2026-10-16
lastmod: 2026-10-17
weight: 96
author: Houming818 & Trinity (Codex)
description: "明确 TreeHeap 中 R 的定义：R 就是 Query-Key 关系计算。每条 parent-child 边产生关系分数，softmax 将其变成路由概率，READ/Value 负责读取内容。"
keywords: [TreeHeap, SPR, Relation, QueryKey, QK, READ, 多分辨率, 关系场, ARA]
tags: [SPR, TreeHeap, Relation, QueryKey, READ, ARA]
---

# 结论先行

本文只固定一个核心定义：

> **R 就是 QK。**

在 TreeHeap 中，parent \(p\) 与 child \(c\) 之间的关系写成：

$$
R_{p,c}(q,z_p)
=
Q(q,h_p,z_p)^{\mathsf T}
K(h_c,e_{p,c},z_{p\rightarrow c}).
$$

其中：

- \(c\in\{l,r\}\)；
- \(e_{p,c}\) 表示当前 left/right 边的类型；
- \(z_p\) 表示 root 到当前 parent 的路径前缀编码；
- \(z_{p\rightarrow c}\) 表示把当前候选边追加到前缀后的路径编码。

R 的职责只有一个：计算当前 Query 与候选 child 的关系强度。它不负责把 parent 状态变成 child
状态，也不直接生成 token。

完整链路应当分成三件事：

~~~text
QK / R：     计算关系分数
softmax：    把关系分数变成路由概率
Value/READ：按路由概率读取内容
~~~

上一篇版本把 R 扩大成了“路由加状态变换”。这个定义过宽，也会把 QK、READ 和 Decoder 混成
同一个模块。本文据此重新整理整个结构。

{{< claim id="SPR-096-TREE-QK-C01" status="hypothesis" >}}
TreeHeap 可以把 Transformer 的全连接 token-to-token QK 关系，改写为树上逐边计算的 QK 关系场。
若局部边关系能够组合成稳定的路径后验，并在有限访问预算下支持语言任务，则树结构可能提供一种
稀疏的多分辨率关系查询机制。当前证据尚未证明该假设。
{{< /claim >}}

![TreeHeap 中 R、路由与 READ 的边界](/spr/spr-096-treeheap-relation-field.svg)

# 第一章：R 的精确定义

## 1.1 Transformer 中的 QK

给定第 \(i\) 个 Query 和第 \(j\) 个 Key：

$$
q_i=W_Qh_i,
\qquad
k_j=W_Kh_j.
$$

它们的关系分数是：

$$
R_{ij}
=
\frac{q_i^{\mathsf T}k_j}{\sqrt{d_k}}.
$$

把所有 \(R_{ij}\) 排在一起，就得到关系矩阵：

$$
R
=
\frac{QK^{\mathsf T}}{\sqrt{d_k}}.
$$

因此，R 不是另一个新模块。R 就是 QK 产生的关系。

## 1.2 TreeHeap 中的 QK

TreeHeap 不必让一个 Query 同时比较所有 token。它可以在当前 parent 只比较两个候选 child：

$$
R_{p,l}
=
\frac{q_p^{\mathsf T}k_l}{\sqrt{d_k}},
\qquad
R_{p,r}
=
\frac{q_p^{\mathsf T}k_r}{\sqrt{d_k}}.
$$

然后计算左右路由概率：

$$
\alpha_{p,l},\alpha_{p,r}
=
\operatorname{softmax}
\left(R_{p,l},R_{p,r}\right).
$$

这里：

- \(R_{p,c}\) 是关系；
- \(\alpha_{p,c}\) 是由关系得到的路由概率；
- 二者都不是被读取的内容。

## 1.3 “每条边都是一次 R”是什么意思

当我们说“每一次 \(p\rightarrow l\) 或 \(p\rightarrow r\) 都是一次 R”，准确含义是每条候选边
都要计算一次 QK 关系分数：

~~~text
                  q_p
                 /   \
          q_p · k_l   q_p · k_r
              |           |
           R(p,l)       R(p,r)
~~~

它不是说每条边都要执行一个额外的隐藏状态变换。

## 本章结论

R 是关系分数或关系场。它由 QK 计算产生；状态读取属于 Value/READ。

# 第二章：R、路由与内容必须分开

## 2.1 R 只回答“相关不相关”

R 的输出是一个标量：

$$
R_{p,c}\in\mathbb R.
$$

它回答当前 Query 与这条 child 边有多相关。一个标量不能单独携带完整 child 内容，也不能替代
child 状态。

## 2.2 softmax 回答“走多少”

关系分数经过归一化：

$$
P(c\mid p,q)
=
\frac{\exp R_{p,c}}
{\exp R_{p,l}+\exp R_{p,r}}.
$$

这一步把任意实数分数变成左右分支上的条件概率。因此：

$$
R\neq P(c\mid p,q),
$$

但 \(P(c\mid p,q)\) 由 R 决定。

## 2.3 Value/READ 回答“读什么”

若两个 child 对应的内容为：

$$
v_l=W_Vh_l,
\qquad
v_r=W_Vh_r,
$$

则一次软 READ 可以写成：

$$
o_p
=
\alpha_{p,l}v_l
+
\alpha_{p,r}v_r.
$$

硬路由则选择概率更高的一侧继续下钻：

$$
c^*=\arg\max_{c\in\{l,r\}}R_{p,c}.
$$

无论软读还是硬路由，内容都来自 Value 或节点状态，不来自 R 本身。

## 2.4 Decoder 最后生成词表 logits

READ 得到查询结果后，Decoder 再生成词表分布：

$$
\operatorname{logits}
=
W_{dec}h_{read}+b_{dec}.
$$

| 组件 | 职责 |
|---|---|
| FOLD | 建立多分辨率节点状态 |
| QK / R | 计算 Query 与边或节点的关系 |
| softmax | 把关系分数归一化为路由概率 |
| Value/READ | 读取节点内容 |
| Decoder | 把读取结果映射到 token 概率 |

## 本章结论

R 决定“相关性”，READ 负责“内容”，Decoder 负责“词表输出”。三者不能用同一个词代替。

# 第三章：树上的关系场

## 3.1 先把路径编码成 QK 的输入

设 left 边编码为 \(b=0\)，right 边编码为 \(b=1\)。root 到第 \(d\) 层的路径前缀为：

$$
\pi_d=(b_1,b_2,\ldots,b_d).
$$

可以先用 heap 地址构造一个无歧义的基础编码：

$$
a_0=0,
\qquad
a_{d+1}=2a_d+b_{d+1},
$$

$$
z_d=E_{path}(d,a_d).
$$

深度 \(d\) 必须保留，因为路径 \(0\) 与 \(00\) 的整数值相同，但它们处于不同分辨率。

对当前 parent \(p_d\)，把查询内容、当前节点和路径前缀一起投影为 Query：

$$
q_d
=
W_Q
\left[
h_q\,\Vert\,h_{p_d}\,\Vert\,z_d
\right].
$$

对候选 child \(c\in\{l,r\}\)，先把该边追加到路径前缀：

$$
z_{d\rightarrow c}
=
E_{path}(d+1,2a_d+b_c),
$$

再构造候选 Key：

$$
k_{d,c}
=
W_K
\left[
g_{p_d,c}\,\Vert\,e_c\,\Vert\,z_{d\rightarrow c}
\right].
$$

于是当前边的关系仍然是 QK：

$$
R_{p_d,c}
=
\frac{q_d^{\mathsf T}k_{d,c}}{\sqrt{d_k}}.
$$

路径编码没有改变 R 的定义。它只是让 QK 能区分“同一个局部状态出现在不同路径和深度”的情况。

基础 smoke 可以先用固定的二进制/heap 路径编码；正式训练再比较固定编码与可学习
\(E_{path}\)。这样不会一开始就把路径规律藏进一个容量过大的查找表。

## 3.2 一条路径上的关系

设 root 到 leaf 的路径为：

$$
\pi=(p_0,p_1,\ldots,p_D).
$$

每一层都有一个条件路由概率：

$$
P(p_{d+1}\mid p_d,q_d)
=
\operatorname{softmax}
\left(R_{p_d,l},R_{p_d,r}\right)_{p_{d+1}}.
$$

整条路径的概率为：

$$
P(\pi\mid q)
=
\prod_{d=0}^{D-1}
P(p_{d+1}\mid p_d,q_d).
$$

在 log 空间中：

$$
\log P(\pi\mid q)
=
\sum_{d=0}^{D-1}
\log P(p_{d+1}\mid p_d,q_d).
$$

因此，路径不是多个隐藏状态变换的复合，而是多次局部 QK 关系判断形成的条件概率链。

## 3.3 关系场是什么

对一棵树的所有边计算 R：

$$
\mathcal R(q)
=
\left\{
R_{p,c}(q)
\mid
(p,c)\in E
\right\}.
$$

这个集合就是当前 Query 在树上的关系场。不同 Query 会产生不同的关系场：

$$
\mathcal R(q_1)\neq\mathcal R(q_2).
$$

树的拓扑不变，但被激活的路径可以改变。

## 3.4 多分辨率体现在哪里

在浅层停止，只访问较粗的 parent；继续向下，则用新的 QK 关系消除更多候选路径。

我们希望观察到：

$$
H(C_{d+1}\mid q)
\leq
H(C_d\mid q).
$$

这不是结构定理，而是需要检验的目标：随着有效证据进入，候选路径后验应逐层集中。

“分辨率提高”在这里不是隐藏值天然变大或变小，而是 Query 对候选区域的区分逐步变细。

## 本章结论

TreeHeap 的多分辨率关系能力，来自同一个 Query 在不同深度对候选区域进行逐层 QK 判断。

# 第四章：FOLD 与 R 的接口

## 4.1 FOLD 不等于 R

FOLD 定义 child 怎样形成 parent：

$$
h_p=F(h_l,h_r).
$$

R 定义 Query 怎样比较 parent 下的候选：

$$
R_{p,c}
=
Q(q,h_p,z_p)^{\mathsf T}
K(h_c,e_{p,c},z_{p\rightarrow c}).
$$

二者可以联合训练，但不是同一个计算。

## 4.2 Key 从哪里来

如果 FOLD 后只保留 \(h_p\)，READ 时却仍需要完整 \(h_l,h_r\) 才能计算 Key，那么树没有减少
访问量。

因此 parent 至少要暴露一个紧凑的 child 目录：

$$
D_p=\{k_{p,l},k_{p,r},a_{p,l},a_{p,r}\}.
$$

其中 \(k_{p,l},k_{p,r}\) 是左右分支的关系 Key，\(a_{p,l},a_{p,r}\) 是 child 地址或读取句柄。
目录还应提供当前节点的路径前缀编码 \(z_p\)，或提供能够确定性重建它的 heap 地址与深度。

Query 先与这个目录计算 R，选中分支后才访问 child 内容：

~~~text
先读小目录并计算 QK
        ↓
再访问被选中的 child 内容
~~~

## 4.3 压缩预算必须包含目录

parent 的成本不能只算 \(h_p\)，还应计入：

$$
B_p
=
B(h_p)
+B(D_p)
+B(\operatorname{residual}_p).
$$

如果 child Key、地址和残差接近完整保存两棵子树，TreeHeap 即使能正确 READ，也没有实现有效
压缩。

## 本章结论

FOLD 负责形成节点；R 负责查询节点。两者真正的接口是 parent 保存的紧凑 Key 目录。

# 第五章：参数怎样共享

## 5.1 共享的是 QK 规则

令当前查询状态为 \(x\)，child 目录中的原始描述为 \(g_{p,c}\)。最小方案在全树共享：

$$
q_{p,c}=W_Q[x\,\Vert\,h_p\,\Vert\,z_p],
\qquad
k_{p,c}=W_K[g_{p,c}\,\Vert\,e_c\,\Vert\,z_{p\rightarrow c}].
$$

共享参数是 \(W_Q,W_K\)，不是共享当前关系值。当前 R 仍然由输入决定：

$$
R_{p,c}(q,z_p)
=
\frac{q_{p,c}^{\mathsf T}k_{p,c}}{\sqrt{d_k}}.
$$

## 5.2 需要比较的参数方案

| 方案 | QK 参数组织 | 要回答的问题 |
|---|---|---|
| R0 | 全树共享 \(W_Q,W_K\) | 一个关系规则是否足够递归使用 |
| R1 | 按深度共享 | 不同分辨率是否需要不同关系规则 |
| R2 | 共享基底加深度调制 | 少量尺度参数是否足够 |
| R3 | 多头 QK | 不同头能否表示不同关系子空间 |
| R4 | 每节点独立 | 高容量上界，不作为目标架构 |

## 5.3 多头并不改变 R 的定义

第 \(m\) 个头计算：

$$
R_{p,c}^{(m)}
=
\frac{
(W_Q^{(m)}q)^{\mathsf T}
(W_K^{(m)}k_{p,c})
}{\sqrt{d_k}}.
$$

多头只是同时学习多个 QK 关系子空间。每个头的 R 仍然是 QK。

## 本章结论

TreeHeap 需要搜索的是 QK 规则怎样跨节点、深度和关系头共享，而不是给 R 追加一个未定义的状态
转换职责。

# 第六章：怎样验证 R

## 6.1 必须固定 Value/READ

若同时改变 QK、Value、FOLD 和 Decoder，即使 NLL 改善，也无法知道收益是否来自 R。

第一轮实验应固定语料、tokenizer、seed、数据顺序、FOLD、Value/READ、Decoder 初值和训练预算，
只改变 QK 关系方案。

## 6.2 四个关系门禁

### 输入依赖

不同 Query 应产生不同关系场：

$$
D_{JS}
\left(
P(E\mid q_1),P(E\mid q_2)
\right)>0.
$$

### 路径因果

交换 Key、左右分支或深度后，路由与输出应发生可测变化。

### 跨层稳定

随着深度增加，不能快速变成单一路径坍缩或接近均匀随机。

### 任务相关

正确 QK 的 NLL、检索率或生成质量应优于 uniform、random 和 shuffled-Key 对照。

## 6.3 干预矩阵

| 干预 | 解释 |
|---|---|
| uniform R | 完全取消关系选择 |
| random R | 检查树路径本身是否碰巧有效 |
| Query shuffle | 检查 R 是否依赖当前请求 |
| Key shuffle | 检查目录是否保存了区域区别 |
| left/right swap | 检查方向是否有意义 |
| depth swap | 检查尺度是否有意义 |
| one-head zeroing | 检查不同关系头的贡献 |

## 6.4 报告指标

仅看最终 NLL 不够。至少报告：

- edge entropy；
- path entropy；
- top-k path recall；
- Query/Key shuffle damage；
- 各深度的关系分布；
- 实际访问节点数；
- Key 目录字节数；
- NLL、BLEU、重复率与非空率。

质量指标允许非单调。实验不应因为一次 wake 变差就中止，只在 OOM、NaN/Inf、实现合同或证据
损坏时停止。

## 本章结论

SPR-096 的直接实验对象应是 QK 关系场，而不是重新训练一个含义不清的“R 状态变换器”。

# 第七章：现有证据支持到哪里

## 7.1 已有结构干预证据

历史 TreeHeap 实验显示，地址、深度和细节通道会影响输出：

- root-only 地址配对破坏后，NLL 增加 2.6252；
- STONE-1 地址交换后，NLL 增加 1.3545；
- 固定代数 codec 替换后，NLL 增加 1.0984；
- C09 detail shuffle 后，NLL 至少增加 0.5634。

这些结果说明树结构进入了计算链，但没有直接证明树上 QK 已形成有效关系场。

## 7.2 Bilinear FOLD smoke 的边界

2026-10-16 的真实语料 smoke 比较了三种 FOLD：

| FOLD | Test NLL | BLEU | source shuffle damage | pair break mean |
|---|---:|---:|---:|---:|
| lifting | 7.56635 | 0.3557 | +0.15218 | +0.02841 |
| MLP | 7.52975 | 0.2231 | +0.19812 | +0.07180 |
| bilinear | **7.52747** | 0.2134 | **+0.28515** | **+0.11255** |

清零 bilinear 分支后，Test NLL 增加 0.07034。这说明 bilinear 分支被模型使用。

但该分支位于 FOLD smoke，不等于本文定义的 parent-child QK。它只能作为“显式二元关系计算可以
进入因果链”的参考证据，不能作为树上 R 已成立的证据。

{{< evidence grade="E1" source="SameTime ARA s3-generation/corpus_fold_relation_smoke, R2 balanced32, seed 20261016" >}}
真实语料 smoke 支持 bilinear 分支进入因果计算链；不支持 TreeHeap 的 parent-child QK 关系场
已经形成，也不支持稀疏树查询已经优于全连接 Attention。
{{< /evidence >}}

## 7.3 094、095、096 的关系

~~~text
SPR-094：多尺度概率空间怎样形成
SPR-095：输入证据怎样改变候选后验
SPR-096：QK 怎样在树上计算关系并选择路径
~~~

096 不再把 R 写成另一个编解码器。它只研究关系计算与路由。

# 当前结论

SPR-096 现在固定以下边界：

$$
\boxed{R=QK}
$$

$$
R_{p,c}
=
\frac{q_p^{\mathsf T}k_c}{\sqrt{d_k}}.
$$

$$
P(c\mid p,q)
=
\operatorname{softmax}_{c\in\{l,r\}}R_{p,c}.
$$

$$
h_{read}
=
\operatorname{READ}
\left(P(c\mid p,q),V_c\right).
$$

三条式子分别对应：计算关系、得到路由概率、读取内容。

下一轮实验要回答：

1. 树上 QK 能否从真实语料学到输入相关的关系场？
2. 局部 QK 概率能否组成稳定的多层路径后验？
3. 紧凑 child Key 目录能否减少访问量，同时维持任务质量？
4. 在同参数、同数据和同训练预算下，它能否优于 uniform、random 与 shuffled-Key 对照？

这些问题通过之前，TreeHeap 只有树结构和关系假设，还没有得到有效树上 QK 协议的正式证据。
