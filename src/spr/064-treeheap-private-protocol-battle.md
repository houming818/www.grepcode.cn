---
title: "[SPR-064] 私有协议，结果见本事：TreeHeap 下一轮公平实验设计"
date: 2026-07-19
lastmod: 2026-07-19
weight: 64
author: Houming818 & Codex Review
description: "停止替 TreeHeap 的内部状态编故事。本文汇总私有协议与 lifting 抽水机的已有证据，并预注册一场只看任务结果、结构因果性和公平基线的实验。"
tags: [SPR, TreeHeap, ARA, Private Protocol, Encoder, Decoder, Lifting, Multi-Head]
---

# 私有协议，结果见本事：TreeHeap 下一轮公平实验设计

> 本文首先纠正一个刚刚出现的方向错误：我们已经决定让 TreeHeap 的 encoder 和 decoder 自己形成私有协议，就不应该再由研究者规定“root 必须保存主题”“detail 必须保存次要信息”或者“某个 head 必须学习语法”。我们只设计可微、递归、可寻址的通信结构。协议内部写了什么，由最终任务的梯度决定。最后有没有本事，由实验结果决定。

---

## 1. 什么叫私有协议

给定输入字符串 $X$ 和目标字符串 $Y$，encoder 把输入写入一个 TreeHeap 状态：

$$
H=E_\theta(X)
$$

decoder 只能读取这个状态，并生成输出概率：

$$
P(Y\mid X)=D_\phi(H)
$$

训练只使用最终输出的交叉熵：

$$
L(\theta,\phi)
=
-\sum_t \log P_{\theta,\phi}(y_t\mid X,y_{<t})
$$

梯度同时修改 $E_\theta$ 和 $D_\phi$。只要 encoder 写出的状态能被 decoder 正确读取，loss 就会下降。内部编码不需要像自然语言，也不需要让人类看懂。

这就叫私有协议。它像一个人自己的笔迹：我们不规定每一笔必须代表什么，只要求写的人和读的人使用同一套规则。

但是，“私有”不等于“无法验证”。我们仍然可以验证：

1. encoder 和 decoder 是否真的能够联合完成任务；
2. decoder 是否依赖 TreeHeap，而不是绕过它读取原字符串；
3. 地址、父子关系、递归深度和 head 被破坏以后，输出是否退化；
4. 相同数据、参数量和训练预算下，它是否优于更简单的结构。

---

## 2. 抽水机在协议中是什么

最近建立的 lifting 抽水机，不是语义分类器，也不是“信息价值判断器”。它只是 encoder 和 decoder 共同遵守的递归通信介质。

一次局部 FOLD 接收左右两个状态 $a,r$，产生一个继续向上传播的 parent $p$，以及保留在当前地址的 detail $d$：

$$
p=a+U_\theta(r)
$$

$$
d=r-P_\theta(p)
$$

decoder 使用相反方向的运算恢复 children：

$$
r=d+P_\theta(p)
$$

$$
a=p-U_\theta(r)
$$

同一组共享 kernel 在整棵树上递归调用：

```text
tokens
  -> WRITE
  -> FOLD 得到 parent + addressed detail
  -> parent 继续递归 FOLD
  -> 形成完整 H_state
  -> decoder 从 H_state 递归 READ / UNFOLD
  -> 输出 token 概率桶
```

这里的 $p$ 和 $d$ 首先只是两个不同位置的私有通信变量。研究者不能提前宣布：

```text
p = 句子主题
d = 表面细节
```

如果将来实验发现某个深度更适合预测全局输出，那是实验结论；不是算法定义。

---

## 3. 我们已经走到了哪里

这条路线并不是今天才提出。ARA 中已经有三段连续证据。

### 3.1 M0：短算子协议能够学习

在受控数论 TreeHeap 中，结构 encoder 学习一个短算子程序，固定 executor 使用 TreeHeap 原生算子恢复目标。

| 测试 | TreeHeap structural restore | Flat program |
|---|---:|---:|
| IID | 0.9270 | 0.1535 |
| OOD 地址 | 0.8400 | 0.0000 |

这说明“学习协议 + 固定结构执行器”在受控世界中可以成立，但联合外推到未见递归深度仍然失败。

### 3.2 Native codec：raw token 能形成地址敏感私有协议

模型从随机参数开始，只用 echo 交叉熵联合训练：

```text
WRITE -> FOLD -> DETAIL -> UNFOLD -> READ
```

| 版本 | 正常 token top-1 | detail 地址错位后 |
|---|---:|---:|
| continuous v1 | 0.9955 | 0.0024 |
| continuous v2 | 0.9915 | 0.0014 |

所有五个算子都收到非零梯度。地址错位几乎摧毁输出，因此模型确实形成了依赖 TreeHeap 地址的私有协议。

但 root 清零后准确率几乎不变。这个协议主要走本地 detail 通道，并没有形成完整的 root-plus-detail 协议。Echo 允许这种答案，所以不能责怪模型“没有学会主题”。

### 3.3 Lifting pump：协议获得了闭合递归载体

抽水机实验已经证明：

- depth-6 闭包最大误差约为 $3.70\times10^{-6}$；
- state MSE 为 $3.14\times10^{-14}$；
- 确定性 token/block echo 都是 1.0；
- WMT checkpoint 从 depth cap 0 开放到 6 时，NLL 从 13.8100 降到 4.6335；
- root、detail 和多个递归 pairing 在 WMT 中具有可测的因果作用。

这证明同一个 decoder 可以沿同一棵 TreeHeap 递归增加可用状态。它没有证明 root 是人类可读摘要，也没有证明 TreeHeap 已经优于 flat sequence。

在 200K WMT 实验中：

| 模型 | NLL | Token BLEU-4 |
|---|---:|---:|
| TreeHeap learned-update lifting | 4.6335 | 9.909 |
| Flat sequence | 4.5419 | 10.572 |

因此当前体检报告是：

```text
私有协议存在                阳性
协议依赖 TreeHeap 地址      阳性
递归 FOLD/UNFOLD 闭合       阳性
真实 WMT 使用多层状态       阳性
翻译质量超过 flat           阴性
内部语义可以被人类解释      未检测，也不是当前门槛
```

---

## 4. 下一条 Claim

下一轮不再证明“私有协议能不能存在”，而测试它有没有工程竞争力。

建议预注册为：

> **S3-PRIVATE-PROTOCOL-BATTLE-C01**：在不提供语法、深度、route、摘要或 head 语义标签的条件下，多个共享递归 TreeHeap kernel 可以仅通过最终 seq2seq 交叉熵形成 encoder-decoder 私有协议；该协议必须在真实任务中稳定训练，因果依赖 TreeHeap 地址和递归结构，并在相同参数、数据与训练预算下，相对单 head TreeHeap 和 flat baseline 产生可测收益。

这条 Claim 没有规定协议内容。它只规定通信介质、训练信号和判分方法。

---

## 5. 实验模型

使用同一份真实数据、同一 tokenizer、同一训练/验证/测试切分和相同随机数据顺序，训练四组模型。

### A. 单 head TreeHeap

```text
token embedding
-> 一个 WRITE/FOLD/DETAIL kernel
-> 一个 H_state
-> 递归 READ/UNFOLD
-> autoregressive decoder
```

这是当前 lifting pump 的直接基线。

### B. 多 head TreeHeap

每个 head 有独立参数，并在相同 TreeHeap 地址上建立自己的状态：

$$
H^{(m)}=E_{\theta_m}(X),\qquad m=1,\ldots,M
$$

decoder 联合读取所有 head：

$$
P(Y\mid X)=D_\phi\left(H^{(1)},\ldots,H^{(M)}\right)
$$

所有 head 共用一个最终 seq2seq loss。没有“语法 head loss”“主题 head loss”或者人工分工。

先测试 $M\in\{1,2,4,8\}$。如果增加 head 只增加参数，不改善验证集，就不能宣称多头有效。

### C. Flat sequence baseline

保留 token 顺序和相同 decoder，但 encoder 不使用父子地址、递归 FOLD 或 addressed detail。参数量和训练 FLOPs应尽量与 TreeHeap 匹配。

### D. 小型 Transformer baseline

使用相同 tokenizer、训练数据和参数预算。它不是敌人，而是成熟的序列私有协议基线。

---

## 6. 最直接的私有协议检查

训练三个随机种子的 encoder-decoder 配对：

```text
(E1, D1)
(E2, D2)
(E3, D3)
```

首先测试原配：

```text
E1 -> D1
E2 -> D2
E3 -> D3
```

然后交换 decoder：

```text
E1 -> D2
E1 -> D3
E2 -> D1
...
```

如果原配工作、交换后明显退化，说明 encoder 与 decoder 形成了互相兼容但不必相同的内部协议。这个实验不能证明协议具有人类语义，却能比观看某个向量的 cosine 更直接地测量“双方是否共同写成了一套编码”。

如果交叉配对也能工作，也不是坏事。它说明架构和数据诱导出了跨 seed 相近的协议。此时再通过权重匹配或小型 adapter 判断它是公共坐标，还是可以被简单变换对齐。

---

## 7. 如何确认它真的用了 TreeHeap

仅有低 loss 不够，因为模型可能退化成普通数组协议。测试时保持参数不变，分别进行干预：

| 干预 | 测试问题 |
|---|---|
| 打乱 left/right 地址 | 协议是否依赖手性与地址 |
| 交换两个 subheap | 协议是否依赖子结构位置 |
| root 清零或换样 | root 是否参与当前任务 |
| 逐层关闭 detail | decoder 是否递归使用不同深度 |
| 单独关闭每个 head | 哪些 head 对最终结果有因果贡献 |
| 全部 head 只留一个 | 多头收益是否来自组合，而非单个幸运 head |
| 禁止 decoder 读取原始 token | 排除 string 旁路 |

记正常 loss 为 $L_0$，干预后的 loss 为 $L_I$：

$$
\Delta L_I=L_I-L_0
$$

只有当结构干预稳定产生正的 $\Delta L_I$，才能说对应结构参与了协议。

但我们仍然不能把它翻译成“这个 head 学会了宾语”。因果参与和人类语义解释是两件事。

---

## 8. 什么叫多 head 真正有效

多 head 不能只比较最终最好的一个数字。至少要同时报告：

1. **任务质量**：NLL、token accuracy、BLEU 或目标任务指标；
2. **训练效率**：达到同一验证 NLL 需要多少 token、step 和 GPU 时间；
3. **参数效率**：相同参数量下谁更好；
4. **稳定性**：至少三个 seed 的均值、标准差和失败尾部；
5. **head 因果性**：逐 head 消融造成多少损失；
6. **组合收益**：完整多头是否优于最佳单 head；
7. **结构收益**：TreeHeap 是否优于 matched flat 和 Transformer。

我们此前讨论过“head 只向前优化”。需要谨慎：非负 gate 或 ReLU 不能自动保证最终 loss 单调下降。第一轮实验不把这个性质写成事实。它只测量多个私有 kernel 是否产生稳定的组合收益。若出现 head 干扰，再单独预注册带 line search、trust region 或阶段式 boosting 的单调更新实验。

---

## 9. 判决表

### 支持

满足以下条件，Claim 才获得支持：

```text
1. 多 head TreeHeap 在多个 seed 上稳定训练；
2. 完整模型优于最佳单 head，而不是只靠一个 head；
3. 地址、subheap、深度干预造成可重复损失；
4. decoder 没有原始 token 或 flat memory 旁路；
5. 在匹配预算下，相对 flat 至少出现一项稳定收益：
   任务质量、收敛速度、参数效率或结构外推。
```

### 部分支持

如果结构干预有效，但任务分数仍低于 flat/Transformer，则结论只能是：

> TreeHeap 私有协议真实存在并使用了结构，但当前实现尚无竞争优势。

### 拒绝或降级

出现以下结果应当降级：

```text
地址打乱几乎不影响输出；
多 head 等于或差于最佳单 head；
收益完全来自参数量增加；
decoder 通过 leaf/string 旁路完成任务；
TreeHeap 在匹配预算下持续落后且没有外推或效率收益。
```

负结果也有价值。它会告诉我们问题究竟在多头组合、训练优化，还是 TreeHeap 归纳偏置本身。

---

## 10. 为什么这次不再走迷宫

这一轮只回答一个问题：

> **已经能够形成的 TreeHeap 私有协议，在真实 seq2seq 任务上到底有没有本事？**

不再同时讨论意识、语法标签、最低熵句子、人类可读 root、世界模型拓扑和有限比特压缩。那些问题可以保留，但不能继续挤进同一个实验。

实验结束后，我们只允许三种结论：

```text
赢：TreeHeap 在公平指标上出现稳定优势，并且结构干预证明优势来自 TreeHeap。

平：TreeHeap 能工作且确实使用结构，但没有超过成熟基线。

输：TreeHeap 的结构没有被使用，或者使用以后仍持续降低任务能力。
```

协议内部可以保持沉默。结果必须公开说话。

