---
title: "[SPR-079·论文特别篇三] TreeHeap 得到了什么证据：三种子 WMT 与双向 Dreams"
date: 2026-08-02
lastmod: 2026-08-02
weight: 79
author: Houming818 & Codex Review
description: "公开 TreeHeap 当前最强正向结果、负向边界和全量训练轨迹：闭包、多分辨率读取、Butterfly 三种子比较，以及不单调的双向 Dreams。"
tags: [SPR, TreeHeap, Paper, Evidence, WMT, NLL, BLEU, Dreams, Ablation]
---

# TreeHeap 得到了什么证据

> **系列定位：TreeHeap 论文特别篇（3/4）。**
>
> 本篇把证据分为代数正确性、机制参与性、架构比较和规模生长观察。不同等级不能互相冒充。

## 系列导航

1. [问题、失败与设计演化](/spr/077-treeheap-paper-origin-and-evolution.html)
2. [数学、参数与数据流](/spr/078-treeheap-paper-math-and-dataflow.html)
3. **本篇：三种子 WMT 与双向 Dreams**
4. [边界、否证条件与复现](/spr/080-treeheap-paper-boundaries-and-reproduction.html)

## 1. 先给证据分级

| 等级 | 回答的问题 | 不能推出什么 |
|---|---|---|
| E1 代数正确性 | 逆运算是否成立 | 不能推出语言能力 |
| E2 机制参与性 | root、detail、通信是否影响任务 | 不能推出架构更优 |
| E3 架构比较 | 匹配合同中哪种配置更好 | 不能推出普遍优势 |
| E4 规模观察 | 行为是否随数据变化 | 样例不能替代标准指标 |

这张表是读懂所有结果的钥匙。

## 2. E1：FOLD 和 Butterfly 是否真的可逆

三颗正式实验种子中：

```text
Butterfly forward/inverse MSE: 约 6.7e-16 .. 7.2e-16
FOLD/UNFOLD closure MSE:      约 6.7e-15 .. 8.2e-15
```

误差接近 FP32 浮点精度。这说明训练没有破坏定义好的逆运算。

它只证明数学闭包，不证明翻译无损，更不证明 root 保存了整句话。

## 3. E2：Decoder 是否使用多个分辨率

在 27K/2K/2K WMT、10 epochs 的 lifting-pump 实验中：

| 读出方式 | 测试 NLL |
|---|---:|
| recursive READ | 5.0903 |
| root-only | 5.4337 |
| full UNFOLD read | 5.1342 |
| flat sequence | 4.8103 |

这里 NLL 越低越好。

recursive READ 优于 root-only，并接近直接读取完整 UNFOLD 状态。source shuffle 和 root shuffle 分别造成约 `+1.4450` 与 `+1.7204` NLL 损伤；所有 detail 深度也表现出可测作用。

因此可以说：

> Decoder 确实使用 root 和多个 detail 层级。

但 flat sequence 仍领先 `0.2800` NLL，所以不能写成“TreeHeap 翻译更好”。

## 4. 可学习 Update 带来了什么

在 200K/5K/5K WMT 实验中：

```text
固定 Update NLL:   4.6743
可学习 Update NLL: 4.6335
提升:              0.0408

token BLEU-4:      9.609 -> 9.909
closure MSE:       2.35e-14
```

预注册要求提升至少 `0.05`，所以强 gate 没有通过。但结果仍支持一个较窄结论：梯度可以改变 detail 向 parent 的上导方式，同时保留 UNFOLD 闭包。

## 5. E3：Butterfly 三种子匹配实验

正式实验保持：

```text
train / valid / test = 200K / 5K / 5K
length = 8..32 pieces
dim / hidden = 256 / 256
epochs = 5
parameters = 34,445,832
seeds = 8104, 8105, 8106
```

只改变通信调度：

- Identity：不执行节点通信；
- Adjacent：每轮重复相邻配对；
- Butterfly：每轮打开不同地址 bit。

### 测试 NLL

| Seed | Identity | Adjacent | Butterfly | Butterfly 相对 Identity | 相对 Adjacent |
|---:|---:|---:|---:|---:|---:|
| 8104 | 4.62285 | 4.62273 | **4.54546** | 0.07738 | 0.07727 |
| 8105 | 4.66175 | 4.67974 | **4.58915** | 0.07260 | 0.09059 |
| 8106 | 4.67127 | 4.65998 | **4.56066** | 0.11061 | 0.09932 |
| Mean | 4.65196 | 4.65415 | **4.56509** | **0.08687** | **0.08906** |

### 项目内 token BLEU-4

| Identity | Adjacent | Butterfly |
|---:|---:|---:|
| 9.9501 | 9.9485 | **10.5462** |

三颗种子都通过预注册门槛。因此，当前最强结论是：

> 在这个 WMT 数据、模型规模和训练合同中，从头训练的 Butterfly 配置稳定优于 Identity 和重复 Adjacent。

这不是“TreeHeap 优于所有序列模型”，也不是“XOR 地址就是语义”。

## 6. 长源结果

在正式实验允许的 25--32-piece 长源子集中，Butterfly 相对 Identity 的 NLL 收益为：

```text
0.07451 / 0.07825 / 0.10424
mean = 0.08567
```

收益没有在该实验的长端消失。但是训练最大长度只有 32，不能把它称为 128 或 256 token 长程证明。

## 7. 为什么运行时 Identity 不是严格拓扑消融

训练完成后，把 Butterfly 改成 Identity，平均 NLL 恶化约 `1.16873`。这个数字很大，却不能直接证明 XOR 拓扑最优。

原因是 Identity 完全绕过了学会的通信变换 $B_\theta$。后续 FOLD 和 Decoder 接收到训练中没见过的坐标。

它能证明：

```text
模型依赖已经学会的通信协议
```

不能单独证明：

```text
损伤全部来自 changing-bit 配对图
```

更严格的实验必须保持 kernel 活跃、调用次数相同，只替换配对图，并使用完全相同的验证句。

## 8. E4：全量双向训练的 NLL 轨迹

全量实验使用 1417 万中英平行句对，最长 253 pieces，单张 RTX 3090 运行 96 小时。

截至 2026-08-02 本文核对时：

| 训练样本 | Mean validation NLL | 状态 |
|---:|---:|---|
| 0 | 10.5612 | 初始快照 |
| 5.99M | 3.5630 | 已归档 |
| 11.98M | 3.4839 | 已归档 |
| 17.93M | 3.4561 | 已归档 |
| 21.93M | 3.4407 | 已归档 |
| 31.88M | **3.4230** | 运行中最好 wake |
| 36.87M | 3.4302 | 最近 wake |

曲线前期快速下降，后期在 `3.42..3.47` 震荡。最新 checkpoint 并不是最好 checkpoint。

这可能来自容量平台、数据 block 分布变化或双向任务干扰，但目前没有控制实验区分。诚实结论只有：训练进入平台震荡，而不是继续单调改善。

## 9. Dreams：同一句话怎样变化

固定输入：

```text
The new company is expected to begin operations in the spring of 2019.
```

初始输出：

```text
意愿 Fe Fe Fe Fe Fe Fe Fe ...
```

约 599 万样本：

```text
预计于2019年年底,开始新年。
```

约 1198 万样本：

```text
新年公司预计于2019年,预计在2019年春天开始运营。
```

约 1793 万样本：

```text
预计于2019年春天开始运营。
```

约 2193 万样本：

```text
新的公司预计将于2019年春春新公司运营。
```

它从单 token 循环，发展为保留“公司、2019、春季、开始运营”的源相关输出。但改善不是单调的：1793 万时比 2193 万时更简洁。

对于“窗户为什么湿”的因果句，模型也学到了雨、风、窗户等相关词，却仍产生明显重复。这说明总体 NLL 下降不会保证每个自由生成样例同步变好。

## 10. Dreams 的正确用途

Dreams 不进入训练，也不参与 loss。它们的用途是暴露：

- 单 token 坍缩；
- 短语循环；
- 实体错误；
- 方向混淆；
- 源条件是否逐渐出现。

六条人工句子不能代表完整测试集。最终质量仍需标准 BLEU、chrF、COMET、重复率、长度分桶和人工盲评。

## 11. 本篇结论

目前可以确认：

1. 数学闭包成立；
2. 多个 TreeHeap 分辨率参与任务；
3. Butterfly 配置在当前合同中获得三种子稳定收益；
4. 双向自由输出从源无关重复发展出部分源相关关系。

目前不能确认：

1. changing-bit 拓扑是全部收益来源；
2. root 是摘要；
3. 地址具有语义；
4. 当前模型达到产品质量；
5. 当前实现节省算力。

> 下一篇：[Claim 边界、否证条件与复现入口](/spr/080-treeheap-paper-boundaries-and-reproduction.html)

---

**License:** GPLv3。
