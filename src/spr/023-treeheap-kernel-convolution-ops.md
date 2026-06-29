---
title: "[SPR-023] 从卷积核重新定义 TreeHeap 操作"
date: 2026-06-24
weight: 23
author: nio (Houming818) & Codex Review
description: "把 plus、search、conjugate 统一为 TreeHeap kernel 在树形内存态上的卷积状态变换，并用 toy proof 验证 score map、write field 与镜像共轭。"
tags: [SPR, TreeHeap, ARA, Kernel, Convolution, Experiment]
---

# 从卷积核重新定义 TreeHeap 操作

上一篇 `SPR-022` 把 TreeHeap 放回了已有数学背景：

```text
rooted-tree Hopf algebra
operad
decomposition space
tree kernel
```

但 Houming818 指出了一个更核心的问题：

```text
TreeHeap 的操作不应该先被理解成一堆手写函数。
TreeHeap 的核心操作应该是 kernel 在树上的卷积。
```

这句话把方向拉正了。

以前容易说成：

```text
TreeHeap 有 plus、compose、decompose、conjugate。
另外，我们再给它加一个 kernel。
```

现在应该反过来：

```text
TreeHeap 的 plus、search、compose、decompose、fold、conjugate，
都应该从 kernel 如何卷积整棵树并更新内存态来定义。
```

也就是说：

```text
TreeHeap 不是“树结构 + 一堆函数”。
TreeHeap 是“树形高维状态场 + 一组卷积核”。
```

## 先看 CNN 的类比

在 CNN 里，一张图像是一个状态场：

```text
image[row, col, channel]
```

卷积核扫过图像：

```text
3x3 patch
↓
kernel
↓
feature score
```

整张图扫完以后得到：

```text
feature map
```

例如一个边缘检测 kernel，不是在一个像素上做判断，而是在整张图上滑动，生成一张“哪里像边缘”的图。

TreeHeap 应该类似。

TreeHeap 的状态场不是二维图像，而是：

```text
value × address × topology
```

也就是：

```text
节点值
路径地址
父子拓扑
```

所以 TreeHeap kernel 不是看一个孤立节点。
它看一个局部子堆：

```text
      root
     /    \
  left    right
```

然后在整棵树上滑动。

## TreeHeap kernel convolution 的定义

设当前 TreeHeap 内存态是：

$$ H_t $$

以路径 \(a\) 为中心的局部子堆是：

$$ S_a(H_t) $$

一个 kernel 是：

$$ K_\theta(q, S_a, W) $$

其中：

| 符号 | 含义 |
|---|---|
| \(q\) | query，要找或要写的目标 |
| \(S_a\) | 地址 \(a\) 处的局部子堆 |
| \(W\) | world model / 背景场 |
| \(\theta\) | kernel 参数，可以固定，也可以学习 |

卷积整棵树就是：

$$ \operatorname{Conv}_K(H_t, q) = \{K_\theta(q, S_a(H_t), W)\}_{a \in A(H_t)} $$

翻译成人话：

```text
对树上每个候选地址 a：
  取局部子堆 S_a
  用同一个 kernel 计算响应
最终得到一张覆盖整棵树的响应图
```

这张响应图可以叫：

```text
score map
update map
route map
probability field
```

不同名字对应不同用途，但本质都是：

```text
kernel 扫树以后得到的全局状态场。
```

## plus 不再是“写到某个地址”

以前我们容易把 plus 理解成：

```text
H plus x = 把 x 写到地址 a
```

但这太像普通数组写入了。

新的定义应该是：

```text
plus kernel 扫描整棵 TreeHeap。
每个地址都产生一个 write score。
这些 score 形成一个写入概率场。
然后 H 根据这个概率场更新。
```

数学上：

$$ s_a = K_{\text{plus}}(x, S_a(H_t), W) $$

$$ p_a = \operatorname{softmax}(s_a) $$

$$ H_{t+1} = H_t + \sum_a p_a \cdot \Delta_a(x, H_t) $$

其中：

```text
s_a = 地址 a 的写入响应
p_a = 地址 a 的写入概率
Δ_a = 如果写到地址 a，会产生的局部状态更新
```

所以 plus 的本质不是：

```text
直接指定地址。
```

而是：

```text
kernel 卷积整棵树，形成 write field，再更新内存态。
```

## search 也是同一个东西

search 更直观。

定义：

$$ s_a = K_{\text{search}}(q, S_a(H_t), W) $$

如果只要硬搜索结果：

$$ a^* = \arg\max_a s_a $$

如果要概率容器：

$$ p_a = \operatorname{softmax}(s_a) $$

所以 search 不是特殊函数。

它就是：

```text
kernel 卷积树，输出 score map。
```

plus 和 search 的差别只是：

```text
search 把 score map 用来读。
plus 把 score map 用来写。
```

## conjugate 不是额外 if-else

共轭操作也应该从 kernel 角度定义。

假设镜像变换是：

```text
L <-> R
```

例如：

```text
LRL -> RLR
```

记为：

$$ \sigma(a) $$

那么 kernel 的共轭是：

$$ K^\sigma = \sigma^{-1} \circ K \circ \sigma $$

这句话的意思是：

```text
先把 TreeHeap 镜像过去；
在镜像空间里用 kernel 做卷积；
再把响应映射回来。
```

所以 conjugate 不是：

```text
如果左边怎样，右边就怎样。
```

它是：

```text
卷积核本身做了一次对称翻转。
```

这就像图像里一个检测左斜边缘的 kernel，可以通过翻转变成检测右斜边缘的 kernel。

TreeHeap 里对应的是：

```text
左路径结构
↓ 镜像
右路径结构
```

## 这次 ARA 的新 claim

这次新增：

```text
M0-SOFT-C08
```

Claim：

```text
TreeHeap primitive operations can be defined as kernel convolutions over
the whole tree state:

search emits a score map,
plus/write uses that map as an update field,
and conjugate is a symmetry transform of the kernel.
```

中文解释：

```text
TreeHeap 的基本操作可以统一成：
kernel 在整棵树上卷积，然后产生状态图。

search 用这张图读；
plus 用这张图写；
conjugate 是对 kernel 做镜像变换。
```

这不是说语言任务已经解决。
它只是先把操作语义统一起来。

## Toy proof 怎么设计

我们做了一个小实验：

```text
kernel_convolution_ops_probe.py
```

构造一棵 full binary TreeHeap。

在目标地址放入一个不对称子堆：

```text
target_path = LRL

query = [root, left, right]
      = [2.0, 5.0, -3.0]
```

局部子堆是：

```text
patch(a) = [H[a], H[aL], H[aR]]
```

kernel 定义为：

$$ score(a) = -\lVert patch(a) - query\rVert^2 $$

这个 kernel 很朴素。
它不是学习出来的。
它只是为了测试：

```text
同一个卷积响应图，能不能解释 search / plus / conjugate。
```

## 实验 1：search score map

kernel 扫描所有候选子堆。

输出：

```text
score(path)
```

然后取：

```text
argmax score(path)
```

结果：

| 指标 | 结果 |
|---|---:|
| search hit@1 | True |
| hit path | LRL |
| target probability | 1.0 |

说明：

```text
search 可以被定义成 kernel 卷积后的 score map。
```

## 实验 2：plus write field

同一张 score map 不只可以拿来读。

也可以变成写入概率：

$$ p(a)=\operatorname{softmax}(score(a)) $$

然后更新 TreeHeap：

$$ H_{t+1} = H_t + \sum_a p(a)\cdot write(a) $$

结果：

| 指标 | 结果 |
|---|---:|
| plus write hit@1 | True |
| write path | LRL |
| target update error | 0.000000 |
| max disjoint non-target update norm | 0.000000 |

这里有一个细节。

`max_nontarget_update_norm = 0.75`，看起来像有非目标节点被影响。

但原因是 TreeHeap 的子堆会重叠。
例如一个父 patch 会包含它的子节点。
目标子堆被写入以后，和它共享节点的其它 patch 也会观察到变化。

所以更干净的定位指标是：

```text
max_disjoint_nontarget_update_norm = 0.0
```

意思是：

```text
不共享节点的非目标子堆没有被写乱。
```

这说明 plus/write 可以被解释成：

```text
kernel 卷积产生 write field，然后写入 TreeHeap 内存态。
```

## 实验 3：conjugate mirror

目标路径：

```text
LRL
```

镜像以后：

```text
RLR
```

原始 query 是不对称的：

```text
[2.0, 5.0, -3.0]
```

如果直接拿原 kernel 去扫镜像树，会失败：

| 指标 | 结果 |
|---|---:|
| raw mirror hit@1 | False |
| raw mirror hit path | RLLR |

但如果使用共轭 kernel：

```text
K^sigma = sigma^-1 K sigma
```

结果：

| 指标 | 结果 |
|---|---:|
| conjugate mirror hit@1 | True |
| conjugate hit path | RLR |
| score-map equiv max error | 0.000000e+00 |

这说明：

```text
共轭不是树外的 if-else。
共轭是 kernel 的对称变换。
```

也说明 TreeHeap 的镜像能力可以从卷积核角度定义。

## 实验总表

| 检查项 | 结果 |
|---|---:|
| pilot_pass | True |
| search hit@1 | True |
| plus write hit@1 | True |
| target update error | 0.000000 |
| max disjoint non-target update norm | 0.000000 |
| raw mirror hit@1 | False |
| conjugate mirror hit@1 | True |
| score-map equiv max error | 0.000000e+00 |

证据路径：

```text
ara/m0-treeheap-math/src/kernel_convolution_ops_probe.py
ara/m0-treeheap-math/evidence/kernel_convolution_ops_probe/
```

## 这个 proof 证明了什么

它证明了一个很小、但很关键的东西：

```text
search、plus/write、conjugate 可以共享同一种 kernel convolution 语义。
```

也就是：

```text
kernel 扫树
↓
产生 score/update map
↓
读、写、镜像都从这张 map 或它的对称变换产生
```

这让 TreeHeap 操作不再是一堆散装函数。

它们开始有一个统一形式：

$$ H_{t+1} = \operatorname{Op}_K(H_t) $$

其中：

$$ \operatorname{Op}_K $$

来自 kernel 在树上的卷积。

## 这个 proof 没证明什么

它没有证明：

```text
kernel 可以自己学出来。
```

这次 kernel 是固定的：

$$ score(a) = -\lVert patch(a)-query\rVert^2 $$

它也没有证明：

```text
TreeHeap 可以翻译。
TreeHeap 可以理解语言。
TreeHeap 比 Transformer 强。
```

这些都还不能说。

它只证明：

```text
从操作定义上，TreeHeap 可以把 search、plus/write、conjugate
统一为 kernel convolution。
```

这个地基比“我们手写了几个函数”更干净。

## GLM 审计后的修订

Runner / GLM 复核以后指出了一个非常重要的边界：

```text
C08 的 conjugate proof 是 by construction 的恒等。
```

这句话是什么意思？

在代码里，我们定义了两个东西：

```text
mirror_tree:
  把路径 L/R 互换。

mirror_patch:
  把局部子堆的 left/right 互换。
```

于是对于原始路径 \(p\)，有：

$$ \operatorname{mirror\_patch} \big( \operatorname{patch}(\operatorname{mirror\_tree}(H), \sigma(p)) \big) = \operatorname{patch}(H,p) $$

所以：

$$ score_{\text{conjugate}}(\sigma(p)) = score_{\text{original}}(p) $$

这不是模型“自己发现了镜像规律”。

这是我们按共轭定义写出来以后，数学上必然成立。

因此，`score_map_equiv_max_error = 0.0` 的意义不是：

```text
TreeHeap 学会了镜像。
```

而是：

```text
如果我们把 conjugate 定义成 kernel 的对称变换，
那么 TreeHeap 的镜像 score map 可以保持一致。
```

这依然有价值。

但它的价值是：

```text
操作语义统一。
```

不是：

```text
学习能力证明。
```

所以 `M0-SOFT-C08` 的精确边界应该写成：

```text
C08 支持的是 operator-semantics pilot。
它证明 search / plus / conjugate 可以被统一写成 kernel convolution。
它不证明 learned kernel，也不证明模型会自动学出共轭对称。
```

这个修订非常重要。

否则我们会把“定义上成立”误读成“实验上发现”。

## 下一步 Predict

下一步不能继续证明 fixed kernel。

fixed kernel 的作用已经完成：

```text
说明 TreeHeap 操作可以被统一定义为 kernel convolution。
```

下一步要证明的是：

```text
这个 kernel 能不能从数据中学出来？
```

所以我建议新增两个 predict。

### P-SOFT05：learned convolution kernel

Predict：

```text
如果 TreeHeap kernel 的核心是卷积状态变换，
那么一个非线性 learned kernel 应该能从 raw query + raw subheap 中
学会产生正确的 score map 和 write field。
```

注意关键词是：

```text
raw query
raw subheap
```

也就是说，不能再手工喂：

```text
diff = patch - query
abs(diff)
diff^2
root_alignment
child_alignment
```

这些都是答案提示。

真正的 learned kernel 应该输入：

```text
query_root, query_left, query_right
patch_root, patch_left, patch_right
path metadata
```

然后自己学出：

```text
query 和 patch 是否匹配。
```

### P-SYNTAX01：真实句法树 micro benchmark

Predict：

```text
如果 TreeHeap kernel 不是只在 toy 树上成立，
那么它应该能在小规模真实句法树上读到局部依存结构信号。
```

这不是 WMT BLEU。

这是一个桥梁实验。

目标是：

```text
让真实语言数据第一次进入 M0/S1 的 TreeHeap kernel 证据链。
```

建议数据：

```text
Universal Dependencies 小型子集
100 到 1000 句
```

任务：

```text
给定一个 head token 的局部 TreeHeap 子结构，
预测或匹配它的 modifier / dependent pattern。
```

例如：

```text
head -> left dependent / right dependent
verb -> subject / object / modifier
noun -> determiner / adjective / prepositional phrase
```

这个实验不要求翻译。

它只问：

```text
TreeHeap kernel 在真实句法树上是否比 flat baseline 更会利用局部树结构？
```

## 下一步实验设计

下一步不是继续手写 kernel。

下一步应该问：

```text
这个 kernel 能不能被学习出来？
```

也就是：

```text
raw query + raw subheap
↓
learned kernel
↓
score map / write field / conjugate transfer
```

建议下一步做：

```text
P-SOFT05: learned convolution kernel
```

对照：

```text
fixed kernel
linear raw kernel
MLP raw kernel
TreeHeap convolution kernel
```

目标：

```text
不用手工 diff。
让模型自己学会 query-subheap 比较。
```

如果 learned kernel 能做到：

```text
search map 正确
write field 正确
mirror conjugate 可迁移
```

那我们才可以把 C05 往前推进。

### 实验 A：learned multi-pattern kernel

数据生成：

```text
每个样本随机生成一个 query pattern。
把这个 pattern 注入 TreeHeap 的某个目标子堆。
模型必须在所有候选子堆里找出目标位置。
```

关键点：

```text
不是固定 query。
必须是 multi-pattern。
```

因为固定 query 很容易退化成：

```text
记住某一个模式。
```

多 pattern 才能测试：

```text
kernel 是否真的学会比较 query 和 patch。
```

对照组：

| 模型 | 输入 | 预期 |
|---|---|---|
| fixed distance kernel | 手写 \( -\lVert patch-query\rVert^2 \) | 上限参考，不算学习 |
| linear raw kernel | raw query + raw patch | 应该失败或较弱 |
| MLP raw kernel | raw query + raw patch | 应该明显强于 linear |
| TreeHeap convolution kernel | raw query + raw patch + path/topology | 应该在 OOD 地址上最好 |

Evidence gates：

```text
E-SOFT14:
  MLP raw kernel > linear raw kernel

E-SOFT15:
  TreeHeap convolution kernel 在 unseen depth / unseen address 上
  优于 flat MLP baseline

E-SOFT16:
  不使用 hand-coded diff / alignment 特征
```

Falsification：

```text
如果 linear raw 或 flat MLP 在同样数据量下稳定匹配 TreeHeap kernel，
那么 TreeHeap kernel 没有显示额外结构收益。
```

### 实验 B：learned conjugate transfer

GLM 已经指出：

```text
当前 conjugate proof 是 by construction。
```

所以真正要测的是：

```text
learned kernel 是否能在镜像结构上迁移。
```

设计：

```text
训练集：
  只出现左侧结构，比如 L 开头路径。

测试集：
  只出现镜像右侧结构，比如 R 开头路径。
```

比较：

```text
raw learned kernel
explicit conjugate kernel
data augmentation baseline
flat MLP baseline
```

Evidence gates：

```text
E-SOFT17:
  explicit conjugate kernel 在 mirror OOD 上优于普通 learned kernel

E-SOFT18:
  使用更少右侧样本达到同等准确率

E-SOFT19:
  mirror score map 在 learned setting 下误差受控
```

Falsification：

```text
如果普通 MLP 通过足够少样本就学到同等镜像迁移，
或者 explicit conjugate kernel 没有 sample efficiency 优势，
那么共轭 kernel 不构成有效归纳偏置。
```

### 实验 C：真实句法树 micro benchmark

数据：

```text
Universal Dependencies
先取 100 到 1000 句
只做英文或中文单语
```

构造：

```text
把 dependency tree 转成 TreeHeap-like 局部子结构。
每个候选 patch 包含：
  head token embedding / id
  left dependent
  right dependent
  dependency label 或无监督 slot
  path/topology metadata
```

任务：

```text
给定 query，找出正确 head-dependent 子结构。
或给定局部子树，预测 masked dependent / role。
```

对照组：

```text
BoW / token-only baseline
flat MLP
small Transformer encoder
TreeHeap convolution kernel
```

Evidence gates：

```text
E-SYNTAX01:
  TreeHeap kernel > token-only baseline

E-SYNTAX02:
  TreeHeap kernel 在 OOD dependency pattern 上比 flat MLP 更稳

E-SYNTAX03:
  去掉 path/topology/subheap 后性能明显下降
```

Falsification：

```text
如果 token-only 或 flat MLP 在真实句法树 micro benchmark 上匹配 TreeHeap kernel，
则 TreeHeap 结构对真实语言局部结构没有显示额外收益。
```

## ARA 补项

GLM 还指出了两个 ARA 文档层面的缺口。

第一，`PAPER.md` 里还没有把 `SPR-022`、`SPR-023` 和 `M0-SOFT-C08` 注册到总 claim 树。

第二，`exploration_tree.yaml` 里还没有把最近三步补进去：

```text
C07 structural proof
C08 kernel convolution proof
P-SOFT05 learned kernel pivot
```

这些不是实验本身的问题。

它们是 ARA 索引问题。

我建议下一次 ARA 修订补：

```text
C5-009:
  SPR-022 数学底座：
  TreeHeap math foundations map to BCK Hopf algebra + operad.

C5-010:
  SPR-023 kernel convolution：
  TreeHeap primitive ops can be defined as kernel convolutions over tree state.
```

同时在 trace DAG 中补：

```text
E-SOFT-002:
  structural_c05_probe

E-SOFT-003:
  kernel_convolution_ops_probe

D-SOFT-003:
  operator semantics unified by kernel convolution

P-SOFT-005:
  learned convolution kernel
```

这一步我先不直接改。
原因是：

```text
这篇 blog 先给 Houming818 review 下一步实验方向。
等 review 后，再把 PAPER.md 和 trace DAG 一次性修正。
```

## 结论

这篇的结论是一句话：

```text
TreeHeap 的操作本体应该是 kernel convolution。
```

不是：

```text
树上有一个 kernel。
```

而是：

```text
kernel 扫树，产生状态场；
状态场再解释为 search、plus、write、fold、conjugate。
```

这把 TreeHeap 从“树形数据结构”推进到了：

```text
树形高维状态场上的卷积计算系统。
```

这才是下一阶段要训练、要证明、要和 MLP / Transformer 对照的对象。
