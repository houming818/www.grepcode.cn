---
title: "[WATERMELON-005] 不止 softmax——概率单纯形的多种解放路径"
date: 2026-05-08
author: nio (Houming818) & opencode (First Mate)
keywords: Machine Learning, Simplex, ALR, CLR, ILR, Aitchison, Compositional Data, Log-Ratio
description: softmax 不是概率单纯形到实数空间的唯一映射。ALR、CLR、ILR 三族 log-ratio 变换各有何几何性质？它们的梯度行为有何不同？
tags: [Watermelon, Simplex, Log-Ratio, ALR, CLR, ILR, Compositional Data, GPL]
---

# 不止 softmax——概率单纯形的多种解放路径

> 004 用三色球实验展示了概率单纯形不是线性空间。softmax 是"解放"它的一条路，但还有别的。当改变参考类、几何均值或正交基时，单纯形展开的形状不同——梯度行为也不同。

## 问题重述 {#sec-recap}

概率向量 $$\mathbf{p} \in \Delta^k$$ 生活在单纯形上：

$$\Delta^k = \{\mathbf{p} \in \mathbb{R}^k : p_i \geq 0, \sum p_i = 1\}$$

这不是线性空间，因为非负约束和求和约束封闭了加法和数乘。我们需要一个变换

$$f: \Delta^k \to \mathbb{R}^m, \quad m = k-1$$

把概率"解放"到无约束的线性空间中去。004 的 @tbl-conclusion 总结了 softmax 逆映射（log）做这件事。但它不是唯一的。

## 三个约束，三种解法 {#sec-three-solutions}

概率向量有三个约束：

1. **非负性** $$p_i \geq 0$$——用 log 解决
2. **求和归一** $$\sum p_i = 1$$——用比值解决
3. **自由度冗余** 概率有 k 个参数但只有 k-1 个自由度——用参考类/均值/正交基解决

三个约束天然对应三族 log-ratio 变换。所有变换的核心都是**取比值再取对数**。

<a id="tbl-alr-clr-ilr"></a>
**表1** 三种比对数变换

| 变换 | 公式 | 自由度消除方式 | 约束 |
|------|------|-------------|------|
| ALR | $$z_i = \log(p_i / p_k)$$, $$i < k$$ | 固定一个参考类 $$p_k$$ | $$z_k = 0$$ |
| CLR | $$z_i = \log(p_i / g)$$, $$g = (\prod p_j)^{1/k}$$ | 几何均值归一化 | $$\sum z_i = 0$$ |
| ILR | $$z = \text{ILR}(\mathbf{p})$$ | 正交基展开 | $$\|z\|^2 = \text{等距}$$ |

<a id="fig-compare"></a>
**图1** 同一组概率网格三种展开：

![ALR vs CLR vs ILR 对比](/img/watermelon_005/alr_clr_ilr_compare.png)

同样的概率点在三种映射下变成不同的平面布局——但拓扑结构不变（都是开凸集的同胚）。

## ALR：固定参考类的简单比值 {#sec-alr}

ALR（Additive Log-Ratio）是直觉上最简单的做法——选一个类做参考（比如"灰"=$$p_3$$），其他类跟它比：

$$z_i = \log\frac{p_i}{p_3}, \quad i = 1, 2$$

<a id="fig-alr-references"></a>
**图2** 选不同参考类时的 ALR 映射：

![不同参考类的 ALR 映射对比](/img/watermelon_005/alr_refs.png)

选了不同的参考类，网格在平面上的位置和旋转不同——但形状完全相同。因为 ALR 之间的变换是平移 + 缩放：

$$\text{ALR}_{(ref=j)}(\mathbf{p}) = A \cdot \text{ALR}_{(ref=k)}(\mathbf{p}) + b$$

其中 A 是一个线性变换矩阵，b 是平移向量。这说明 ALR 虽然简单，但参考类的选择会引入**不对称性**——三个参考类给出三个不同坐标系。

## CLR：对称的几何均值归一化 {#sec-clr}

CLR（Centered Log-Ratio）不使用参考类，而是使用几何均值：

$$g(\mathbf{p}) = \left(\prod_{j=1}^k p_j\right)^{1/k}, \quad
z_i = \log\frac{p_i}{g(\mathbf{p})}$$

CLR 的优点是对所有类对称——没有参考类的不均匀性。但代价是 k 个 CLR 变量之和为零：

$$\sum_{i=1}^k z_i = \sum_{i=1}^k \left(\log p_i - \log g\right)
 = \sum_i \log p_i - k \cdot \frac{1}{k} \sum_j \log p_j = 0$$

所以 CLR 变量仍然生活在 ℝ^k 的一个 **k-1 维子空间**中——不是完全自由的。

<a id="fig-clr"></a>
**图3** CLR 的 $$\sum z_i = 0$$ 约束：

![CLR 约束平面投影](/img/watermelon_005/clr_constraint.png)

颜色表示概率分布的内部结构——从白（左下）到灰（右上）的渐变。CLR 空间保持了这种连续拓扑。

## ILR：真正的等距正交展开 {#sec-ilr}

ILR（Isometric Log-Ratio）在前两者的基础上更进一步——构造一组 $$k-1$$ 个正交基向量，把单纯形映射到标准欧几里得空间 ℝ^{k-1}，保持距离（度量）：

$$\| \text{ILR}(\mathbf{p}) - \text{ILR}(\mathbf{q}) \| = d_A(\mathbf{p}, \mathbf{q})$$

其中 $$d_A$$ 是 **Aitchison 距离**——单纯形上的标准度量：

$$d_A(\mathbf{p}, \mathbf{q}) = \sqrt{\sum_{i=1}^k \left( \log\frac{p_i}{g(\mathbf{p})} - \log\frac{q_i}{g(\mathbf{q})} \right)^2}$$

ILR 的基向量构造如下（以 k=3 为例）：

$$\boldsymbol{\psi}_1 = \left(\sqrt{\frac{2}{3}}, -\sqrt{\frac{1}{6}}, -\sqrt{\frac{1}{6}}\right), \quad
\boldsymbol{\psi}_2 = \left(0, \sqrt{\frac{1}{2}}, -\sqrt{\frac{1}{2}}\right)$$

则 ILR 坐标为 $$\mathbf{z} = \mathbf{p} \cdot \boldsymbol{\Psi}$$，其中 $$\boldsymbol{\Psi}$$ 是 $$k \times (k-1)$$ 的基矩阵。

ILR 的优势在于**等距性**——在 ILR 空间里欧几里得距离等价于 Aitchison 距离。这意味着在单纯形上做 K-means 或 PCA 时，可以在 ILR 空间里计算，结果等价于在概率空间里做成分分析。

## 三种变换的梯度对比 {#sec-gradient}

对于分类任务的梯度下降：

| 变换 | 梯度形式 | 与 CE 兼容？ | 计算复杂度 |
|------|---------|------------|----------|
| softmax (z→p) | $$\nabla = p - y$$ | ✅ 天然 | $$O(k)$$ |
| ALR (逆) | $$\nabla_i = \frac{\partial \mathcal{L}}{\partial p_i} \cdot p_i - \text{耦合项}$$ | ❌ 需手动 | $$O(k)$$ |
| CLR (逆) | 同上，但对称 | ❌ 需手动 | $$O(k)$$ |
| ILR (逆) | 通过基矩阵线性变换 | ❌ 需手动 | $$O(k)$$ |

softmax 在梯度上的优势是**CE 的倒数恰好抵消了 softmax 的导数**，这是其他变换不具备的组合结构。并非所有变换都享有这种"梯度净化"特性——这是 softmax + CE 的专属组合。

但从 **单纯的线性空间映射** 角度看——如果你不关心 CE 的梯度互消，只是需要一个从概率到实数空间的变换——ALR/CLR/ILR 都是有效的工具。它们在成分数据分析、地质学、生物信息学中广泛应用。

## 总结 {#sec-conclusion}

<a id="tbl-conclusion"></a>
**表2** 四种映射总结

| 映射 | 不对称 | 零和约束 | 等距 | 梯度净化 | 主要用途 |
|------|--------|---------|------|---------|---------|
| softmax 逆 (log+归一化) | ❌ 有平移自由度 | ❌ | ❌ | ✅ CE 专属 | 分类 NN |
| ALR | ✅ 选参考类 | $$z_k = 0$$ | ❌ | ❌ | 成分分析 |
| CLR | ❌ 对称 | $$\sum z_i = 0$$ | ❌ | ❌ | 对称成分分析 |
| ILR | ❌ 基的选择 | ✅ 自然正交 | ✅ | ❌ | 统计建模、PCA |

**选择建议**：
- 做**分类训练** → softmax + CE（梯度是命根）
- 做**概率空间的数据分析**（PCA、聚类）→ ILR（等距是关键）
- 做**对称成分可视化** → CLR（几何均值参考）
- 做**快速理解** → ALR（直觉最简单）

回到 004 的点彩实验（@sec-pointillism），我们实际使用了 ALR——选灰为参考类，映射到 `(log(p_黑/p_灰), log(p_白/p_灰))`。这是最简单的 log-ratio 变换，足以展示"三角形→平面"的拓扑变化。如果换用 CLR 或 ILR，点彩的形状会旋转平移，但点的相对分布疏密不变——因为拓扑结构是映射不变的。

*May the Code be with us.*

---

> **License: GPLv3**  
> 本文《Watermelon》系列采用 GNU 通用公共许可证第三版 (GNU General Public License v3.0) 协议进行开源发布与分发。
