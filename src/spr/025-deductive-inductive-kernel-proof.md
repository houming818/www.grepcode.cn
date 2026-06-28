---
title: "[SPR-025] 演绎与归纳：TreeHeap Kernel 的两类 Proof"
date: 2026-06-24
weight: 25
author: nio (Houming818) & Codex Review
description: "把 TreeHeap kernel proof 拆成演绎证明和归纳证明：演绎证明代数操作按定义成立，归纳证明概率 kernel 能通过梯度学习拟合世界模型分布，并用 KL/OOD KL 评价。"
tags: [SPR, TreeHeap, ARA, Kernel, KL, Experiment]
---

# 演绎与归纳：TreeHeap Kernel 的两类 Proof

上一篇 `SPR-024` 说：

```text
TreeHeap kernel 要分成代数 kernel 和概率 kernel。
```

Houming818 又把问题说得更准确：

```text
这里其实是演绎推理和归纳推理的区别。
```

这句话是关键。

我们之前有时把两类 proof 混在一起了。

例如：

```text
conjugate 按公式定义后，镜像结果成立。
```

这是演绎推理。

它不是模型从数据中学出来的。

而：

```text
一个概率 kernel 通过梯度下降，学会输出接近世界模型的概率分布。
```

这是归纳推理。

它不是由公式直接推出的。

它必须通过数据、loss、梯度、参数更新和测试集来证明。

所以从这篇开始，我们把 TreeHeap kernel proof 正式拆成两类：

```text
Deductive Kernel Proof
Inductive Kernel Proof
```

## 演绎 Proof 是什么

演绎 proof 的形式是：

```text
给定定义
推出结论
```

例如镜像路径：

```text
L <-> R
```

如果：

```text
mirror(LRL) = RLR
```

再镜像一次：

```text
mirror(RLR) = LRL
```

所以：

```text
mirror(mirror(path)) = path
```

这是从定义直接推出的。

不需要训练。

不需要梯度。

不需要数据集。

只要定义正确，它就应该 100% 成立。

数学上可以写：

$$ \sigma^{-1}(\sigma(a)) = a $$

这就是演绎 proof。

## TreeHeap 里的演绎 Kernel

TreeHeap 里很多 kernel 都是这种。

例如：

```text
mirror kernel
conjugate kernel
path shift kernel
subheap extract kernel
one-hot Soft Plus
hard compose/decompose 的合法性
```

这些东西的 proof 目标是：

```text
操作定义是否自洽。
```

它们的指标应该是：

```text
mirror_error = 0
conjugate_equiv_error = 0
closure_ok = true
one_hot_soft_plus_error = 0
```

如果这些不成立，说明：

```text
TreeHeap 的代数定义有 bug。
```

但如果它们成立，也不能说明：

```text
模型学会了语言。
模型学会了概率。
模型学会了世界模型。
```

它只说明：

```text
操作空间定义正确。
```

## 归纳 Proof 是什么

归纳 proof 的形式是：

```text
给定数据
给定模型
给定 loss
通过训练更新参数
看模型是否学到数据中的规律
```

例如线性回归：

```text
y = ax + b
```

我们不知道 \(a,b\)。

模型通过数据和梯度下降学到：

```text
a_hat
b_hat
```

这不是从定义直接推出的。

这是从样本中归纳出来的。

Transformer 也是类似。

Transformer 不是因为矩阵定义在那里，所以自然懂语言。

而是因为：

```text
大量文本数据
↓
loss
↓
梯度下降
↓
参数矩阵被修正
↓
模型学到 token 共现、上下文关系、query-key-value 结构
```

这是归纳推理。

TreeHeap 的概率 kernel 也必须走这条路。

## TreeHeap 概率 Kernel 学什么

概率 kernel 输出的是分布：

$$ P_\theta(a \mid H,q) $$

其中：

| 符号 | 含义 |
|---|---|
| \(H\) | 当前 TreeHeap 状态 |
| \(q\) | query |
| \(a\) | 候选操作或候选地址 |
| \(\theta\) | 可学习参数 |

世界模型给一个目标分布：

$$ P_W(a \mid H,q) $$

模型要学的是：

```text
P_theta 尽量接近 P_W。
```

评价工具是 KL 散度：

$$ D_{KL}(P_W \parallel P_\theta) = \sum_a P_W(a)\log\frac{P_W(a)}{P_\theta(a)} $$

如果：

```text
KL 接近 0
```

说明模型分布接近世界模型分布。

如果：

```text
KL 很大
```

说明模型没学好。

这就是概率 kernel 的归纳 proof。

## 这次实验

我写了一个新 proof：

```text
deductive_inductive_kernel_probe.py
```

证据路径：

```text
ara/m0-treeheap-math/src/deductive_inductive_kernel_probe.py
ara/m0-treeheap-math/evidence/deductive_inductive_kernel_probe/
```

这个 proof 分成两部分。

第一部分：

```text
演绎 proof
```

检查代数定义是否精确成立。

第二部分：

```text
归纳 proof
```

训练概率 kernel 去模仿一个世界模型分布，并用 KL 测量。

## Part A：演绎检查

实验检查了四个确定性性质：

```text
mirror_path(mirror_path(p)) == p
mirror_patch(mirror_patch(x)) == x
conjugate score equivalence error == 0
one-hot Soft Plus == Hard Plus
```

结果：

| Check | Result |
|---|---:|
| mirror involution | True |
| mirror patch involution error | 0.000000e+00 |
| conjugate equivalence error | 0.000000e+00 |
| one-hot soft plus error | 0.000000e+00 |

解释：

```text
这些是演绎性质。
它们按定义应该成立。
```

这个结果说明：

```text
TreeHeap 的这些代数 kernel 定义是自洽的。
```

但它不说明：

```text
模型学到了概率分布。
```

这部分只属于演绎 proof。

## Part B：归纳 KL 学习

为了测试概率学习，我们构造了一个 toy world model。

世界模型定义：

```text
query 和某个子堆越接近，
这个子堆被选中的概率越高。
```

数学上：

$$ P_W(a \mid H,q)=\operatorname{softmax}(-\lVert patch(a)-query\rVert^2 / T) $$

其中 \(T=0.45\) 是温度。

模型看不到这个公式。

模型只看到：

```text
raw query
raw patch
path/topology metadata
目标概率分布 P_W
```

训练目标：

$$ \min_\theta D_{KL}(P_W \parallel P_\theta) $$

测试指标：

```text
train_KL
test_KL
OOD_KL
top1_agreement
entropy_error
calibration_l1
```

## 对照模型

这次用了五个模型：

| Model | 含义 |
|---|---|
| address_prior | 只记地址偏好，不看 query / patch |
| linear_raw | 线性模型，看 raw query + raw patch |
| mlp_raw | 非线性 MLP，看 raw query + raw patch |
| treeheap_prob_kernel | MLP + path/topology metadata |
| oracle_fixed_kernel | 直接使用世界模型公式，上限参考 |

注意：

```text
oracle_fixed_kernel 不算学习。
```

它只是告诉我们理论上最优可以到哪里。

## 实验结果

| Model | Train KL | Test KL | OOD KL | OOD top1 |
|---|---:|---:|---:|---:|
| address_prior | 1.435286 | 1.434764 | 2.403086 | 0.047 |
| linear_raw | 1.436146 | 1.440253 | 2.403392 | 0.040 |
| mlp_raw | 0.007935 | 0.009027 | 0.022695 | 0.957 |
| treeheap_prob_kernel | 0.009950 | 0.010835 | 0.053386 | 0.877 |
| oracle_fixed_kernel | 0.000000 | 0.000000 | 0.000000 | 1.000 |

结论先说清楚：

```text
归纳学习成立。
TreeHeap 结构优势没有在这个 toy 里成立。
```

为什么？

因为：

```text
mlp_raw 的 OOD KL = 0.022695
treeheap_prob_kernel 的 OOD KL = 0.053386
```

也就是说，在这个 toy world 里，单纯的 raw MLP 比加了 path/topology 的 TreeHeap prob kernel 更好。

这不是坏消息。

这是一个很有用的负边界。

它说明：

```text
这个世界模型主要由 query-patch 内容距离决定。
路径/topology 不是必要信息。
```

所以 TreeHeap 结构没有优势，是合理的。

## 这个实验真正证明了什么

它证明了三件事。

第一：

```text
演绎 proof 和归纳 proof 必须分开。
```

代数恒等式成立，是定义正确。

KL 下降，是参数从数据中学到概率规律。

第二：

```text
概率 kernel 可以用 KL 来评价。
```

`mlp_raw` 从高 KL 降到：

```text
test_KL = 0.009027
OOD_KL = 0.022695
```

说明它确实通过梯度学习到了世界模型分布。

第三：

```text
TreeHeap 结构优势需要更合适的数据分布。
```

如果世界模型只依赖内容距离：

```text
distance(query, patch)
```

那么普通 MLP 就足够强。

TreeHeap 应该在这些数据分布上证明自己：

```text
路径前缀影响概率
镜像结构影响概率
子堆组合影响概率
延迟坍缩影响概率
```

也就是说，下一步的世界模型不能只靠内容距离。

它必须让：

```text
address
path
topology
composition
decomposition
```

真的进入 \(P_W\)。

## 这次实验没证明什么

它没有证明：

```text
TreeHeap 比 MLP 更强。
```

相反，这个 toy 里：

```text
mlp_raw 更好。
```

它也没有证明：

```text
TreeHeap 能翻译。
TreeHeap 能理解句法。
TreeHeap 能替代 Transformer。
```

它只证明：

```text
概率 kernel 的归纳学习可以用 KL/OOD KL 来测量。
```

这个边界很重要。

## 下一步怎么改世界模型

下一步的世界模型应该加入结构项。

例如：

$$ P_W(a \mid H,q)=\operatorname{softmax}(-(d_{content}(a)+\lambda d_{path}(a)+\mu d_{topology}(a))/T) $$

其中：

```text
d_content:
  query 和 patch 的内容距离

d_path:
  query 目标路径和候选路径的前缀距离

d_topology:
  候选子堆的结构合法性或组合关系
```

这样，TreeHeap kernel 才有机会利用：

```text
path
topology
subheap relation
```

否则它只是一个更复杂的 MLP。

下一轮 predict 应该是：

```text
P-SOFT06:
当世界模型分布同时依赖 content + path + topology 时，
TreeHeap prob kernel 的 OOD KL 应该低于 mlp_raw。
```

对应 falsification：

```text
如果 mlp_raw 在 content+path+topology 世界里仍然匹配或优于 TreeHeap prob kernel，
那么当前 TreeHeap 概率 kernel 没有显示结构归纳偏置。
```

## 总结

这篇的结论是：

```text
演绎 proof 证明定义正确。
归纳 proof 证明参数从数据中学习。
```

TreeHeap 需要两种 proof。

代数 kernel 的成功，不应该冒充概率学习。

概率 kernel 的成功，必须用 KL、OOD KL、校准和样本效率来衡量。

这次实验支持：

```text
M0-SOFT-C09:
TreeHeap kernel proof 必须区分演绎代数恒等与归纳概率学习；
KL 散度可以衡量 learned probabilistic kernel 是否模仿了世界模型分布。
```

但它也给出一个负边界：

```text
当前 toy 不支持 TreeHeap 结构优势。
```

下一步，要把世界模型从：

```text
只依赖内容距离
```

升级为：

```text
同时依赖内容、路径、拓扑、组合和分解。
```

那才是真正测试 TreeHeap 存在性的概率 proof。
