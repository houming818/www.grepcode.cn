---
title: "[SPR-048] TreeHeap 私有编码：多头参数森林与串行推理"
date: 2026-07-09
lastmod: 2026-07-09
author: Codex Review
description: "从经典 Huffman 编码出发，定义 TreeHeap 参数森林、私有编码、并行多头和串行 kernel composition，并说明 scalar loss 如何把数据写入参数树。"
tags: [SPR, TreeHeap, ARA, S1, Encoder, Huffman, Kernel]
---

# TreeHeap 私有编码：多头参数森林与串行推理

这篇文章承接 SPR-046 和 SPR-047，进入新的问题：

> 一个空的 TreeHeap 工作区，为什么经过若干 query kernel 的卷积，就能解压出一组数据？这些数据最初又是怎样编码进一棵或多棵参数 TreeHeap 的？

我们先不讨论自然语言理解，也不假设模型已经知道“食物”“水果”等概念。先建立一个有限、可以计算和证伪的模型。

## 1. 从一个具体例子开始

假设执行 `food` kernel：

```text
H0 = [0, 0, 0, 0]

K_food(H0; Theta)
  -> [0.1 稻子, 0.3 米浆, 0.5 米饭, 0.6 芒果]
```

再执行 `fruit` kernel：

```text
K_fruit(K_food(H0; Theta); Theta2)
  -> [0.6 芒果]
```

这里马上出现一个必须说清楚的事实：

```text
零数组里没有稻子、米浆、米饭和芒果。
```

因此，这些信息一定保存在参数 `Theta` 及其树形组织关系中。`H0` 只是一次查询使用的工作区。

本文采用以下术语：

```text
Theta_forest 长期保存的一组参数 TreeHeap，也就是编码森林
H_query     一次查询产生的运行时状态
K_q         针对 query q 执行的卷积 kernel
leaf        可以最终解码出的数据对象
internal    一组叶子共享的前缀状态
```

## 2. 经典 Huffman 到底怎样写入和读出

假设四个符号出现的概率为：

| 符号 | 概率 |
|---|---:|
| 米饭 | 0.4 |
| 米浆 | 0.3 |
| 稻子 | 0.2 |
| 石头 | 0.1 |

经典 Huffman 算法不断合并概率最小的两个节点，可能得到：

```text
root
├─ 0   -> 米饭
└─ 1
   ├─ 10  -> 米浆
   └─ 11
      ├─ 110 -> 石头
      └─ 111 -> 稻子
```

对应码表：

```text
米饭 = 0
米浆 = 10
石头 = 110
稻子 = 111
```

编码：

```text
米饭 石头 稻子
-> 0 110 111
-> 0110111
```

解码时，从 root 开始逐位行走。到达叶子便输出符号，然后返回 root。

这里有两个重要性质：

1. 高频符号使用较短路径；
2. 任何叶子的编码都不是另一个叶子编码的前缀，因此可以无歧义解码。

但是，经典 Huffman 只根据出现频率压缩。它不会因为“米饭”和“米浆”在语义上相似，就主动让它们共享前缀。

## 3. TreeHeap 增加了什么

TreeHeap 的假设是：一棵树不仅可以压缩符号频率，还可以压缩查询规律。

例如，一棵候选参数树可能是：

```text
root
└─ food
   ├─ grain-family
   │  ├─ 稻子
   │  └─ processed
   │     ├─ 米浆
   │     └─ 米饭
   └─ fruit
      └─ 芒果
```

路径可以写成：

```text
稻子 = 000
米浆 = 0010
米饭 = 0011
芒果 = 01
```

现在，不同 query 可以在不同深度停止：

```text
food query
  -> 到达 food
  -> 解压 food 节点覆盖的全部叶子

fruit query
  -> 到达 fruit
  -> 只解压 fruit 节点覆盖的叶子

exact token query
  -> 一直走到具体叶子
  -> 输出米饭或芒果
```

因此，`stop` 不一定表示“读到了一个词”。它也可以表示：

> 当前内部节点已经包含回答 query 所需的全部信息。

## 4. 路径编码和输出概率不是一回事

下面两个对象容易混淆：

```text
Path(米饭) = 0011
P(米饭 | food) = 0.5
```

`0011` 是米饭在参数树中的地址。

`0.5` 是当前 query 下米饭的分数或概率。

如果输出被解释为概率分布，就必须归一化：

$$
\sum_x P(x\mid q)=1
$$

而路径只要求前缀无歧义，不要求数值加和为 1。

## 5. Kernel 如何查询一棵树

在节点 \(i\) 上，局部 kernel 读取：

$$
K_\Theta(q,H_i,H_{2i},H_{2i+1})
$$

并输出一个概率桶：

$$
[p_{\text{stop}},p_{\text{left}},p_{\text{right}}]
$$

例如 `fruit` query：

```text
root:
  [stop=0.00, left=0.05, right=0.95]

food:
  [stop=0.02, grain=0.03, fruit=0.95]

fruit:
  [stop=0.99, left=0.005, right=0.005]
```

一条路径的概率是沿途动作概率的乘积：

$$
P(\pi\mid q)
=
\prod_{i\in\pi}P(a_i\mid q,H_i)
$$

到达某个内部节点并选择 `stop` 后，decoder 可以读取该节点保存的叶子分布：

$$
Decode(H_i,q)\rightarrow P(x\mid q,H_i)
$$

所以完整读出过程是：

```text
query
-> kernel 在参数树上递归卷积
-> 得到 stop/left/right 概率
-> 形成路径分布
-> 在某个节点停止
-> 解压该节点的叶子分布
```

硬查询可以每步选择 `argmax`。软查询则保留多条路径，直到信息足够时再坍缩。

## 6. Encoder 面对的原始数据是什么

Encoder 不能从“空”中发现分类。它至少需要观察到查询与结果之间的统计关系。

一个有限数据集可以表示成矩阵：

| Query | 稻子 | 米浆 | 米饭 | 芒果 |
|---|---:|---:|---:|---:|
| food | 0.1 | 0.3 | 0.5 | 0.6 |
| fruit | 0 | 0 | 0 | 0.6 |
| grain | 0.1 | 0.3 | 0.5 | 0 |
| processed | 0 | 0.3 | 0.5 | 0 |

这张表不一定来自人工标签。未来它可以来自语料观察，例如：

```text
“吃 [MASK]”经常观察到米饭
“喝 [MASK]”经常观察到米浆
“成熟的 [MASK]”经常观察到芒果
```

但无论来源是什么，encoder 真正看到的是某种有限统计量：

$$
P_D(x\mid q)
$$

也就是在数据 \(D\) 中，query \(q\) 对对象 \(x\) 的条件分布。

## 7. Encoder 不是人工聚类器

一种看似直接的方案是：

```text
先计算对象之间的相似度；
再人工规定合并距离；
最后按距离构造语义树。
```

这个方案仍然是研究者替模型设计编码。即使最终树看起来合理，也不能说明 encoder 和 decoder 形成了自己的关联编码。

本文采用更严格的定义：

```text
人提供：
  有限 TreeHeap 地址
  stop/left/right
  compose/decompose
  可微 kernel

人不提供：
  哪个节点是 food
  哪些对象必须共享前缀
  哪个 token 写在哪条路径
  每个 head 必须学习什么类别
```

参数 TreeHeap 从零或随机状态开始：

```text
Theta[i] = learnable parameters
```

给定 query \(q\)，kernel 对参数树执行卷积：

$$
\hat Y_q=K_q(\Theta)
$$

数据提供该 query 的目标结果 \(Y_q\)，于是得到一个标量 loss：

$$
L_q=d(\hat Y_q,Y_q)
$$

多个 query 共同训练参数树：

$$
L(\Theta)=\sum_q L_q
$$

梯度直接写入参数 TreeHeap：

$$
\Theta
\leftarrow
\Theta-\eta\frac{\partial L}{\partial\Theta}
$$

因此：

```text
Encoder：
  用 query 产生的 scalar loss，把规律写入参数 TreeHeap。

Decoder：
  用 query kernel 从训练后的参数 TreeHeap 解压结果。
```

内部编码可以不符合人类命名。只要 encode、query、decode 闭合，模型可以形成自己的“笔迹”。

## 8. 为什么还需要压缩约束

只优化 query 正确率，模型可能把每个答案分别记在巨大参数表里。它虽然能查询，却没有形成有价值的编码。

因此还需要限制平均编码成本：

$$
L_{\text{rate}}
=
\mathbb E[-\log P_\Theta(path)]
$$

或者先使用简单的期望路径深度：

$$
L_{\text{depth}}
=
\mathbb E[\operatorname{depth}(path)]
$$

总目标可以写成：

$$
L
=
L_{\text{query}}
+
\alpha L_{\text{echo}}
+
\beta L_{\text{rate}}
$$

三部分分别要求：

```text
query：能回答问题；
echo：私有编码仍能还原原始数据；
rate：不要为每个样本建立无限长、互不共享的路径。
```

这里没有人工规定共享前缀。只有当共享某个子堆能降低总 loss 时，它才应该形成。

## 9. 写入究竟发生在哪里

必须区分两种“写入”。

### 9.1 训练参数森林

```text
Train(D)
-> 修改 Theta_forest
-> 改变节点状态、路径概率和 kernel 参数
```

这相当于学习和更新码本。

### 9.2 使用参数森林编码一个样本

```text
Encode(sample, Theta_forest)
-> 生成路径或运行时 H_sample
```

这相当于使用已经存在的码本压缩一条消息，通常不修改长期参数树。

因此：

```text
Theta_forest 保存长期规律
H_sample 保存当前样本
H_query 保存本次查询过程
```

如果 `H0=[0,0,0,0]` 经过 kernel 能生成具体对象，那么具体对象的信息来自 `Theta_forest`，不能说它来自零状态。

## 10. Encoder 和 Decoder 的共同协议

Transformer 的 encoder、decoder 和 cross-attention 都使用同一种 Attention 数学接口，但通常不共享同一套参数。

TreeHeap 也可以采用类似的接口纪律，但这只是接口设计，不是 Transformer 有效性向 TreeHeap 的自动迁移。

共同协议可以定义为：

$$
K(q,H_i,H_{2i},H_{2i+1})
\rightarrow
[p_{\text{stop}},p_{\text{left}},p_{\text{right}}]
$$

Encoder 使用它评估：

```text
一个对象写入哪个前缀，能让整个数据集更容易重建。
```

Decoder 使用它完成：

```text
一个 query 应沿哪条路径读取，并在哪个节点停止。
```

双方必须共享：

```text
相同的地址规则
相同的路径含义
相同的节点 compose/decompose 规则
相同的 kernel 输入输出契约
```

它们不必共享完全相同的权重。

## 11. 为什么不要求所有信息写进同一棵树

一棵共享参数树适合表达公共前缀，但它不是 TreeHeap 的理论限制。更一般的参数对象是：

$$
\Theta_{\text{forest}}
=
\{\Theta^{(1)},\Theta^{(2)},\ldots,\Theta^{(M)}\}
$$

每个 head 都是一棵 TreeHeap。它们共享地址和 kernel 协议，但可以拥有不同的节点值、深度和参数。

### 11.1 并行多头

多个 head 可以同时观察同一个状态：

$$
H_m=K_m(q,H_0;\Theta^{(m)})
$$

再通过明确的 TreeHeap compose 算子合并：

$$
H_{\text{out}}
=
\operatorname{Compose}(H_1,H_2,\ldots,H_M)
$$

这种结构允许不同参数树保留不同的可学习关系，不要求它们被压进同一个梯度大锅。

### 11.2 串行推理

更重要的是 kernel 可以顺序组合：

```text
H0 = [0,0,0,0]

H1 = K_food(H0; Theta_food)
   = [0.1稻子, 0.3米浆, 0.5米饭, 0.6芒果]

H2 = K_fruit(H1; Theta_fruit)
   = [0.6芒果]
```

数学上：

$$
H_2
=
K_{\text{fruit}}
\left(
K_{\text{food}}(H_0;\Theta_{\text{food}});
\Theta_{\text{fruit}}
\right)
$$

也就是：

$$
K_{\text{fruit}}\circ K_{\text{food}}
$$

这使 TreeHeap 不只是保存查询答案，还可能保存可组合的操作。

## 12. 连续查表不等于串行推理

如果 `Theta_fruit` 直接记住：

```text
fruit query -> 芒果
```

那么连续执行两个 query 仍然只是两次查表。

真正的 `fruit` kernel 应当对不同输入状态执行同一过滤规律：

```text
[苹果, 石头, 芒果] -> [苹果, 芒果]
[稻子, 米饭, 芒果] -> [芒果]
[香蕉, 汽车, 梨]   -> [香蕉, 梨]
```

所以必须把以下组合留出训练集：

```text
K_fruit(K_food(H0))
```

分别训练 `food` head 和 `fruit` head 后，第一次在测试中组合它们。只有未见组合仍然正确，才能支持“kernel 学会了算子”而不是“参数树记住了答案”。

## 13. 一个重要限制：树只能自然表达嵌套集合

如果：

```text
fruit 是 food 的子集
```

一棵树可以自然表达。

但真实世界存在重叠分类：

```text
番茄在植物学中是水果
番茄在烹饪中又常被视为蔬菜
```

单棵严格二叉树无法让一个叶子同时拥有两条独立父路径。

可能的扩展包括：

```text
多个 TreeHeap
一个叶子对应多条概率路径
TreeHeap DAG
```

第一阶段不应同时解决这个问题。我们可以先使用严格嵌套的有限数据，验证最基本的编码和解码闭环。

## 14. 下一步可证伪实验

第一项实验只需要四到八个对象、四到八种 query，以及两棵小参数 TreeHeap。

### Claim

存在一个有限参数 TreeHeap forest，使 scalar query loss 能把数据写入各参数树，并使独立训练的 kernel 在未见串行组合上正确闭合。

```text
较低的 query 重建误差
较短的平均编码长度
前缀无歧义的精确 echo
未见 kernel composition 的正确输出
```

### Predict

如果 head 学到的是可迁移算子，那么 `fruit` kernel 在训练时未见过 `food` head 输出的情况下，仍应正确过滤 `food` 的运行时状态。

如果它只记住 query 到答案的映射，未见组合应当失败。

### Proof

```text
1. 将 `Theta_food` 和 `Theta_fruit` 初始化为零或随机参数树；
2. 用各自 query 的 scalar loss 独立训练两棵树；
3. 保存每个节点的 loss、梯度和参数变化；
4. 验证只保存参数森林即可重新解压训练 query；
5. 测试训练时保留的 `K_fruit ∘ K_food` 组合；
6. 与两个独立查找表、单棵共享树和 shuffled control 比较；
7. 清空、打乱或交换子堆，检查查询与组合能力是否下降。
```

### Falsification

以下任一结果都会削弱当前假设：

```text
query 或答案被偷偷放进运行时 H；
每个 head 只记住固定输出，不能过滤新输入；
未见串行组合明显失败；
清空或打乱参数树以后结果不变；
扁平查找表在相同存储和计算预算下全面更好。
```

## 15. 当前结论

本文没有证明 TreeHeap 已经学会食物、水果或自然语言语义。

它只把问题缩小为一个可以执行的数学任务：

> 给定有限的 `query -> result distribution`，scalar loss 能否把规律写进一个参数 TreeHeap forest，并让各 head 通过相同代数协议并行观察、串行组合和无歧义解码？

如果答案是否定的，就不必继续讨论梯度涌现。

如果答案是肯定的，下一步才是：

```text
先证明 loss 的梯度确实写入参数树
-> 再证明 encoder/decoder 能形成私有路径编码
-> 再证明独立 head 能完成未见组合
-> 最后研究树结构和 head 数量能否自行形成
```

TreeHeap 不必只有一棵树，也不必让人类理解内部节点。真正的边界是：信息必须保存在参数树中，query 不能携带答案，kernel 必须在新状态上执行可复用操作，而不是连续查表。
