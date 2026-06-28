---
title: "[SPR-020] Soft TreeHeap 审计：proof 证明了什么，没证明什么"
date: 2026-06-23
weight: 20
author: nio (Houming818) & Codex Review
description: "根据 GLM/Runner 的复现实验修订 ARA：区分梯度可达、toy 坍缩、clean kernel 学习三件不同的事，并说明下一步实验。"
tags: [SPR, TreeHeap, ARA, SoftTreeHeap, Audit]
---

# Soft TreeHeap 审计：proof 证明了什么，没证明什么

上一篇 `SPR-019` 讲了一个关键设计：

```text
Hard TreeHeap 是离散树堆。
Soft TreeHeap 是它的概率提升。
```

也就是说，原来 hard 操作是：

$$
H_{\text{next}} = H \oplus_a x
$$

意思是：

```text
把 x 按 TreeHeap plus 的规则写到地址 a。
```

Soft 以后变成：

$$
H_{\text{next}} = \sum_a p(a \mid H, x) \cdot (H \oplus_a x)
$$

翻译成人话：

```text
模型暂时不知道 x 应该写到哪个地址。
所以它先对多个地址都生成候选结果，
再按照概率 p(a) 混合这些候选结果。
```

如果训练到最后：

$$
p(LL)=1.0,\quad p(\text{other})=0.0
$$

那么 Soft TreeHeap 就坍缩回 hard 操作：

$$
H_{\text{next}} = H \oplus_{LL} x
$$

这个设计是为了让梯度进入 TreeHeap。

但 GLM/Runner 复现实验后指出了一个很重要的问题：

```text
当前 proof 确实证明了梯度能流动，
也证明了当前 toy 能坍缩到正确地址。

但它还没有证明：
kernel 能从干净的 TreeHeap 子结构里自己学会路由。
```

这篇文章就是把这个边界讲清楚。

## 三件事不要混在一起

我们现在有三件很像、但其实不同的事。

第一件：

```text
梯度能不能进入 TreeHeap？
```

这是 `M0-SOFT-C03`。

如果 loss 算完以后：

```text
d loss / d K_write != 0
d loss / d Plus_a  != 0
```

说明梯度确实能更新写入 kernel 和 plus 参数。

第二件：

```text
当前 toy 能不能坍缩到正确 hard 地址？
```

这是 `M0-SOFT-C04`。

如果低温 softmax 后：

```text
argmax p(a) = gold_address
```

而且准确率是 1.0，说明当前 toy 在当前特征下能坍缩。

第三件：

```text
kernel 能不能不靠人工提示，
从 TreeHeap 子结构里自己学会路由？
```

这是更强的 `M0-SOFT-C05 / P-SOFT02`。

这还没有证明。

这三件事的关系像这样：

```text
梯度能流
  ↓
当前 toy 能坍缩
  ↓
干净 kernel 能自己学路由
  ↓
TreeHeap 写入机制比普通神经内存更好
```

我们现在只走完了前两步。

## 这些 Claim 编号到底是什么意思

`M0-SOFT-C03` 这种编号看起来像内部黑话，其实可以拆开看：

```text
M0        = Math layer 0，也就是 TreeHeap 的数学地基
SOFT      = Soft TreeHeap，也就是可微概率版本
C03 / C04 = 第 3 / 第 4 条 claim
```

这里的 claim 不是口号，而是一个可以被实验检查的小命题。

### M0-SOFT-C03：梯度可达

白话说：

```text
loss 算出来以后，能不能真的改到 TreeHeap 的写入 kernel 和 plus 参数？
```

数学上就是看：

$$
\left\lVert\frac{\partial L}{\partial K_{\text{write}}}\right\rVert > 0
$$

以及：

$$
\left\lVert\frac{\partial L}{\partial \text{Plus}}\right\rVert > 0
$$

类比线性回归：

```text
线性回归里，如果 dL/dW = 0，
W 就不会被训练数据改变。

TreeHeap 里，如果 dL/dK_write = 0，
写入 kernel 就不会被训练数据改变。
```

所以 C03 证明的是：

```text
TreeHeap 的这些参数不是死的。
训练信号能碰到它们。
```

它还没有证明：

```text
这些参数已经学会了好的结构。
```

### M0-SOFT-C04：低温坍缩能回到 hard 地址

白话说：

```text
Soft TreeHeap 训练时可以保留多个可能地址，
但最后能不能收敛成一个明确的 hard 地址？
```

例如一开始模型可能这样想：

```text
LL: 0.25
LR: 0.25
RL: 0.25
RR: 0.25
```

训练后变成：

```text
LL: 0.98
LR: 0.01
RL: 0.005
RR: 0.005
```

低温 softmax 或 argmax 后，就可以坍缩成：

```text
LL
```

这就是 C04。

类比一下：

```text
考试早期，学生在四个选项里摇摆。
训练后，学生几乎确定选 A。
最终交卷时，只能填一个答案。
```

C04 证明的是：

```text
Soft 的概率状态可以变回 Hard 的离散结构。
```

这很重要。因为如果 Soft TreeHeap 永远只是一团概率雾，它就不能回到我们前面建立的 hard TreeHeap 数学地基。

### M0-SOFT-C05：TreeHeap kernel 是否真的更好

C05 比 C03/C04 强很多。

它问的是：

```text
用 TreeHeap 子结构 kernel 来决定写入位置，
是否比普通神经内存写入更好？
```

这才接近 TreeHeap 的存在性问题。

如果 C05 成立，说明 TreeHeap 不是只是“也能训练”，而是：

```text
在需要地址、子结构迁移、路径复用、延迟坍缩的问题上，
TreeHeap 的结构 bias 可能真的有优势。
```

如果 C05 不成立，那也很重要：

```text
说明当前 TreeHeap 写入设计可能只是复杂包装，
普通 MLP / neural memory 已经够用了。
```

## 当前 proof 做了什么

`soft_plus_probe.py` 用了一个很小的地址集合：

```text
LL, LR, RL, RR
```

你可以把它想成一棵深度为 2 的小树：

```text
        root
       /    \
      L      R
     / \    / \
   LL  LR  RL  RR
```

输入一些 key：

```text
2, 3   -> LL
5, 6   -> LR
10, 11 -> RL
13, 14 -> RR
```

模型要学会：

```text
给定 key，选择正确地址。
```

然后用 Soft Plus 生成：

$$
H_{\text{next}}
=
\sum_a p(a) \cdot \text{Plus}_a(H, key)
$$

loss 会比较：

```text
H_next
```

和目标 TreeHeap。

如果 loss 下降，并且梯度能传到：

```text
K_write
Plus_a
```

就说明 Soft Plus 的训练链路是通的。

当前结果是：

```text
pilot_pass = true
initial_loss = 0.677455
final_loss   = 0.000774
dL/dK_write  = 0.0902425
dL/dPlus     = 0.143869
collapse_accuracy_tau_0.05 = 1.0
```

这说明：

```text
loss 明显下降；
梯度不是 0；
低温坍缩能选中正确地址。
```

所以 C03/C04 是成立的。

但要注意：

```text
成立范围是这个 synthetic toy。
```

不是语言任务。

不是 WMT。

不是 Transformer 替代。

## GLM 的审计发现

GLM/Runner 做了两类复现。

第一类是多 seed 复现：

| Seed | pilot_pass | collapse_acc |
|---:|---|---:|
| 42 | true | 1.0 |
| 7 | true | 1.0 |
| 123 | true | 1.0 |
| 999 | true | 1.0 |

这说明 proof 不是一次随机运气。

第二类是 ablation，也就是把某些设计拿掉，看结果会不会坏。

最重要的结果是：

| 特征集合 | collapse_acc | 说明 |
|---|---:|---|
| 当前完整特征 | 1.000 | proof 通过 |
| 去掉 alignment/sum 特征 | 0.625 | 明显退化 |
| raw/basic 8D 特征 | 0.250 | 接近随机 |
| 随机投影 + side flags | 0.250 | 接近随机 |

这里的 `0.250` 很好理解。

因为地址有 4 个：

```text
LL, LR, RL, RR
```

随机猜一个，准确率就是：

```text
1 / 4 = 0.25
```

所以 raw/basic 特征下的模型基本没学会路由。

## 问题出在哪里

当前 kernel features 里有两个很强的人工提示：

```python
root_alignment = root_diff * root_side
child_alignment = diff * child_side
```

这两个公式确实容易看懵。我们拆开讲。

假设当前 toy 是一棵二叉搜索树。为了判断一个 key 应该往左还是往右，最原始的信息应该是：

```text
key 是多少？
root key 是多少？
left child key 是多少？
right child key 是多少？
```

模型应该自己从这些数里学出：

```text
key < root_key  -> 往左
key > root_key  -> 往右
```

但是当前 proof 里又额外给了两个方向提示。

先看第一个：

$$
\operatorname{root\_diff} = \operatorname{key} - \operatorname{root\_key}
$$

如果：

```text
key = 5
root_key = 8
```

那么：

```text
root_diff = 5 - 8 = -3
```

它表示：

```text
key 在 root 的左边。
```

再看：

```text
root_side
```

这个变量不是从数值自然学出来的，它是人为给的“正确大方向”。可以粗略理解成：

```text
目标地址在 root 左边时，root_side = -1
目标地址在 root 右边时，root_side = +1
```

于是：

$$
\operatorname{root\_alignment} = \operatorname{root\_diff} \cdot \operatorname{root\_side}
$$

如果 key=5，root_key=8，目标确实在左边：

```text
root_diff = -3
root_side = -1
root_alignment = (-3) * (-1) = 3
```

结果是正数。

正数就像在告诉模型：

```text
这个方向和目标方向对齐。
```

如果方向错了，乘出来就会是负数。

所以 `root_alignment` 的问题在于：

```text
它不是单纯告诉模型 key 和 root 的关系；
它把“这个关系是否符合正确路由方向”也编码进去了。
```

这就接近答案提示。

第二个公式：

$$
\operatorname{child\_alignment} = \operatorname{diff} \cdot \operatorname{child\_side}
$$

作用类似，只是它看的是更下面一层 child 的方向。

可以这样理解：

```text
root_alignment 帮模型判断第一步走 L 还是 R。
child_alignment 帮模型判断第二步走 LL/LR 或 RL/RR。
```

所以这两个 feature 不是普通“观测数据”，而是已经把搜索路径的判断边界整理好了。

它们已经把路由边界编码进去了。

可以粗略理解成：

```text
如果 root_alignment 为正，说明 key 应该走 root_side 指示的方向。
如果 child_alignment 为正，说明 key 应该走 child_side 指示的方向。
```

这就像考试时给学生一张提示纸：

```text
如果看到这个符号，就选左边。
如果看到那个符号，就选右边。
```

学生最后答对了。

这当然说明：

```text
笔能写；
答案纸能收；
分数能反馈；
学生能根据提示填答案。
```

但还不能说明：

```text
学生真的学会了这门课。
```

对应到 TreeHeap：

当前 proof 能说明：

```text
梯度链路通了。
Soft Plus 可以坍缩。
```

但还不能说明：

```text
TreeHeap kernel 从子树几何里学会了搜索规则。
```

## 为什么这不是否定 TreeHeap

这点要说清楚。

GLM 的审计不是在说：

```text
TreeHeap 错了。
```

它是在说：

```text
当前 evidence 的边界要写清楚。
```

`M0-SOFT-C03` 的 claim 是：

```text
Kernel-guided Soft Plus can receive gradient through K_write and Plus_a.
```

这个 claim 只问：

```text
梯度有没有到？
```

答案是：

```text
到了。
```

`M0-SOFT-C04` 的 claim 是：

```text
Kernel-guided Soft Plus can collapse to the correct hard plus address
in the synthetic toy.
```

这个 claim 只问：

```text
当前 toy 有没有坍缩对？
```

答案也是：

```text
对了。
```

但 `M0-SOFT-C05` 问的是：

```text
Kernel-guided Soft Plus 是否比 naive memory write 或 generic encoder soft plus 更好？
```

这个还没有做。

所以 ARA 修订后的状态是：

| Claim | 状态 | 解释 |
|---|---|---|
| C03 梯度可达 | supported | 当前 toy 有证据 |
| C04 toy 坍缩 | supported | 当前 toy 有证据 |
| C05 优于普通写入 | open | 需要下一步 ablation |
| clean kernel 学路由 | open | 当前 ablation 显示还没证明 |

## ARA 做了哪些修订

这次我把 SameTime 里的 ARA 做了几件修订。

第一，给 `claims.md` 加了 scope notes。

现在 C03/C04 明确写了：

```text
in scope:
  当前 toy 的梯度可达和坍缩。

out of scope:
  干净 kernel 从 raw subheap geometry 自己学会路由。
```

第二，加了 GLM audit summary：

```text
ara/m0-treeheap-math/evidence/soft_plus_probe/glm_audit_summary.md
```

这里保存多 seed 复现和 feature ablation 结论。

第三，补了结构化 trace：

```text
ara/m0-treeheap-math/trace/exploration_tree.yaml
```

这个文件记录：

```text
问题是什么；
为什么拒绝 naive memory write；
当前 proof 证明了什么；
GLM ablation 发现了什么；
为什么下一步要做 clean-kernel proof。
```

第四，把 `log/ara` 里缺失的 S2 诊断证据同步进 SameTime：

```text
ara/s2-translation/evidence/frame_probe_2h_queue/
ara/s2-translation/evidence/overnight_stopped_20260617/
```

这些不是正向成功证据。

它们是诊断证据：

```text
说明历史 checkpoint 和 world-model/frame probe 还不能支撑强 claim。
```

这类失败或不充分证据也必须进入 ARA。

因为 ARA 的目的不是只保存胜利。

ARA 的目的是真实保存研究状态。

## 下一步真正该 proof 什么

下一步不是再证明一次：

```text
梯度能流。
```

这个已经有了。

下一步应该证明：

```text
clean kernel 能不能学会 TreeHeap 路由。
```

也就是新的 `P-SOFT02`。

这句话的实际含义是：

```text
给模型一棵 TreeHeap 的局部子结构，
不给它人工整理好的答案方向，
让它通过训练自己学出：

什么时候往左；
什么时候往右；
什么时候 stop；
什么时候 merge；
哪个地址更像正确写入位置。
```

这和我们的总目标直接相关。

TreeHeap 最终想证明的不是：

```text
我也能把数组槽位 softmax 写一遍。
```

而是：

```text
树结构、路径、子堆、前缀、概率容器这些结构工具，
能让模型在某些任务上更有效地学习和外推。
```

如果 clean kernel 能学会路由，预期改进是：

```text
1. 更少人工规则：不用手写 root_alignment 这种答案提示。
2. 更强迁移：同一个 kernel 可以在不同地址、不同子树上复用。
3. 更好外推：训练见过浅层地址，测试能处理更深地址。
4. 更可解释：失败时能看出是 stop/left/right 哪一步错了。
5. 更接近语言结构：后续 S2 的 fold/slot/graph 才可能接上这个结构 kernel。
```

如果 clean kernel 学不会，也会告诉我们一个硬事实：

```text
当前 TreeHeap 的可微写入还缺少足够表达力；
也许需要 MLP kernel、多头 kernel、额外结构 loss，
或者 TreeHeap plus 本身还要改。
```

干净输入应该只给：

```text
key
parent key
left child key
right child key
is_leaf
depth/address metadata
```

不允许给：

```text
root_side
child_side
root_alignment
child_alignment
```

因为这些太像答案提示。

实验要比较三种写入方式：

```text
A: naive soft memory write
B: encoder soft plus
C: kernel-guided soft plus
```

A 是普通神经内存写入：

```text
arr_new[i] = (1 - p[i]) * arr_old[i] + p[i] * write_vector
```

B 是 soft plus，但地址概率由普通 encoder 输出：

```text
MLP(H, x) -> p(a)
H_next = sum_a p(a) * Plus_a(H, x)
```

C 是 TreeHeap 版本：

```text
K_write(subheap(H, a), x) -> score(a)
H_next = sum_a softmax(score(a)) * Plus_a(H, x)
```

判断指标包括：

```text
collapse_accuracy
final_loss
hard_soft_gap
collapse_legality
unseen_address_accuracy
sample_efficiency
```

如果 C 在干净特征下赢 A 和 B，那么 C05 可以升级。

如果 A 或 B 一样好，说明 TreeHeap kernel 的优势还没有证明。

如果三者都失败，就要重新设计 kernel。

## 给本科水平读者的一句话总结

现在的状态可以这样理解：

```text
我们证明了：
TreeHeap 这套结构可以接上梯度管道。

我们还没有证明：
TreeHeap kernel 能自己从树结构里学会聪明的搜索规则。
```

更口语一点：

```text
水管通了。
水能流到 TreeHeap 的 kernel 和 plus 参数。

但水流到那里以后，
能不能灌出一棵真正会搜索、会压缩、会外推的树，
还要做下一组实验。
```

这不是坏消息。

这是研究进入下一层的信号。

因为现在的问题已经从：

```text
TreeHeap 能不能训练？
```

变成了：

```text
TreeHeap 的结构归纳偏置，能不能比普通神经内存更有效？
```

这才是 TreeHeap 是否有存在性的关键问题。

> **License: GPLv3**
