---
title: "[WATERMELON-002] 从对称开始——回归与分类是同一个问题"
date: 2026-05-08
author: nio (Houming818) & opencode (First Mate)
keywords: Machine Learning, Regression, Classification, Linear Model, Symmetry, GPL
description: 回归和分类在假设空间层面完全对称——同样的线性基底，不同的输出层。从 wx+b 出发，统一广义线性模型框架。
tags: [Watermelon, Regression, Classification, Linear Model, GPL]
---

# 回归与分类是同一个问题

> 同样的 `wx + b`，接恒等映射就是回归，接 sigmoid 就是分类。输入输出维度不同、损失函数不同——但梯度形式完全一致。

## 线性基底：`wx + b`

给定特征向量 $$\mathbf{x} \in \mathbb{R}^d$$，线性模型的核心是：

$$z = \mathbf{w}^\top \mathbf{x} + b$$

参数 $$\mathbf{w}$$ 决定了每个特征的权重方向，$$b$$ 是偏置。这个基底在回归和分类中完全共享——不管最后输出什么，模型的第一层计算是一样的。

## 回归：恒等映射 + MSE

回归任务输出连续实数 $$y \in \mathbb{R}$$。线性回归直接使用 `z` 作为预测值：

$$\hat{y} = z = \mathbf{w}^\top \mathbf{x} + b$$

损失函数采用均方误差（Mean Squared Error, MSE）：

$$\mathcal{L}_{\text{MSE}} = \frac{1}{2}(\hat{y} - y)^2$$

对参数 $$\mathbf{w}$$ 求梯度：

$$\frac{\partial \mathcal{L}}{\partial \mathbf{w}} = (\hat{y} - y) \cdot \mathbf{x}$$

梯度方向 = **预测减真实 × 输入向量**。

## 分类：sigmoid 映射 + CrossEntropy

二分类任务输出离散标签 $$y \in \{0, 1\}$$。线性基底 `z` 经过 sigmoid 函数压缩到 `(0, 1)` 区间：

$$p = \sigma(z) = \frac{1}{1 + e^{-z}}$$

其中 $$p$$ 解释为样本属于正类的概率。损失函数采用交叉熵（CrossEntropy）：

$$\mathcal{L}_{\text{CE}} = -\big[y \log p + (1-y)\log(1-p)\big]$$

对参数 $$\mathbf{w}$$ 求梯度。sigmoid 的导数是 $$p(1-p)$$：

$$\frac{\partial p}{\partial z} = p(1-p)$$

链式法则展开：

$$\frac{\partial \mathcal{L}}{\partial \mathbf{w}} = \frac{\partial \mathcal{L}}{\partial p} \cdot \frac{\partial p}{\partial z} \cdot \frac{\partial z}{\partial \mathbf{w}}$$

$$= \left[-\frac{y}{p} + \frac{1-y}{1-p}\right] \cdot p(1-p) \cdot \mathbf{x}$$

$$= \bigg[-(1-p)y + p(1-y)\bigg] \cdot \mathbf{x}$$

$$= (p - y) \cdot \mathbf{x}$$

## 关键发现：梯度形式统一

| | 回归 (MSE) | 分类 (CE + sigmoid) |
|------|------|------|
| 输出映射 | 恒等: $$\hat{y} = z$$ | sigmoid: $$p = \sigma(z)$$ |
| 损失函数 | $$(\hat{y}-y)^2/2$$ | $$-y\log p - (1-y)\log(1-p)$$ |
| 参数量 | $$d+1$$ | $$d+1$$ |
| **梯度形状** | $$(\hat{y}-y) \cdot \mathbf{x}$$ | **$$(p-y) \cdot \mathbf{x}$$** |
| 梯度含义 | 预测 − 真实 | 预测 − 真实 |

梯度完全一致：**（预测值 − 真实值）× 输入向量**。MSE 的 $$\hat{y} - y​$$ 和 CE+sigmoid 的 $$p - y$$ 是同一个数学结构——sigmoid 的导数 $$p(1-p)$$ 恰好约掉了 CE 分母中的 $$p$$ 和 $$1-p$$。

这不是巧合。这是**广义线性模型（GLM）**框架的必然：
- **系统组件**（线性预测器）：$$\eta = \mathbf{w}^\top \mathbf{x}$$
- **链接函数**：回归用恒等 $$g(\mu) = \mu$$，二分类用 logit $$g(p) = \log\frac{p}{1-p}$$
- **误差分布**：回归假设高斯，分类假设伯努利

不同链接函数 + 不同误差分布 → 不同的损失函数。但梯度形状由 `(预测−真实)×输入` 统一。

## 多分类扩展：softmax

从二分类推广到 $$k$$ 类分类，输出从单值 $$p$$ 变成向量 $$\mathbf{p} \in \mathbb{R}^k$$：

$$p_i = \text{softmax}(\mathbf{z})_i = \frac{e^{z_i}}{\sum_{j=1}^k e^{z_j}}$$

交叉熵损失：

$$\mathcal{L} = -\sum_{i=1}^k y_i \log p_i$$

对 $$z_i$$ 求梯度：

$$\frac{\partial \mathcal{L}}{\partial z_i} = p_i - y_i$$

和二元分类**完全一致**——（softmax 概率 − one-hot 真实标签）。

## 从西瓜书到 WMT

NMT 的翻译训练就是这个对称结构的最大规模实例：

```
分类任务: 56K 词选一个
模型基底: Attention/Transformer 的 hidden state → Linear(56K)
输出映射: softmax
损失函数: CrossEntropy(label_smoothing=0.1)
梯度形状: (p - y_onehot) × hidden_state
```

我们的 WMT 系列（[003-009](/wmt/)）跑了 30+ 组实验，不管 RNN 还是 Attention 还是 Transformer，梯度始终是同一个形式：**预测概率 − 真实分布，回传到 hidden 层**。K_lang 限制 softmax 分母的研究正是建立在这个对称性之上的——你不需要理解"翻译"这个任务，你只需要理解 softmax 在 56K 维空间里的梯度稀释规律。

## 小结

- 回归和分类共享同一个线性基底 $$wx+b$$
- 差异只在链接函数（sigmoid/softmax）和损失函数（MSE/CE）
- 梯度形式统一为 `(prediction − truth) × input`
- 这个对称性是广义线性模型（GLM）的数学结论，不依赖具体任务
- NMT 翻译只是这个结构在大规模分类上的应用

*May the Code be with us.*

---

> **License: GPLv3**  
> 本文《Watermelon》系列采用 GNU 通用公共许可证第三版 (GNU General Public License v3.0) 协议进行开源发布与分发。
