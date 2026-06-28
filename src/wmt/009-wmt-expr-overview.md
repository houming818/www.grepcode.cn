---
title: "[WMT-009] 实验总览——从 RNN 到 Transformer 的技术组合与天花板"
date: 2026-05-04
author: nio (Houming818) & opencode (First Mate)
keywords: SameTime, WMT, Experiment Report, RNN, Attention, SoftBLEU
description: Phase 1 RNN 和 Phase 2 Attention 的全部实验编号与最佳 BLEU 总结。
tags: [WMT, NMT, SameTime, Experiment Report]
---

# 实验总览

> **全局实验 ID**：全部实验跨系列统一编号 E-001 ~ E-030。E 系列=R01-08, A 系列=E09-23, TI 系列=E24-30。

## Phase 1：RNN（纯 tanh）

| 编号 | 实验 | 损失 | 关键参数 | Best BLEU | E-# | 发现 |
|---|---|---|---|---|---|---|---|
| E1 | hidden 扫描 | CE | H=E∈{16~1024} | 3.02 | E-001 | 倒 U，天花板 3.0 |
| E2 | embed 解耦 | CE | H=512, vary E | 3.06 | hash 碰撞最优 ~580 词/维 |
| E3 | epoch 深度 | CE | H=512/1024, 20ep | 3.02 | epoch 不改变 K_lang |
| E4 | 数据翻倍 | CE | H=1024, ×2 data | 2.50 | epoch 0 缓解，过拟合照旧 |
| E5 | sin 激活 | CE | H=512, E=128 | **0.76** | 梯度方向自毁 |
| E6 | SoftBLEU 混合 | CE+SB λ=0.5 | H=512, E=128 | **3.21** | 突破纯 CE 天花板 |
| E7 | SoftBLEU 纯 | 纯 SB | H=512, E=128 | 🔄 | CE=1-gram 不插一手 |
| E8 | BLEU Function | 0/1 STE | H=512, E=128 | ❌ | backward 循环太慢 |

## Phase 2：Attention（LSTM + Bahdanau）

| 编号 | 实验 | 损失 | 关键参数 | Best BLEU | 发现 |
|---|---|---|---|---|---|
| A1 | CE 基线 | CE | H=256, E=256 | 3.57 | BLEU 未衰退（小模型） |
| A2 | CE 大模型 | CE | H=512, E=256 | 3.76 | peak ep2 后衰退 |
| A3 | CE 深 epoch | CE | H=512, E=256, 10ep | 3.76→3.02 | 与 RNN 相同的倒 U |
| A4 | SoftBLEU 混合 | CE+SB | H=512, E=256 | 3.50 | 反降——梯度拉锯 |
| A5 | SoftBLEU 纯 | 纯 -log SB | H=512, E=256 | 0.00 | soft 匹配与 argmax 鸿沟 |
| A6 | E6 on Attention | CE+SB λ=0.5 | H=512, E=256, 10ep | **3.74** | 振荡不崩，但未破 3.76 |

## 全局结论

1. **换 hash 架构（RNN→Attention）不改变过拟合模式**——loss ↓ 时 BLEU ↓
2. **SoftBLEU 是缺陷补偿器**：RNN 上 +0.15，Attention 上 −0.02。基线越好增益越小
3. **纯 BLEU 梯度永远无法替代 CE**：1-BLEU 梯度太小，-log(BLEU) 梯度够但 soft 匹配和 argmax 之间存在结构性鸿沟（BLEU=0）
4. **E6（CE+SB λ=0.5）在 RNN 上是最优方案**，但在 Attention 上不产生增益

## 全局结论

换 hash 架构（RNN→Attention）不改变过拟合模式。loss 持续下降时 BLEU 仍在衰退——梯度方向问题比架构问题更深。

---

*May the Code be with us.*

---

> **License: GPLv3**
