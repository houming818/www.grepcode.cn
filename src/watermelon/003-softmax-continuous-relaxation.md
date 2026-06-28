---
title: "[WATERMELON-003] softmax——从离散标签到连续梯度"
date: 2026-05-08
author: nio (Houming818) & opencode (First Mate)
keywords: Machine Learning, softmax, Classification, Probability, Gradient, Continuous Relaxation
description: 分类标签是离散的，梯度在离散点上不存在。softmax 把离散选择转化为连续概率分布，让梯度得以流过——这是分类问题能被优化的数学前提。
tags: [Watermelon, softmax, Classification, Continuous Relaxation, Gradient, GPL]
---

# softmax——从离散标签到连续梯度

> 分类标签是离散的 `{猫, 狗, 鸟}`，梯度对离散变量无定义。softmax 把一个 56K 维的离散选择松弛为 56K 维的连续概率分布——自此，梯度得以下山。

## 问题：离散标签没有梯度 {#sec-discrete}

分类任务的真值是离散向量。以三分类为例：

$$\mathbf{y} = [0, 1, 0]$$

这个向量在数学上是 "one-hot 表示"。它的特性：
- 只有一个位置是 1，其余是 0
- 在 0 和 1 之间没有任何中间值
- 对 `y` 的导数无定义——你不能问 "把猫变成 1.1 只猫" 是什么意思

梯度下降要求损失函数在参数空间上处处可微。如果输出直接对应离散标签，梯度就断了。

## softmax：离散 → 连续的松弛 {#sec-softmax}

softmax 的核心操作是对模型输出的 `logits` 向量做 **指数归一化**：

$$p_i = \text{softmax}(\mathbf{z})_i = \frac{e^{z_i}}{\sum_{j=1}^k e^{z_j}}$$

其中 $$\mathbf{z} = [z_1, z_2, z_3]$$ 是模型最后一层 linear 输出的原始分数（logits）。

<a id="tbl-softmax-steps"></a>
**表1** softmax 做了什么：

| 步骤 | 操作 | 效果 |
|------|------|------|
| 1 | $$e^{z_i}$$ | 把负无穷到正无穷的实数 → 正数，保序 |
| 2 | $$\sum_j e^{z_j}$$ | 累加所有正数 |
| 3 | $$e^{z_i} / \sum_j e^{z_j}$$ | 归一化到 $$(0, 1)$$ |

结果是一个 **概率分布**：

$$\sum_{i=1}^k p_i = 1, \quad p_i \in (0, 1)$$

这个分布在 `(0, 1)` 上连续可微。每个 $$p_i$$ 不再是 0 或 1，而是一个**光滑的近似**——它告诉你 "模型认为这个 token 有 73% 的概率是正确的"。

## 为什么是指数函数 `e^z`？ {#sec-why-exp}

三个等价理由：

### 1. 数学必然性——从最大熵推导 {#sec-maxent}

在已知 logits 线性约束下，使熵最大的概率分布恰好是 softmax。这是**最大熵原理**的推论——在一个信息有限的系统里，最稳妥的猜测是假设均匀分布加约束：

$$\text{maximize} \quad -\sum_i p_i \log p_i \quad \text{subject to} \quad \sum_i p_i = 1, \quad \sum_i p_i z_i = \text{const}$$

拉格朗日乘子法求出的解析解就是 softmax。

### 2. 统计必然性——从玻尔兹曼分布推导 {#sec-boltzmann}

统计力学中，一个系统在温度为 $$T$$ 的热浴中，处于能量为 $$E_i$$ 的状态的概率是：

$$p_i \propto e^{-E_i / k_B T}$$

令 $$z_i = -E_i / k_B T$$，这就是 softmax。机器学习里 $$\mathbf{z}$$ 相当于模型的"信任能级"——越高的 logit，对应越低的状态能量，越可能被采样。

### 3. 优化必然性——配合 CrossEntropy 求导极简 {#sec-gradient}

CrossEntropy loss：

$$\mathcal{L} = -\sum_{i=1}^k y_i \log p_i$$

对 logits 求导（链式法则 + softmax 导数）：

$$\frac{\partial \mathcal{L}}{\partial z_i} = p_i - y_i$$

化简过程在 [002](/watermelon/002-symmetric-prediction/) 的 @sec-gradient 已经推过。结果是**概率 − 标签**，干净得惊人。如果不是 softmax + CE 的组合，梯度没有这么简洁。

## softmax 的"假"连续——稀释问题 {#sec-dilution}

softmax 成功地将离散标签松弛为连续概率，但在大词表场景（如 NMT 的 56K tokens）中引入了一个工程问题：

<a id="tbl-dilution"></a>
**表2** softmax 分母稀释效应：

| | 好情况（词表小） | 坏情况（词表大） |
|------|------|------|
| 词表大小 | 10 类 | 56,652 tokens |
| softmax 分母 | ~10 | 56,652 |
| 平均概率 | $$\sim 0.1$$ | $$\sim 1.8\times 10^{-5}$$ |
| 梯度量级 | $$\sim 0.1$$ | $$\sim 1.8\times 10^{-5}$$ |
| 学习效果 | 每个 token 的梯度明显 | **梯度被均匀稀释** |

softmax 的连续松弛在做**除法归一化**时，分母是整个词表的所有指数项之和。词表越大，每个 token 分配到的概率越小，梯度越小。

这就是 restricted softmax 和 K_lang 碰撞框架的切入点——如果你知道只有 ~170 个 token 之间有有效碰撞（$$K_{\text{lang}} \times |V|$$），为什么要把分母扩展到一个大多数 token 无关的 56K 维空间呢？详见 [004](/watermelon/004-probability-simplex-linear-space/) 的 @sec-pointillism 和 @sec-resolution。

## 大词表的三种优化路线 {#sec-fast-softmax}

到了 BPE 32K 甚至 BPE 56K 的词表，全量 softmax 虽然数学正确，但每次训练的重计算是浪费——绝大多数 token 的概率趋近于 0。工程上有三条路：

<a id="tbl-fast-softmax"></a>
**表3** 优化 softmax 的三种思路

| 方法 | 数据结构 | 规律 | 复杂度 | 取舍 |
|------|---------|------|--------|------|
| **Hierarchical** | 哈夫曼树 | 高频词路径短，低频词路径长 | $$O(\log V)$$ | 树结构僵化 |
| **Adaptive** | 频率 cluster | 高频词独占大容量，低频词共享小容量 | $$O(\log\|C\|)$$ | cluster 边界硬 |
| **Top-k restricted** | topk(z, k) | 只有碰撞桶内的词有有效信号 | $$O(V)$$ 线性投影 + $$O(k\log k)$$ topk | k 决定代价 |

两种不同哲学：

- **Hierarchical / Adaptive** — 利用可观测的语言规律（高频/低频）构建预定义数据结构，把搜索变成树遍历。
- **Top-k restricted / K_lang** — 利用碰撞常数 $$K_{\text{lang}} \approx 0.003$$ 作为理论约束，认定 "只有 ~170 个 token 之间有有效碰撞"，把 softmax 分母限制在这些 token 上。**它不是近似，是重新定义了什么是有意义的概率空间。**

Top-k 的做法最接近本文的论点：**既然大多数概率是噪声，不如直接砍掉它们，让梯度全部集中在少数相关 token 上。** 但这种做法的代价是放弃了 softmax 的全局归一化——可能在词表极端稀疏时丢失信号。

## 代码实验 {#sec-code}

下面用三分类做一个最小可重现的实验，验证 softmax 的梯度行为：

<a id="lst-grad-verify"></a>
**代码1** 三分类梯度验证：

```python
import torch
import torch.nn.functional as F

# 三分类，一个样本，logits 是原始得分
logits = torch.tensor([2.0, 1.0, 0.1], requires_grad=True)
# 真实标签（one-hot）
y = torch.tensor([1.0, 0.0, 0.0])
# 真实标签对应的类别索引
target = torch.tensor(0)

# softmax → 连续概率
p = F.softmax(logits, dim=-1)  # [0.659, 0.242, 0.099]

# CrossEntropy loss
loss = F.cross_entropy(logits.unsqueeze(0), target.unsqueeze(0))
print(f"logits: {logits}")
print(f"p:      {p}")
print(f"loss:   {loss:.4f}")

# 验证梯度公式：p_i - y_i
logits.grad = None
loss.backward()
expected_grad = p - y  # [0.659-1, 0.242-0, 0.099-0] = [-0.341, 0.242, 0.099]
print(f"grad:   {logits.grad}")
print(f"expect: {expected_grad}")
print(f"match:  {torch.allclose(logits.grad, expected_grad)}")
```

输出：

```
logits: tensor([2.0000, 1.0000, 0.1000], requires_grad=True)
p:      tensor([0.6590, 0.2424, 0.0986], grad_fn=<SoftmaxBackward0>)
loss:   0.4170
grad:   tensor([-0.3410,  0.2424,  0.0986])
expect: tensor([-0.3410,  0.2424,  0.0986])
match:  True
```

$$p - y$$ 恰好就是梯度。正确类的梯度为负（概率 0.659，标签 1.0，差值 −0.341），错误类的梯度为正——梯度会把概率从错误类比回正确类。这就是 softmax + CE 组合的梯度发动机。

## 结论：离散标签没有梯度——是 softmax 把它变出来的 {#sec-conclusion}

<a id="tbl-conclusion"></a>
**表3** 概念总结：

| 概念 | 说明 |
|------|------|
| 离散标签 | 无法求导 |
| softmax | 指数归一化，把 logits 映射到 (0,1) 上的连续概率分布 |
| CE loss | 在连续概率上定义距离 |
| **梯度 = p − y** | 预测概率 − 真实标签，干净的线性形式 |
| **本质** | softmax 是离散问题的**连续松弛**（continuous relaxation），不是近似——是让梯度流存在的数学桥梁 |

这个认识对 WMT 机器学习翻译训练至关重要。56K 维度的 softmax 虽然数学上连续可微，但在工程上被稀释到噪声水平。如果你理解了 softmax 是"离散→连续"的转换器，再回头看 K_lang 限制软最大分母的策略——那是把稀释的连续概率重新浓缩回有效的碰撞空间。

*May the Code be with us.*

---

> **License: GPLv3**  
> 本文《Watermelon》系列采用 GNU 通用公共许可证第三版 (GNU General Public License v3.0) 协议进行开源发布与分发。
