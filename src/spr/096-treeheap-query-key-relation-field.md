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
R_{p,c}(q,z_p) =
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
R_{ij} =
\frac{q_i^{\mathsf T}k_j}{\sqrt{d_k}}.
$$

把所有 \(R_{ij}\) 排在一起，就得到关系矩阵：

$$
R =
\frac{QK^{\mathsf T}}{\sqrt{d_k}}.
$$

因此，R 不是另一个新模块。R 就是 QK 产生的关系。

## 1.2 TreeHeap 中的 QK

TreeHeap 不必让一个 Query 同时比较所有 token。它可以在当前 parent 只比较两个候选 child：

$$
R_{p,l} =
\frac{q_p^{\mathsf T}k_l}{\sqrt{d_k}},
\qquad
R_{p,r} =
\frac{q_p^{\mathsf T}k_r}{\sqrt{d_k}}.
$$

然后计算左右路由概率：

$$
\alpha_{p,l},\alpha_{p,r} =
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
P(c\mid p,q) =
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
o_p =
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
\operatorname{logits} =
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
q_d =
W_Q
\left[
h_q\,\Vert\,h_{p_d}\,\Vert\,z_d
\right].
$$

对候选 child \(c\in\{l,r\}\)，先把该边追加到路径前缀：

$$
z_{d\rightarrow c} =
E_{path}(d+1,2a_d+b_c),
$$

再构造候选 Key：

$$
k_{d,c} =
W_K
\left[
g_{p_d,c}\,\Vert\,e_c\,\Vert\,z_{d\rightarrow c}
\right].
$$

于是当前边的关系仍然是 QK：

$$
R_{p_d,c} =
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
P(p_{d+1}\mid p_d,q_d) =
\operatorname{softmax}
\left(R_{p_d,l},R_{p_d,r}\right)_{p_{d+1}}.
$$

整条路径的概率为：

$$
P(\pi\mid q) =
\prod_{d=0}^{D-1}
P(p_{d+1}\mid p_d,q_d).
$$

在 log 空间中：

$$
\log P(\pi\mid q) =
\sum_{d=0}^{D-1}
\log P(p_{d+1}\mid p_d,q_d).
$$

因此，路径不是多个隐藏状态变换的复合，而是多次局部 QK 关系判断形成的条件概率链。

## 3.3 关系场是什么

对一棵树的所有边计算 R：

$$
\mathcal R(q) =
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
R_{p,c} =
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
B_p =
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
R_{p,c}(q,z_p) =
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
R_{p,c}^{(m)} =
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

## 7.4 路径 QK 的真实语料机制实验

2026-10-17，我们按照第六章的控制要求实现了第一轮真实语料实验。实验固定 WMT
中英语料切片、tokenizer、seed、FOLD、Value/READ、Decoder、优化器和训练轮数，只改变
关系路由方式：

| 实验臂 | 关系路由 |
|---|---|
| uniform | 对所有有效 child 使用均匀概率 |
| qk_no_path | 只用 Query 与 child Key 计算 R |
| qk_fixed_path | 在 QK 中加入固定 heap 路径编码 |
| qk_learned_path | 在 QK 中加入从零开始学习的路径编码 |

在 6,000 条训练语料、1,000 条验证语料和 1,000 条测试语料上，结果为：

| 实验臂 | Test NLL | BLEU-4 | 重复 token 比例 | 有效 leaf 数 |
|---|---:|---:|---:|---:|
| uniform | 7.465374 | 0.9202 | 0.7616 | 21.57 |
| qk_no_path | 7.484448 | 1.1686 | 0.6903 | 10.74 |
| qk_fixed_path | 7.473946 | 0.7649 | 0.6724 | 11.91 |
| qk_learned_path | 7.468156 | 1.1111 | 0.6358 | 11.68 |

原始质量排序还不能说明 QK 优于均匀路由：这一档训练中，uniform 的 Test NLL 仍然最低。
但干预实验说明 QK 和路径并不是装饰参数。

对 `qk_no_path`：

- 打乱 Query 后，NLL 增加 0.010207；
- 打乱 Key 后，NLL 增加 0.213982；
- 交换左右关系分数后，NLL 增加 0.909093。

对 `qk_learned_path`：

- 清零路径编码后，NLL 增加 0.014340，路由 JSD 为 0.016110；
- 打乱同层路径编码后，NLL 增加 0.051478，路由 JSD 为 0.046671。

所以目前可以说：树上 QK 能在真实语料上接受梯度，形成非均匀路径后验，并且学到会被模型
实际使用的路径编码。还不能说：它已经比均匀 READ 产生更好的语言模型。

{{< evidence grade="E1" source="SameTime ARA S3-TREE-QK-PATH-C01, WMT 6K/1K/1K, seed 20261017" >}}
真实语料机制实验支持 QK 与路径编码进入因果计算链；Test NLL 尚不支持路径 QK 优于均匀
路由，生成质量也不足以形成翻译能力结论。
{{< /evidence >}}

# 第八章：实验代码怎样实现

这一章不再只讲公式，而是把公式落到实际训练器的数据流中。

## 8.1 两个入口文件

机制档与全量档分开实现：

~~~text
ara/s3-generation/src/s3_tree_qk_path_encoding_smoke.py
ara/s3-generation/src/s3_tree_qk_path_full_corpus.py
~~~

第一个文件负责四臂机制实验和完整干预矩阵。第二个文件复用相同模型，把训练改成可恢复的
全量流式扫描。模型定义不因数据规模改变。

## 8.2 FOLD 如何建立树

输入 token 先变成 leaf hidden state。相邻两个 child 通过共享 FOLD 合成 parent：

$$
h_p=\operatorname{LayerNorm}
\left(
\operatorname{MLP}[h_l\Vert h_r]
\right).
$$

若一侧是 padding，parent 直接继承有效 child。32 个 leaf 依次生成 16、8、4、2、1 个节点，
并保留全部层级：

~~~text
levels = [root, depth-1, ..., leaf]
~~~

保留这些层级不是为了让 R 携带内容，而是为了让每一步 QK 都有对应的 parent 和候选 child。

## 8.3 QK 如何沿树递归

Decoder 在第 \(t\) 个生成位置持有状态 \(s_t\)。当前层的 Query 为：

$$
q_{t,d}=
W_{Q,s}s_t+W_{Q,p}h_{p_d}+W_{Q,z}z_d.
$$

左右 child 的 Key 为：

$$
k_{d,c}=W_{K,h}h_{d,c}+W_{K,z}z_{d\rightarrow c}.
$$

代码对左右 child 计算缩放点积：

$$
R_{t,d,c}=\frac{q_{t,d}^{\mathsf T}k_{d,c}}{\sqrt{d_k}},
$$

再在当前 parent 的两个 child 之间做局部 softmax。设 parent 概率为
\(P_t(p_d)\)，child 概率就是：

$$
P_t(c)=P_t(p_d)P_t(c\mid p_d,q_{t,d}).
$$

因此，程序不是在最后一次性对 32 个 leaf 做 flat attention，而是逐层乘起局部条件概率。
所有 leaf 概率之和在每层之后重新归一化为 1。

## 8.4 READ 与 R 在代码中仍然分开

递归 QK 最终得到 leaf 概率 \(P_t(i)\)。READ 才对 leaf Value 求加权和：

$$
c_t=\sum_{i=1}^{32}P_t(i)W_Vh_i.
$$

然后 GRU Decoder 使用前一个目标 token 和 \(c_t\) 更新状态：

$$
s_{t+1}=\operatorname{GRU}
\left([E(y_t)\Vert c_t],s_t\right),
$$

最后生成词表 logits：

$$
\ell_{t+1}=W_O[s_{t+1}\Vert c_t]+b_O.
$$

所以代码中的计算边界是：

~~~text
TreeEncoder/FOLD -> levels
Decoder state + levels + path -> QK/R -> leaf probability
leaf probability + Value -> READ context
READ context + decoder state -> token logits
~~~

## 8.5 为什么全量实验只保留三臂

6K 实验已经表明，固定路径的路径干预响应弱于可学习路径。全量实验因此保留：

1. `uniform`：判断复杂关系路由是否真的必要；
2. `qk_no_path`：判断内容 QK 本身是否有效；
3. `qk_learned_path`：判断路径信息是否在内容 QK 之上增加收益。

三个模型在同一个进程中初始化。除 learned path table 外，它们的共享参数初始 SHA-256 必须
一致；`qk_no_path` 与零初始化的 `qk_learned_path` 在 step 0 的 NLL 必须完全相同。

训练时，程序只顺序读取一次语料。每个 batch 被同一套 tokenizer 和 collate 处理一次，再依次
送给三个模型更新：

~~~python
for batch in nioclean_stream:
    source, length, target = collate(batch)
    for arm in (uniform, qk_no_path, qk_learned_path):
        logits = arm.teacher(source, length, target)
        loss = cross_entropy(logits, target)
        loss.backward()
        optimizer.step()
~~~

这里的三个模型不是共享训练参数，而是共享数据、顺序和训练预算。这样才能把结果差异归因到
关系路由方式。

## 8.6 全量语料合同

全量档使用已经登记的不可变发布集：

~~~text
NioClean-ZHEN-S098-7M-v2
rows:   7,304,358
bytes:  1,535,169,936
sha256: 299134867398720cc6d407eadd6de4fb237812319d113fbe12071758e79d92c8
~~~

训练方向固定为 English 到 Chinese。source 最多保留 31 个内容 piece，再加 EOS 放入 32-leaf
heap；target 最多保留 63 个内容 piece，再加 EOS。这里是容量合同，不把被截断部分伪装成完整
句子。

评测集复用 6K 实验的确定性 WMT 选择过程，其 8,000 行总哈希必须仍为：

~~~text
5271a5fb90633eedff5b8746147c38c768c0f2bd9a0480ca94c3f4ac36c3a3e9
~~~

第 6,001 至 7,000 行固定为 valid，第 7,001 至 8,000 行固定为 test。全部 8,000 个编码后的
pair 都进入排除集合；全量训练流遇到精确相同 pair 时跳过，避免直接把盲测样本写回训练集。

## 8.7 学习率与断点恢复

全量单遍约 11.4 万个 batch。学习率先在 1,000 step 内线性升到 \(3\times10^{-4}\)，再按
cosine 衰减到 \(3\times10^{-5}\)。该调度只控制优化稳定性，不作为 TreeHeap 理论结论。

每 5,000 step 写一次 wake 和原子 checkpoint，checkpoint 保存：

- 三个模型的 state dict；
- 三个 AdamW optimizer state；
- 文件行 cursor 与 byte offset；
- 已处理 example/token 数；
- 数据、tokenizer、评测集和初始状态合同。

若 io 重启，程序从最后一个 byte offset 继续。恢复前必须重新核对数据与评测哈希，避免把另一份
语料接到旧 optimizer 上。

## 8.8 代码要回答什么

全量任务不以“训练更久必然更好”为前提。它要观察五件事：

1. content QK 能否在完整语料暴露后超过 uniform；
2. learned path 能否超过 content-only QK；
3. Query、Key 和 path 干预是否仍然造成独立损伤；
4. 有效 leaf 数是否保持分布式选择，而不是坍缩为 1；
5. 重复率下降时，NLL 与 BLEU 是否同步改善。

质量曲线允许非单调，不能用一次 wake 恶化提前停止。只有 OOM、CUDA/Xid、NaN/Inf、hash
不符、checkpoint 损坏或 cursor 不前进才停止任务。

## 8.9 公式怎样对应源码和证据

下面这张表用于代码 review。它不是模块命名说明，而是理论量到可执行对象的逐项对应：

| 理论对象 | 源码位置 | 可审计输出 |
|---|---|---|
| leaf 到 root 的 FOLD 层级 | `TreeEncoder.forward()` | 每层节点数量、mask 和模型参数哈希 |
| 固定或可学习路径编码 \(z_d\) | `TreeQKDecoder.path_codes()` | `path_zero`、`path_shuffle` 干预损伤 |
| 局部关系分数 \(R_{t,d,c}\) | `TreeQKDecoder.route()` | 各深度熵、leaf 后验和路由 JSD |
| leaf READ \(c_t\) | `TreeQKDecoder.route()` 末段 | `key_shuffle`、`left_right_swap` 后的 NLL 变化 |
| 自回归状态与词表 logits | `TreeQKDecoder.step()` | Test NLL、PPL、BLEU、重复率和生成样例 |
| 固定评测集与训练排除集 | `build_evaluation()` | 8,000 行选择哈希及 valid/test 行数 |
| 全量流式读取 | `iter_full_batches()` | 行 cursor、byte offset、截断数和排除数 |
| 同批三臂训练 | `main()` 的 arm 循环 | 同数据顺序、同 step、同学习率的 wake 曲线 |
| 原子恢复 | `save_checkpoint()` | 模型、optimizer、cursor、offset 与合同哈希 |

机制档最终写出 `summary.json`、`examples.json` 和 `trace.jsonl`。全量档增加
`contract.json`、`wakes.jsonl`、`wake_latest.json` 与可恢复 checkpoint。可携带 evidence 的
`SHA256SUMS` 不包含大型 checkpoint；checkpoint 保留在训练主机，只用于断点恢复和 reload
审计。这一分离避免把“文件太大没有拉回”误写成“模型不可重载”。

96 维、32-leaf、64 batch 的代表性合同 smoke 已完成 4,096 行扫描：cursor 到达 4,096，
无无效行、NaN、OOM 或 CUDA 错误，且三臂均完成最终评测。这个结果只确认全量代码路径可运行，
不用于判断关系路由质量；4,096 行不足以训练出可解释的 QK 差异。

当前实现仍会计算所有层的全部有效节点，再形成完整 leaf 后验。它验证的是“树上逐边 QK 能否
学到有效关系”，不是稀疏执行器，也没有证明访问量、显存或功耗收益。只有关系门禁通过后，才应
把同一组 QK 参数接到 top-k 或硬路由执行器，并把 child-Key 目录、实际访问节点数和峰值显存纳入
新的配对实验。

# 当前结论

SPR-096 现在固定以下边界：

$$
\boxed{R=QK}
$$

$$
R_{p,c} =
\frac{q_p^{\mathsf T}k_c}{\sqrt{d_k}}.
$$

$$
P(c\mid p,q) =
\operatorname{softmax}_{c\in\{l,r\}}R_{p,c}.
$$

$$
h_{read} =
\operatorname{READ}
\left(P(c\mid p,q),V_c\right).
$$

三条式子分别对应：计算关系、得到路由概率、读取内容。

6K 机制实验已经回答：树上 QK 和路径编码可以被训练，也会因干预而改变关系场与预测结果。
但它尚未回答质量优势。正在执行的 NioClean 全量单遍实验继续回答：

1. 树上 QK 能否从真实语料学到输入相关的关系场？
2. 局部 QK 概率能否组成稳定的多层路径后验？
3. learned path 是否在 content-only QK 之上增加任务收益，而不只是增加干预响应？
4. 在同参数、同数据和同训练预算下，它能否优于 uniform，并对 shuffled-Query、Key 与 path
   保持可测的因果响应？

因此，TreeHeap 当前已经有“关系机制存在”的真实语料证据，但还没有“关系协议有效优于均匀
路由”的证据，也没有稀疏执行收益证据。机制成立、架构胜出与工程节能是三个不同层级的 Claim，
不能合并书写。
