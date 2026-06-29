---
title: "[SPR-024] 概率 Kernel：用 KL 散度衡量 TreeHeap 是否学到世界模型"
date: 2026-06-24
weight: 24
author: nio (Houming818) & Codex Review
description: "把 TreeHeap kernel 拆成代数 kernel 与概率 kernel：前者证明操作定义正确，后者用 KL 散度和交叉熵证明模型是否学到了世界模型中的操作分布。"
tags: [SPR, TreeHeap, ARA, Kernel, Probability, KL]
---

# 概率 Kernel：用 KL 散度衡量 TreeHeap 是否学到世界模型

上一篇 `SPR-023` 证明了一件很基础的事：

```text
TreeHeap 的 search / plus / conjugate
可以统一理解成 kernel 在树形内存态上的卷积。
```

但 Houming818 进一步指出：

```text
kernel 也要分类型。
有的 kernel 是代数的，100% 确定；
有的 kernel 是概率的，像 softmax 一样输出分布。
```

这个拆分非常重要。

因为它可以直接回答 GLM 对 C08 的批评：

```text
conjugate proof 是 by construction。
```

是的。

如果一个 kernel 是代数 kernel，它本来就应该 by construction。
它证明的是：

```text
操作定义是否正确。
```

不是证明：

```text
模型是否学会了这个操作。
```

如果要证明“学会了”，就必须进入第二类：

```text
概率 kernel proof。
```

而概率 kernel proof 需要一个新的量尺。

这个量尺就是：

```text
KL 散度。
```

## 两类 Kernel

TreeHeap kernel 现在应该拆成两层。

```text
1. Algebraic Kernel
2. Probabilistic Kernel
```

它们分别回答不同问题。

## Algebraic Kernel：证明操作空间

代数 kernel 是确定性的。

它像数学函数：

$$ K(H) \to H' $$

只要输入相同，输出就相同。

例如：

```text
mirror kernel
path shift kernel
subheap extract kernel
exact match kernel
compose kernel
decompose kernel
conjugate kernel
```

这些 kernel 的目标不是学习。

它们的目标是证明：

```text
TreeHeap 操作空间定义良好。
```

例如镜像：

```text
L <-> R
```

如果路径：

```text
LRL
```

镜像后应该是：

```text
RLR
```

这不是概率问题。

这是代数定义。

如果写成公式：

$$ \sigma(LRL)=RLR $$

那 proof 应该要求：

$$ \sigma^{-1}(\sigma(a)) = a $$

也就是：

```text
镜像两次回到原路径。
```

这类 proof 的指标应该是：

```text
closure_ok = true
mirror_error = 0
equiv_error = 0
compose_consistency = true
```

它对应：

```text
数学正确性。
```

所以 `SPR-023` 的 C08 更准确地说属于：

```text
Algebraic Kernel Proof
```

它证明：

```text
search / plus / conjugate 可以被统一定义成 kernel convolution。
```

它不证明：

```text
模型从数据里学会了 search / plus / conjugate。
```

## Probabilistic Kernel：证明选择机制

概率 kernel 不直接输出一个确定结果。

它输出一个分布：

$$ P_\theta(a \mid H,q) $$

其中：

| 符号 | 含义 |
|---|---|
| \(H\) | 当前 TreeHeap 内存态 |
| \(q\) | query |
| \(a\) | 候选操作或候选地址 |
| \(\theta\) | 可学习参数 |

例如 route kernel：

```text
stop: 0.1
left: 0.8
right: 0.1
```

例如 write kernel：

```text
LL: 0.05
LR: 0.82
RL: 0.07
RR: 0.06
```

例如 decompose kernel：

```text
A+B: 0.55
C+D: 0.35
other: 0.10
```

这才进入学习问题。

它问的是：

```text
模型输出的概率分布，
是否接近世界模型里的真实概率分布？
```

## 世界模型里的概率分布

我们先定义一个世界模型。

世界模型不是玄学。

在 proof 里，它可以是一个明确的数据生成器：

```text
WorldModel W
```

它给出：

$$ P_W(a \mid H,q) $$

意思是：

```text
在 TreeHeap 状态 H 和 query q 下，
世界模型认为每个操作 a 的真实概率是多少。
```

例如：

```text
P_W(stop, left, right)
=
[0.1, 0.8, 0.1]
```

模型输出：

```text
P_\theta(stop, left, right)
=
[0.3, 0.4, 0.3]
```

这时我们就可以问：

```text
模型离世界模型有多远？
```

这个距离就用 KL 散度衡量。

## KL 散度是什么

KL 散度的定义是：

$$ D_{\rm KL}(P \parallel Q) = \sum_x P(x)\log \frac{P(x)}{Q(x)} $$

在我们这里：

```text
P = 世界模型分布
Q = TreeHeap kernel 学到的分布
```

所以：

$$ D_{\rm KL} \big( P_W(a \mid H,q) \parallel P_\theta(a \mid H,q) \big) = \sum_a P_W(a \mid H,q) \log \frac{ P_W(a \mid H,q) }{ P_\theta(a \mid H,q) } $$

人话解释：

```text
如果真实世界按 P_W 运行，
但模型用 P_theta 去解释，
会多付出多少信息代价？
```

如果：

$$ P_\theta = P_W $$

那么：

$$ D_{\rm KL}(P_W \parallel P_\theta)=0 $$

越接近 0，说明模型越像世界模型。

## KL 与交叉熵

KL 可以展开：

$$ D_{\rm KL}(P \parallel Q) = H(P,Q)-H(P) $$

其中：

$$ H(P,Q) = -\sum_x P(x)\log Q(x) $$

是交叉熵。

因为 \(H(P)\) 是世界模型自己的熵，对模型参数 \(\theta\) 来说是常数。

所以训练时：

$$ \min_\theta D_{\rm KL}(P_W \parallel P_\theta) $$

等价于：

$$ \min_\theta H(P_W, P_\theta) $$

这就是为什么机器学习经常用 cross entropy。

如果 \(P_W\) 是 one-hot：

```text
left = 1.0
其他 = 0.0
```

那就是普通分类。

如果 \(P_W\) 是 soft distribution：

```text
stop = 0.1
left = 0.8
right = 0.1
```

那就是概率模仿。

TreeHeap 的概率 kernel 更应该从 soft distribution 开始。

因为 TreeHeap 的核心思想之一是：

```text
信息不足时不要过早坍缩。
```

## TreeHeap 的概率 Kernel 训练目标

一个概率 TreeHeap kernel 可以写成：

$$ P_\theta(a \mid H,q) = \operatorname{softmax}(K_\theta(H,q))_a $$

世界模型给：

$$ P_W(a \mid H,q) $$

训练 loss：

$$ L(\theta) = \mathbb{E}_{(H,q)\sim \mathcal{D}} \left[ D_{\rm KL} \big( P_W(a \mid H,q) \parallel P_\theta(a \mid H,q) \big) \right] $$

人话：

```text
在很多 TreeHeap 状态和 query 上，
让模型输出的操作分布接近世界模型的操作分布。
```

这可以训练：

```text
route kernel
write kernel
merge kernel
decompose kernel
collapse kernel
```

## plus 的两层定义

现在 plus 可以拆成两层。

第一层是代数候选：

$$ \{\operatorname{Plus}_a(H,x)\}_{a\in A} $$

意思是：

```text
对每个地址 a，
如果把 x plus 到那里，
都会得到一个合法候选 TreeHeap。
```

这是代数 kernel 的部分。

第二层是概率选择：

$$ P_\theta(a \mid H,x) $$

意思是：

```text
模型认为这次应该写到哪个地址。
```

Soft Plus 是两者合起来：

$$ H_{t+1} = \sum_a P_\theta(a \mid H,x) \operatorname{Plus}_a(H,x) $$

如果 \(P_\theta\) 最后坍缩成 one-hot：

```text
P_theta(LR)=1.0
其他 = 0.0
```

那它就回到 hard plus。

所以：

```text
代数 kernel 定义可以做什么；
概率 kernel 学习什么时候做什么。
```

这是这篇最重要的一句话。

## 一个 Toy 世界模型

为了证明概率 kernel 能学到世界模型，我们需要先设计一个可控世界。

例如定义一个路由世界：

```text
如果 query 和左子堆更相似：
  P_W(left)=0.8, P_W(right)=0.1, P_W(stop)=0.1

如果 query 和右子堆更相似：
  P_W(right)=0.8, P_W(left)=0.1, P_W(stop)=0.1

如果当前节点已经足够匹配：
  P_W(stop)=0.8, P_W(left)=0.1, P_W(right)=0.1
```

注意这里不是 hard label。

不是：

```text
left = 1
```

而是：

```text
left = 0.8
```

这样才能测试 Probability Container。

模型输出：

$$ P_\theta(stop,left,right \mid H,q) $$

训练目标：

$$ D_{\rm KL}(P_W \parallel P_\theta) $$

如果训练成功，应该看到：

```text
train_KL 下降
test_KL 下降
OOD_KL 仍然较低
```

这才说明：

```text
模型不是只记住训练样本。
它学到了世界模型分布里的规律。
```

## 为什么要看 OOD KL

只看训练集 KL 不够。

因为模型可能死记：

```text
这个样本就是 left。
那个样本就是 right。
```

所以必须设计 OOD 测试。

例如：

```text
训练：
  depth <= 3
  path 只出现 L 开头

测试：
  depth >= 5
  path 出现 R 开头镜像结构
```

如果：

```text
train_KL 低
test_KL 高
```

说明模型只是记忆。

如果：

```text
train_KL 低
test_KL 低
OOD_KL 也低
```

才说明：

```text
模型学到了可迁移的世界模型概率规律。
```

## 实验设计：P-SOFT05-KL

我建议下一步 predict 写成：

```text
P-SOFT05-KL:
TreeHeap probabilistic kernel should learn a world-model operation
distribution with lower OOD KL than flat baselines.
```

中文：

```text
如果 TreeHeap 概率 kernel 真的有结构归纳偏置，
它应该能用更少样本学到世界模型的操作概率分布，
并在未见过的地址、深度、镜像结构上保持较低 KL。
```

### 数据

构造 TreeHeap toy world：

```text
H = full binary TreeHeap
q = query pattern
a = {stop, left, right} 或候选 write addresses
```

世界模型生成：

```text
P_W(a | H,q)
```

例如：

```text
P_W(a | H,q)
=
softmax(-distance(query, subheap_a) / temperature)
```

这里 distance 是世界模型内部规则。

训练模型不知道这个公式。

模型只能看到：

```text
raw query
raw subheap
path/topology metadata
目标分布 P_W
```

### 模型对照

| 模型 | 输入 | 目的 |
|---|---|---|
| flat MLP | 展平 TreeHeap + query | 测普通函数逼近 |
| linear kernel | raw query + raw patch | 测线性是否足够 |
| MLP raw kernel | raw query + raw patch | 测非线性比较能力 |
| TreeHeap prob kernel | raw query + raw patch + path/topology | 测结构归纳偏置 |
| oracle fixed kernel | 世界模型公式 | 上限参考，不算学习 |

### 指标

主要指标：

```text
train_KL
test_KL
OOD_KL
```

辅助指标：

```text
cross_entropy
entropy_error
top1_agreement
calibration_error
sample_efficiency
collapse_accuracy_tau_low
```

其中：

```text
entropy_error
```

衡量模型有没有把世界模型的不确定性学出来。

例如世界模型很犹豫：

```text
[0.45, 0.45, 0.10]
```

模型不应该强行输出：

```text
[0.99, 0.01, 0.00]
```

否则它虽然 top1 可能对，但概率世界模型学错了。

## 预期结果

如果 TreeHeap 概率 kernel 成立，我们希望看到：

```text
TreeHeap prob kernel:
  train_KL 低
  test_KL 低
  OOD_KL 低
  calibration 好
  sample_efficiency 高

flat MLP:
  train_KL 可以低
  但 OOD_KL 更高

linear kernel:
  多 pattern 下 KL 较高

oracle fixed kernel:
  KL 接近 0
  作为上限参考
```

如果结果相反：

```text
flat MLP 的 OOD_KL 和 TreeHeap 一样低，
或者 TreeHeap 需要更多样本，
或者 TreeHeap calibration 更差，
```

那就说明：

```text
TreeHeap 概率 kernel 暂时没有显示结构收益。
```

这就是 falsification。

## 和 Transformer 的类比

Transformer 学到的不是：

```text
矩阵本身很神秘。
```

而是：

```text
通过梯度下降，把 token 共现、上下文相关性、
query-key-value 关系压进参数矩阵。
```

它可以被理解为学习：

$$ P(token_j \mid token_i, context) $$

TreeHeap 概率 kernel 要学的是：

$$ P(operation \mid query, subheap, path, topology, context) $$

也就是：

```text
在某个树形状态下，
应该 stop、left、right、write、merge、decompose 的概率是多少。
```

这才是 TreeHeap 的概率学习对象。

## 这篇的结论

现在 TreeHeap kernel proof 应该分成两条线。

第一条：

```text
Algebraic Kernel Proof
```

证明：

```text
TreeHeap 操作空间定义正确。
```

指标：

```text
closure
equivariance
mirror error
compose consistency
```

第二条：

```text
Probabilistic Kernel Proof
```

证明：

```text
模型能从数据中学习世界模型的操作概率分布。
```

指标：

```text
KL divergence
cross entropy
calibration
OOD KL
sample efficiency
```

最终一句话：

```text
代数 kernel 定义 TreeHeap 能做什么；
概率 kernel 学习 TreeHeap 什么时候应该做什么。
```

下一步实验就应该从 KL proof 开始。
