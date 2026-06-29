---
title: "[WMT-006] 可微 BLEU 的算法代价——从黑板公式到 GPU 现实"
date: 2026-05-03
author: nio (Houming818) & opencode (First Mate)
keywords: SameTime, WMT, BLEU, SoftBLEU, CrossEntropy, Algorithm Complexity
description: SoftBLEU 理论是对的——但在 GPU 上跑 Python 循环不属于这份正确。
tags: [WMT, NMT, SameTime, BLEU, Gradient, SoftBLEU]
---

# 可微 BLEU 的算法代价

> 黑板上的公式是对的。Python 循环是错的。

## 问题的起点

[上一篇](/wmt/005-wmt-gradient-theory.html) 提出了 SoftBLEU——给 BLEU 套一层 softmax，让翻译质量的评价直接参与梯度计算。

写完公式，写完伪代码，写完 `base/soft_bleu.py`。

然后跑了两小时，0 个 epoch 完成。

## 不是你代码写得丑——是 Python 循环不该碰 loss 函数

CrossEntropy 的计算复杂度是：

$$\text{CE} = O(B \times T \times V)$$

一行 `F.cross_entropy(logits, targets)`。PyTorch 底层是 CUDA kernel——所有操作在 GPU 上并行，一步完成。每 step 约 0.5 毫秒。

SoftBLEU 的 Python 实现：

```python
def soft_bleu(logits, ref_ids, vocab, max_n=4):
    B, T, V = logits.shape
    probs = F.softmax(logits, dim=-1)

    for b in range(B):                    # Python 循环 ← 64 次
        ref_set = set()                   # Python 数据结构
        for r in ref_ids[b]:              # Python 循环 ← ~50 次
            ref_set.add(r.item())         # tensor→Python 转换

        for t in range(T):                # Python 循环 ← ~50 次
            prob_t = probs[b, t, :]       # 切片
            matched[b] += prob_t[list(ref_set)].sum()  # Python list→tensor
```

四层嵌套 Python 循环。每一个 `probs[b, t, :]` 都在触发 tensor→Python→tensor 的往返——这种往返在 GPU 和 CPU 之间产生了几百次数据传输。

每 step 约 500 毫秒。同等条件下 CE 只需要 0.5 毫秒。

**差距不是 10 倍或 100 倍——是 1000 倍。**

## CE 为什么那么快

CE 从 logits 到 loss 走的全是 GPU 原生操作：

```
logits (B,T,V) → reshape → GPU 矩阵索引 → CrossEntropyLoss kernel → 标量
     ↑                                                              ↑
    全是浮点运算，没有 Python 插足                                  梯度一步到位
```

## SoftBLEU 为什么那么慢

每行 Python 代码都在打断 GPU 流水线：

```
GPU:  [softmax 算完] → wait...
CPU:  [for b in B] → [for t in T] → [构建 ref_set] → [tensor 切片]
         ↑
    GPU 在等 CPU 把数据从显存拉回来
    每一毫秒的等待 = 几百个 CUDA core 空转
```

这不是 "Python 慢"。这是一个结构性错误：**把 GPU 当成 CPU 在用**。Python 循环里切片 tensor，等价于把 CUDA 的并行管线切成一段一段的串行任务——每个 `prob_t[list(ref_set)].sum()` 都在 GPU 上起一个全新的 kernel launch，而 launch 的时间开销本身就大于计算本身。

## 结论不在于"不用 SoftBLEU"——在于"正确实现"

SoftBLEU 的理论是对的：给 BLEU 套 softmax，可微，能参与梯度。错的不是理论——是把一个应该在 CUDA 内核里完成的计算写成了四层 Python 循环。

解决方案不是放弃 SoftBLEU。是**用向量化操作重写**——去掉 Python 循环，用 `torch.scatter`、`torch.where`、`torch.einsum` 这些可以在 GPU 上一步完成的算子。

下一篇：SoftBLEU 的向量化实现——把 1000 倍的差距压回个位数。

---

## SoftBLEU 公式剖析——为什么 2/3/4-gram 是假的

E6 实验使用的 SoftBLEU（`bdf4a63` 版本）的实际公式：

**1-gram（真实的）**：

$$\text{prec}_1 = \frac{1}{B} \sum_b \frac{\sum_t \sum_{r \in \text{ref}} P(hyp_t = r)}{\max(1, T)}$$

对每个位置 t，求和参考 token 的 softmax 概率 → 除以句子长度 → 得到软 1-gram 精度。这个是真的，可导的。

**2/3/4-gram（假的）**：

$$\text{prec}_n = \text{prec}_1 \times (1 - 0.5^{n-1}) \quad n \in \{2,3,4\}$$

只是 1-gram 精度乘以一个衰减系数。**没有真正的 bigram/trigram/4-gram 匹配。** 等于把 DC 分量复制三份乘以衰减——高频信息全丢了。

**BLEU 合成**：

$$\text{SoftBLEU} = (\text{prec}_1 \times \text{prec}_2 \times \text{prec}_3 \times \text{prec}_4)^{1/4}$$

**损失函数（E6 混合模式）**：

$$L = 0.5 \times \text{CE} + 0.5 \times (1 - \text{SoftBLEU})$$

CE 和 1-gram 等价 → 两者本质上在做同一件事 → E6 只是在 CE 上套了个衰减壳。**这就是 SoftBLEU 在 RNN 上只加了 +0.15、在 Attention 上只加了 -0.26 的根本原因。**

要真正发挥 SoftBLEU 的作用，必须把真实的 2/3/4-gram 软匹配算出来——相邻位置的概率乘积，或者用卷积在 GPU 上一步完成。

---

## 时间线

| 日期 | 事件 | 关键发现 |
|---|---|---|
| 2026-04-26 | Phase 0 底座骨架完成 | DummyModel BLEU=91/0/0（相位差 0/1/2） |
| 2026-04-27 | Phase 1.0 RNN 代码拆分 | 拆为 1.0（vanilla RNN）+ 1.1（LSTM） |
| 2026-05-01 | 7 组 hidden_size 对照实验 | BLEU 天花板 ≈ 3.0，倒 U 峰值 H=512 |
| 2026-05-01 | 解耦合 embed 实验 | 最佳 E=128，hash 碰撞密度 ~580 词/维 |
| 2026-05-01 | K_lang 碰撞密度模型提出 | BLEU ∝ |N_data/N_params − K_lang|⁻¹, K≈0.003 |
| 2026-05-01 | 预测 3 证伪：epoch 深度 | H=512/1024 ep20：epoch 不改变 K_lang |
| 2026-05-02 | sin RNN 实验 | BLEU=0.76：cos 梯度方向翻转自毁 |
| 2026-05-02 | 梯度函数决定学习规律 | 独立文章发表 |
| 2026-05-02 | GPU 稳定性诊断 | ROG 3090 锁 1800MHz 稳定，390W 不掉卡 |
| 2026-05-03 | SoftBLEU Python 循环版 | 2 小时 0 epoch——1000 倍差距 |
| 2026-05-03 | **SoftBLEU 向量化版** | **BLEU=3.21，突破 CE 天花板 3.06** |

## 前方的路

**SoftBLEU 已验证可行。现在有三条路：**

| 路线 | 实验 | 预期 |
|---|---|---|
| **A. 深挖 SoftBLEU** | 调 λ（0.3/0.5/0.7），多组 seed，H=1024 + SoftBLEU | 找最佳混合比，大模型上验证 |
| **B. 换 hash 架构** | Phase 2 Bahdanau Attention | Attention 替代 RNN 时序压缩，预期 BLEU 10-15 |
| **C. 跳级** | Phase 6 Transformer | 并行 hash，多头碰撞，预期 BLEU 25-35 |

路线 B 最合理——Attention 是自然演进。路线 C 最激进——跳过中间 Phase 直接验证终极架构。

**建议先跑 B（Attention + SoftBLEU），验证"更好的 hash 策略 + BLEU 感知梯度"的联合效果。**

---

*May the Code be with us.*

---

> **License: GPLv3**
