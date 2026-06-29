---
title: "[WATERMELON-001] 西瓜书学习专题——从一条公式开始"
date: 2026-05-07
weight: 1
author: nio (Houming818) & opencode (First Mate)
keywords: Machine Learning, Watermelon Book, Zhou Zhihua, Gradient Descent, GPL
description: 精读周志华《机器学习》，一章一个实验，从数学推导到 GPU 实现。GPLv3 开源。
tags: [Watermelon, Watermelon Book, Gradient, GPL]
---

# 西瓜书学习专题

> 从一条公式出发，推导、实现、验证。不做"实验表明"，做"因为……所以……"。

## 为什么开这个专题

WMT 系列（003-009）跑了 30+ 组实验，从 RNN 到 Transformer，从 sin 到 K_lang。每走一步都在想一个问题：**这个结论是实验巧合，还是数学必然？**

西瓜书（周志华《机器学习》）正好提供了这种"从定理出发"的思维训练。每一章从假设空间、损失函数、优化方法三条线推到底——不依赖实验，依赖推演。

但这个训练不该停在纸面上。每条定理都可以写成代码，跑出实验数据来验证推演是否正确。

每一章三件套：
1. **数学推演**——读出定理为什么成立
2. **代码实现**——用 PyTorch 跑实验复现
3. **心得 + 偏差**——推演 vs 实验的差异，为什么有差异

## 路线图

`[ML-002]` 到 `[ML-015]` 对应西瓜书第 1 章到第 16 章。每篇独立成文，含理论推导的可复现代码。

---

*May the Code be with us.*

---

> **License: GPLv3**  
> 本文《ML》系列采用 GNU 通用公共许可证第三版 (GNU General Public License v3.0) 协议进行开源发布与分发。
