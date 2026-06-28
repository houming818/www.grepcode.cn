---
title: "[SPR-022] TreeHeap 的数学底座：有根树 Hopf 代数、Operad 与 Kernel"
date: 2026-06-23
weight: 22
author: nio (Houming818) & Codex Review
description: "把 SPR-011 到 SPR-021 的 TreeHeap 代数设计放回已有数学框架：BCK/MKW rooted-tree Hopf algebra、operad、decomposition space、tree kernel，以及它们对 TreeHeap kernel 的意义。"
tags: [SPR, TreeHeap, ARA, Mathematics, Kernel]
---

# TreeHeap 的数学底座：有根树 Hopf 代数、Operad 与 Kernel

这篇不是新的实验报告。

它要解决一个更基础的问题：

```text
TreeHeap 的数学设计，是不是我们凭空造出来的？
还是已经有成熟数学领域能承接它？
```

现在我的判断是：

```text
TreeHeap 不是凭空出现的。
它很接近两个已有数学框架在工程上的合流：

1. 有根树上的 Hopf 代数
2. Operad，也就是多输入、单输出的组合算子理论
```

这件事很重要。

因为从 `SPR-011` 到 `SPR-021`，我们一直在手工搭建：

```text
compose
decompose
plus
inverse / transpose
subheap
kernel
probability container
soft collapse
```

现在看，这些不是孤立发明。
它们可以放回已有数学框架中解释。

## 先给一句人话版结论

如果用本科能理解的语言说：

```text
TreeHeap 是一种把“树形结构”当成计算对象的模型。

它不是只存一个向量。
它还存：
  地址
  路径
  父子关系
  子树
  如何合成
  如何分解
```

在数学上，这类对象早就被研究过。

有根树 Hopf 代数研究的是：

```text
树怎么组合？
树怎么切开？
切开以后剩下什么？
这些操作能不能形成一个封闭的代数系统？
```

Operad 研究的是：

```text
多个输入如何组合成一个输出？
组合过程如何再组合？
不同组合顺序是否一致？
```

TreeHeap 正好站在这两个问题的交叉处。

## 为什么是有根树 Hopf 代数

TreeHeap 的核心对象是有根树：

```text
        root
       /    \
   left    right
```

在工程里，我们把它实现成堆数组：

```text
A[0] = root
A[1] = left(root)
A[2] = right(root)
A[3] = left(A[1])
...
```

但是数学上，它仍然是有根树。

有根树上的 Hopf 代数，典型来源包括 Butcher 的数值分析树、Connes-Kreimer 的重整化树，以及后续 Munthe-Kaas-Wright Hopf algebra。

可以参考：

- [A Survey on the Munthe-Kaas-Wright Hopf Algebra, arXiv:2306.04381](https://arxiv.org/abs/2306.04381)

这类数学关心的不是自然语言，而是：

```text
树结构本身能不能做代数计算？
```

这和我们前面问的问题很像。

## TreeHeap 与 BCK/MKW 代数的对应

先看一个对应表。

| TreeHeap 里的说法 | 有根树 Hopf 代数里的说法 | 直觉解释 |
|---|---|---|
| TreeHeap 对象 | rooted tree | 一个带根的树对象 |
| compose / plus | product / grafting | 把树接到另一棵树上 |
| decompose | coproduct / admissible cuts | 按合法方式把树切开 |
| inverse-like / inverse_transpose | antipode | 类似“反向还原”的递归操作 |
| subheap | rooted subtree / pattern | 从树里取局部结构 |
| 非交换性 | non-commutative structure | 左右顺序、接入位置会改变结果 |
| primitive | primitive element | 不能再从乘积里拆出的基础生成元 |

所以，当我们在 `SPR-013` 里实验：

```text
noncomm_margin = 0.7117
```

它不是一个很孤立的发现。

它对应的是：

```text
树的嫁接、组合、路径顺序，本来就可以是非交换的。
```

也就是说：

```text
H1 plus H2
```

和：

```text
H2 plus H1
```

可以不是同一个东西。

这和整数加法不同。
但它和矩阵乘法、函数复合、树嫁接更接近。

## compose 与 decompose

TreeHeap 里最核心的一对操作是：

```text
compose:    children -> parent
decompose:  parent -> possible children
```

用公式写：

$$ \operatorname{compose}(H_1, H_2, \ldots, H_n) = H $$

意思是：

```text
多个子堆合成一个父堆。
```

反过来：

$$ \operatorname{decompose}(H) = \sum_c P_c(H) \otimes R_c(H) $$

这里的 \(c\) 可以理解成一次合法切割。

翻译成人话：

```text
一棵树不一定只有一种拆法。
每一种合法切法，都得到一部分被切下来的树，以及剩下的树。
```

这就是 Hopf 代数里 coproduct 的味道。

注意，这里有一个很重要的点：

```text
decompose 不是 compose 的唯一反函数。
```

也就是说：

```text
父结构 -> 子结构
```

通常不是唯一答案。

这正好对应我们一直说的：

```text
Probability Container
```

信息不足时，不要过早坍缩成一个答案。
应该保留多个候选分解。

## 为什么还需要 Operad

Hopf 代数解释了：

```text
树怎么合成、怎么切开、怎么反向递归。
```

但 TreeHeap 还有另一个核心：

```text
多个输入合成一个输出。
```

例如：

```text
cat + run       -> [cat run]
ball + foot     -> football
root + left + right -> subheap
```

这类结构正是 operad 擅长表达的。

Operad 的基本思想是：

```text
一个算子可以吃多个输入，吐出一个输出。
这些算子本身还可以继续组合。
```

可以参考：

- [Operads for compositional reasoning in LLMs, arXiv:2606.13634](https://arxiv.org/abs/2606.13634)

这篇论文把 operad 用到 LLM 的多步问题分解上。
它把复杂问题拆成子问题，再把子答案组合回来。

它的核心观点可以和 TreeHeap 对齐：

```text
问题分解树上的局部回答，必须和整体回答保持一致。
```

这和我们的 TreeHeap consistency 很像：

```text
soft TreeHeap 经过局部坍缩之后，
应该能回到合法的 hard TreeHeap。
```

## TreeHeap Operad 怎么定义

我们可以暂时这样定义一个 TreeHeap operad：

```text
T = TreeHeap operations
```

其中每个 operation 是：

```text
多棵子树 -> 一棵父树
```

数学上：

$$ \omega : (H_1, H_2, \ldots, H_n) \to H $$

其中 \(\omega\) 可以是：

```text
plus
compose
fold
merge
slot fill
kernel-guided write
```

如果一个模型能解释这些操作，我们就可以说它是：

```text
an algebra over the TreeHeap operad
```

翻译成人话：

```text
这个模型知道 TreeHeap 的算子该怎么作用到具体数据上。
```

这给了我们一个更正式的说法：

```text
可学习的 TreeHeap 模型
不是“一个 MLP 外面套树壳”。

它应该是 TreeHeap operad 上的一个 algebra。
```

## Kernel 在这里是什么

上一轮我们把 kernel 定义成：

```text
TreeHeap 上可重复滑动使用的局部推理算子。
```

现在可以把它放到 operad 语境里：

```text
kernel 是 TreeHeap operad 上的局部 algebra action。
```

不用被这个说法吓到。

它的意思很简单：

```text
kernel 不是凭空看一个向量。
它是在 TreeHeap 的局部子结构上执行一个算子。
```

例如一跳 kernel 看：

```text
S_i = root(i) -> [left(i), right(i)]
```

也就是：

$$ S_i = \big(A_i, A_{L(i)}, A_{R(i)}\big) $$

然后：

$$ K_\theta(q, S_i, W) \to y_i $$

其中：

| 符号 | 含义 |
|---|---|
| \(q\) | query，当前要查找或写入的目标 |
| \(S_i\) | 第 \(i\) 个局部子堆 |
| \(W\) | world model，也就是背景参考系 |
| \(\theta\) | kernel 的可学习参数 |
| \(y_i\) | 匹配、路由、写入或合并输出 |

输出不一定是硬答案。
更合理的是概率容器：

```text
{stop: 0.1, left: 0.8, right: 0.1}
{match: 0.7, no_match: 0.3}
{write_here: 0.6, write_elsewhere: 0.4}
```

这就是 TreeHeap 和 Probability Container 的接口。

## TreeHeap 操作本质上是卷积 kernel 的组合

这里需要补一层更重要的理解。

前面说：

```text
kernel 是 TreeHeap 上可重复滑动使用的局部推理算子。
```

但这句话还不够强。

更准确地说：

```text
TreeHeap 的多数操作，都应该被理解成卷积 kernel 的组合。
```

也就是说，TreeHeap 不是先有一个普通数组，然后偶尔拿 kernel 扫一下。

它更像是：

```text
一个高维结构空间
        +
一组可组合的局部卷积算子
```

### 为什么说 TreeHeap 至少是 3D 结构

普通一维序列只有：

```text
index -> value
```

二维矩阵有：

```text
(row, col) -> value
```

TreeHeap 至少同时有三类坐标：

```text
1. value:    节点里存的向量或符号
2. address:  节点的路径，比如 LLR、RLL
3. topology: 父子关系、子堆、祖先、兄弟节点
```

所以一个 TreeHeap 节点不只是：

```text
A[i]
```

而更像：

$$ H_i = \big(v_i, a_i, \tau_i\big) $$

其中：

| 符号 | 含义 |
|---|---|
| \(v_i\) | value，节点向量 |
| \(a_i\) | address/path，节点地址 |
| \(\tau_i\) | topology，局部拓扑关系 |

这就是我现在说的：

```text
TreeHeap 至少是 3D 的结构对象。
```

它不是简单的：

```text
一维数组 + 一点树形解释
```

而是：

```text
值空间 × 地址空间 × 拓扑空间
```

### 卷积 kernel 定义可能的局部操作

在 CNN 里，不同卷积核可以检测不同模式：

```text
横线
竖线
边缘
角点
纹理
```

在 TreeHeap 里，不同 kernel 也可以定义不同局部操作：

```text
查找 kernel:     这个子堆像不像 query？
路由 kernel:     下一步 stop / left / right？
写入 kernel:     信息应该写到哪个地址？
合并 kernel:     子堆能不能 fold 成父堆？
分解 kernel:     父堆有哪些可能切法？
对齐 kernel:     两个子堆是不是同构或近似同构？
翻转 kernel:     当前结构能不能镜像成另一侧结构？
```

因此，TreeHeap 的 `plus`、`compose`、`decompose`、`fold`、`match_subheap` 不应该被看成互不相关的函数。

更统一的看法是：

```text
它们都是不同 kernel 或 kernel composition 的结果。
```

写成抽象形式：

$$ \operatorname{Op}(H) = K_m \circ K_{m-1} \circ \cdots \circ K_1(H) $$

其中每个 \(K_j\) 都是一个局部 TreeHeap kernel。

### 共轭 kernel 与镜像翻转

Houming818 提到的“共轭操作”很重要。

如果 TreeHeap 的地址空间里有左右路径：

```text
L, R
```

那么镜像变换可以定义成：

```text
L <-> R
```

例如：

```text
LLR -> RRL
```

把这个路径镜像记为：

$$ \sigma(a) $$

对整棵 TreeHeap 的镜像可以写成：

$$ \sigma(H)_i = H_{\sigma(i)} $$

更直观地说：

```text
原树：
        root
       /    \
      A      B

镜像：
        root
       /    \
      B      A
```

那么一个 kernel \(K\) 的共轭 kernel 可以定义为：

$$ K^\sigma = \sigma^{-1} \circ K \circ \sigma $$

这句话翻译成人话：

```text
先把 TreeHeap 镜像过去；
在镜像空间里执行同一个 kernel；
再镜像回来。
```

如果这个等式成立，说明：

```text
TreeHeap kernel 可以在左右翻转后的结构上复用。
```

这和 CNN 里对称、旋转、平移相关的卷积思想很接近。

只不过 CNN 通常处理二维图像变换；
TreeHeap 处理的是：

```text
路径变换
子堆变换
拓扑变换
```

### 这对 TreeHeap 的意义

这件事给了我们一个更清楚的 claim：

```text
TreeHeap 的优势不只是“它是树”。
TreeHeap 的优势应该来自：

1. 高维结构坐标：value × address × topology
2. kernel 在这些坐标上的局部卷积
3. kernel composition 形成复杂推理
4. 共轭 kernel 允许镜像、翻转、对偶结构复用
```

如果这个方向成立，TreeHeap 的实验就不应该只测：

```text
能不能分类？
```

而应该测：

```text
同一个 kernel 能不能在不同路径上复用？
同一个 kernel 能不能在镜像结构上复用？
kernel composition 能不能形成多跳推理？
共轭 kernel 是否能减少训练样本？
```

这会成为后续 C05/C06 实验的重要设计点。

## query 从哪里来

前面公式里有 \(q\)，它不能凭空出现。

在 TreeHeap 管线里，\(q\) 可以来自三类地方：

```text
input token -> encoder -> q
当前上下文 -> context encoder -> q
上一层 kernel 输出 -> next query
```

更完整地写：

```text
token / phrase / task
        ↓
encoder
        ↓
q

context window / memory / world model
        ↓
context encoder
        ↓
W

q + W + local subheap
        ↓
TreeHeap kernel
        ↓
route / write / merge / collapse
```

所以 \(q\) 不是一个固定词向量。
它是当前推理任务发出的“查询意图”。

例如：

```text
q = 找 ball + foot 的组合
```

kernel 扫到：

```text
S_i = ball -> [foot, hand]
```

如果世界模型知道：

```text
ball + foot -> football
ball + hand -> basketball
```

那么 kernel 应该能给出：

```text
football 方向的高匹配
```

## kernel 的滑动与感受野

CNN 的卷积核会在图像上滑动。
TreeHeap kernel 也可以在树上滑动。

这里的滑动不是二维平移，而是：

```text
对所有内部节点 i，取它的局部子堆 S_i，然后执行 K(q, S_i, W)。
```

可以写成：

$$ \operatorname{ScoreMap}(H, q) = \{K_\theta(q, S_i, W) \mid i \in \operatorname{Internal}(H)\} $$

遍历顺序可以是 BFS、DFS，也可以并行。
数学上重点不是遍历顺序，而是：

```text
同一个 kernel 在不同地址复用。
```

这就是 TreeHeap 的结构归纳偏置。

### 一跳、二跳、k 跳

如果一跳 kernel 看：

```text
root + left + right
```

它的感受野是 3 个节点。

二跳 kernel 看：

```text
root
├── left subtree
└── right subtree
```

如果每个子树也看一跳，总共是：

```text
1 + 2 + 4 = 7 个节点
```

一般地，二叉树深度 \(k\) 的局部感受野大小是：

$$ 2^{k+1} - 1 $$

这解释了为什么 `SPR-021` 的实验只是一个起点。
它只测试了一跳子堆：

```text
root -> left, right
```

还没有测试多层 kernel 堆叠。

## kernel 的组合就是 operadic composition

CNN 可以多层堆叠：

```text
conv1 -> conv2 -> conv3
```

TreeHeap kernel 也可以堆叠：

```text
K1 看局部 3 节点
K2 看 K1 的输出和父层子堆
K3 再看更高层
```

写成公式：

$$ K_2 \circ K_1(q, S_i) = K_2\big(K_1(q, S_i), S_{\operatorname{parent}(i)}\big) $$

这就是 operad 语言里的组合：

```text
一个局部操作的输出，
可以成为另一个局部操作的输入。
```

所以 TreeHeap kernel 不是一个孤立分类器。
它应该是一组可组合的局部算子。

## 为什么线性 kernel 不够

GLM 的多 pattern 消融指出了一个关键问题：

```text
线性 kernel 不会真正比较 query 和 patch。
```

如果 kernel 是：

$$ K(q, S) = w^\top [q, S] + b $$

它只能分别给 \(q\) 和 \(S\) 加权求和。

它天然不会形成：

$$ q - S $$

更不会自然形成：

$$ \lVert q - S\rVert^2 $$

除非我们手工把这些差分特征喂进去。

所以，如果任务要求：

```text
判断这个子堆是不是和 query 匹配
```

那么纯线性 kernel 通常不够。

更合理的是：

$$ K_\theta(q, S, W) = \operatorname{MLP}_\theta([q, \phi(S), W]) $$

或者显式给出交互项：

$$ K(q, S) = -\lVert q - \phi(S)\rVert^2 $$

这里 \(\phi(S)\) 是子堆编码。

这不是实现小细节。
这是数学约束：

```text
结构比较需要交互项。
没有交互项，kernel 很容易退化成地址分类器。
```

## Attention 对比

Transformer attention 也可以看成一种 kernel：

$$ \operatorname{score}(i,j) = Q_i K_j^\top $$

它的特点是：

```text
flat
all-to-all
通过点积比较 token
```

TreeHeap kernel 的特点是：

```text
structural
local subheap
path-aware
可递归堆叠
可以输出概率容器
```

对比一下：

| 项目 | Transformer Attention | TreeHeap Kernel |
|---|---|---|
| 基本对象 | token 序列 | 有根树 / 堆 |
| 比较单位 | token-token | query-subheap |
| 连接方式 | 全连接 | 局部结构滑动 |
| 地址 | 位置编码 | 路径 / 子堆地址 |
| 归纳偏置 | 序列与全局相关性 | 子结构迁移与递归组合 |
| 输出 | attention weights | route/write/merge/collapse 容器 |

所以 TreeHeap 不是要说：

```text
attention 错了。
```

更准确的说法是：

```text
TreeHeap kernel 想给 attention 缺少的树形地址、子结构复用、延迟坍缩提供结构约束。
```

## 与传统 Tree Kernel 的关系

NLP 里早就有 tree kernel。

经典方向包括 Collins-Duffy tree kernel、Moschitti 的 syntactic tree kernel。
它们常用于 SVM 或句法树分类。

它们大致做的是：

```text
两棵句法树之间有多少公共子树？
公共子树越多，相似度越高。
```

TreeHeap kernel 和它们有亲缘关系，但不是同一个东西。

| 项目 | 传统 tree kernel | TreeHeap kernel |
|---|---|---|
| 主要用途 | 树相似度 / 分类 | 路由、写入、合并、坍缩 |
| 是否可学习 | 多数是固定相似度 | 可以固定，也可以可学习 |
| 数据结构 | 句法树 | 可寻址 TreeHeap |
| 输出 | similarity score | probability container / action |
| 是否改写结构 | 通常不写入 | 可以指导 soft plus 写入 |

所以我们不是第一个想到“树上 kernel”的项目。
真正的新问题是：

```text
能不能把 tree kernel 从固定相似度函数，
推进成可微、可写入、可组合的 TreeHeap 局部推理算子？
```

## Morphosyntax 与语言结构

TreeHeap 最终要回到语言任务。
这里也已经有相关数学方向。

例如：

- [The Algebraic Structure of Morphosyntax, arXiv:2507.00244](https://arxiv.org/abs/2507.00244)

这类工作把词法、句法的树结构放到 operad / algebra 的框架里讨论。

对我们来说，它至少说明一件事：

```text
用 operad 描述语言结构组合，不是离谱方向。
```

但是我们必须谨慎：

```text
这不等于 TreeHeap 已经能做 WMT。
```

它只是说明：

```text
语言结构上层可以站在代数结构底座上。
```

中间还缺：

```text
真实语料 encoder
真实句法 micro benchmark
S1b baseline battle
S2 graph assembly
S3 generation
```

## Decomposition Space 与概率容器

还有一个相关方向是 decomposition space：

- [Decomposition spaces in Combinatorics, arXiv:1612.09225](https://arxiv.org/abs/1612.09225)

它关心的是：

```text
组合与分解如何形成一致的数学结构。
```

这对 TreeHeap 的启发是：

```text
如果 decompose 有多个合法结果，
那么模型不应该立刻 argmax。
```

它应该保留：

```text
Parent candidates
Route candidates
Graph candidates
Decomposition candidates
```

也就是：

```text
Probability Container
```

这能把 TreeHeap 的设计从：

```text
每一步强行选一个答案
```

推进到：

```text
信息不足时保留多个合法分解，
等更强上下文再坍缩。
```

这和我们最早的 L0/L1/L2 叠加态想法是一致的。

## 这篇文章修正了什么

它修正了一个重要叙述：

```text
TreeHeap 不应该被说成“我们发明了一套全新的数学”。
```

更专业、更可靠的说法是：

```text
TreeHeap 是把 rooted-tree Hopf algebra、operad、tree kernel、
probabilistic soft lifting 这些思想，工程化到可学习结构内存中的尝试。
```

这让项目更稳。

因为我们不需要自己证明所有基础性质。
很多东西已有成熟数学支持：

```text
树可以组合。
树可以切割。
多输入单输出算子可以组合。
局部树模式可以匹配。
结构分解可以不是唯一的。
```

我们真正要证明的是工程问题：

```text
这些数学对象能不能变成有效的机器学习结构？
能不能比 flat MLP / 普通 Transformer 在某些任务上更省样本、更稳外推、更低计算？
```

## 当前 Claim 应该怎么更新

我建议把核心 claim 重新表述成：

```text
Claim:
TreeHeap 的数学底座可以由 rooted-tree Hopf algebra 与 operad 承接。
因此 compose/decompose/plus/subheap/kernel 不需要作为孤立发明来理解。
真正需要实验验证的是：
可学习 kernel 是否能利用这个结构底座，获得 flat 模型没有的归纳偏置。
```

对应 predict：

```text
Predict:
在需要地址、子结构迁移、前缀复用、延迟坍缩的问题上，
TreeHeap kernel 应该比 flat MLP 更少样本、更稳 OOD 外推。
```

对应 falsification：

```text
如果足够宽的 flat MLP / 普通 Transformer，
在相同参数量、相同训练数据下，
稳定匹配 TreeHeap kernel 的 OOD 地址外推、子结构迁移和延迟坍缩能力，
那么 TreeHeap kernel 没有显示出额外归纳偏置。
```

这很重要。

TreeHeap 不能靠“看起来更优美”成立。
它必须靠：

```text
更明确的数学对象
更清楚的可证伪预测
更干净的对照实验
```

成立。

## 下一步怎么接实验

这篇文章之后，我不建议继续只做纯文字推理。

下一步应该接两个实验。

### 实验 1：非线性 kernel 是否能学会 query-subheap 比较

目标：

```text
不用手工 diff 特征。
只给 raw query 和 raw subheap。
看 MLP kernel 能不能学会比较。
```

对照：

```text
linear_raw
mlp_raw
linear_with_diff
treeheap_kernel
```

如果结果是：

```text
linear_raw 失败
mlp_raw 成功
```

说明：

```text
kernel 的非线性交互是必要的。
```

### 实验 2：真实小句法树 micro benchmark

目标：

```text
不要直接跳 WMT BLEU。
先拿 100 到 1000 句真实句法树，
测试 TreeHeap kernel 能否迁移局部依存结构。
```

例如：

```text
head -> subject/object/modifier
```

不是先证明翻译质量，而是先证明：

```text
TreeHeap kernel 在真实语言树上确实能读到结构信号。
```

这才是从 M0 到 S1/S2 的桥。

## 最终结论

这篇的结论很简单：

```text
TreeHeap 的数学底座并不孤单。
它可以站在 rooted-tree Hopf algebra、operad、decomposition space 和 tree kernel 的已有传统上。
```

但这不是胜利宣言。

它只是把问题从：

```text
我们是不是在乱造数学？
```

推进到：

```text
我们能不能把这些成熟数学对象，训练成有效机器学习系统？
```

这一步反而更严格。

因为以后我们不能只说：

```text
TreeHeap 很像树，很像代数。
```

我们必须证明：

```text
TreeHeap kernel 在具体任务上，利用了树的地址、路径、子结构、组合和分解。
并且这种利用带来了可测量的收益。
```

这就是下一阶段实验的方向。
