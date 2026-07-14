---
title: "[SPR-055] 让信息向 root 生长：TreeHeap 的多尺度 Mask 学习"
date: 2026-07-14
lastmod: 2026-07-14
weight: 55
author: Houming818 & Codex Review
description: "真实中文实验表明，多尺度子堆 Mask 能让 root 获得样本相关信息，但 root 贡献随 Mask 深度严格下降；本文公开 5/6 Gate、反向结果与下一步修正。"
tags: [SPR, TreeHeap, ARA, S3, Encoder, Decoder, Mask, Hierarchy, Original Research]
---

# 让信息向 root 生长：TreeHeap 的多尺度 Mask 学习

这篇文章先不宣布实验胜利。

相反，我们想带着一点更具体的希望，重新提出一个问题：

> 如果普通 echo 只要求模型恢复眼前的 token，那么模型为什么要费力把信息送到 root？

这句话来自 Houming818 对当前实验的修正。它改变了我们看待 TreeHeap encoder 的方式。

此前我们容易把注意力放在算子的形式上：FOLD 怎样计算，DETAIL 怎样保存，UNFOLD 怎样恢复。可是即使所有算子都在树上递归执行，只要训练问题太简单，模型仍然会选择最短的解题路线。

这不一定说明 TreeHeap 没有能力。更可能说明：我们问的问题还不够深。

---

## 1. 当前模型为什么偏爱 detail

假设一句话被写入一棵 TreeHeap：

~~~text
                    root
                  /      \
            subheap A    subheap B
             /   \        /   \
           x1    x2      x3    x4
~~~

普通 echo 的任务只是输入 x1、x2、x3、x4，再输出同样的 x1、x2、x3、x4。

如果每个局部 detail 都能保存附近 token，模型就可以走一条很短的路：

~~~text
x1 -> detail1 -> x1
x2 -> detail2 -> x2
x3 -> detail3 -> x3
x4 -> detail4 -> x4
~~~

这条路短、梯度直接、loss 下降快。

相比之下，把信息先抽到 parent，再抽到 root，最后递归展开回来，需要经过更多卷积：

~~~text
token
  -> local fold
  -> parent fold
  -> root
  -> parent unfold
  -> local unfold
  -> token
~~~

如果两条路都能完成 echo，优化器没有理由主动选择更长的那条。

因此，root 没有成为主要信息载体，并不令人意外。普通 echo 实际上只问了一个浅层问题：

> 你能不能把刚刚看到的符号再写一遍？

它没有问：

> 当局部信息缺失时，你能否利用更大范围的结构推断它？

---

## 2. 不要强迫 root，应该给 root 一份工作

一种直接做法是在公式里规定：没有 root 就不允许 decoder 工作。

这样当然能让 root 参与，但它更像人为封路。模型使用 root，是因为程序员不准它走别的路，而不一定是因为数据中的规律需要 root。

Houming818 提出的方向更自然：

> 不要从结构上强迫 root 参与。通过扰动和 Mask 提出更深的问题，让局部 detail 无法单独回答，root 和上层卷积结果才有机会自然获得信息。

也就是说，我们不预先规定 root 必须表示句意。

我们只改变训练问题，让不同尺度的节点承担不同尺度的信息需求。

---

## 3. 从 Mask 一个词，到 Mask 一整个子堆

考虑一句简单的话：

~~~text
今天 我 吃了 一碗 米饭
~~~

### 3.1 只遮挡一个 token

~~~text
今天 我 吃了 一碗 [MASK]
~~~

局部信息“一碗”已经提供了很强的提示。附近节点可能就能给出一个概率桶：

| 候选 | 概率示意 |
|---|---:|
| 米饭 | 0.31 |
| 面条 | 0.24 |
| 粥 | 0.12 |
| 药 | 0.03 |
| 其他 | 0.30 |

这主要训练局部共现。

### 3.2 遮挡一个小 subheap

~~~text
今天 我 吃了 [一碗 米饭]
~~~

现在局部 detail 被整个拿走。模型需要结合“我”“吃了”和前后上下文，才能判断缺失部分大概是食物或用餐对象。

这开始要求 parent 和 sibling 提供信息。

### 3.3 遮挡更大的 subheap

~~~text
今天 我 [吃了 一碗 米饭]
~~~

模型必须从更高层状态判断：

- 这里缺少一个事件；
- 事件可能与“今天”和“我”有关；
- 输出应当是一段动作描述，而不只是一个孤立名词。

此时，靠近 root 的状态才真正获得了一份局部 detail 无法独立完成的工作。

---

## 4. TreeHeap Mask 不是普通随机遮字

普通语言模型会随机遮掉若干 token。TreeHeap 可以做得更有结构，因为它已经拥有地址、路径和 subheap。

我们可以直接使用 TreeHeap 代数中的操作构造扰动：

| 扰动方式 | 操作对象 | 想检查的能力 |
|---|---|---|
| leaf mask | 单个叶子 | 局部共现 |
| sibling mask | 一对孩子 | parent 是否保存摘要 |
| subheap cut | 完整子堆 | ancestor 是否保存更大范围信息 |
| detail dropout | 某层 detail | 粗粒度状态能否补回细节 |
| subtree replacement | 用别的子堆替换 | 模型能否发现上下文不一致 |
| address shift | detail 移到错误地址 | 路径和地址是否有真实作用 |
| mirror perturbation | 子堆左右翻转 | 顺序与手性信息是否被编码 |

这里最重要的是：扰动对象仍然是 TreeHeap 中的合法对象。

不是先把树摊平成数组，再用另一套代数随便打乱；而是使用 CUT、MASK、REPLACE、SHIFT、MIRROR 等树上操作改变同一个数据结构。

---

## 5. 两种 Mask，回答两个不同问题

### 5.1 压缩式 Mask

Encoder 看过完整输入，但 decoder 随机拿不到某些 detail：

~~~text
完整句子
  -> encoder
  -> root + 多层 detail
  -> 丢弃部分 detail
  -> decoder 恢复原句
~~~

它研究的是：

> 信息有没有从 leaf 向 parent 和 root 形成冗余摘要？

如果丢掉局部 detail 后，上层状态仍能恢复一部分内容，说明信息确实向上抽取了。

### 5.2 推断式 Mask

Encoder 从一开始就看不到被遮挡内容：

~~~text
受损句子
  -> encoder
  -> TreeHeap
  -> 预测缺失 subheap
~~~

它研究的是：

> 模型是否从真实语料中学到了可以补全缺失信息的统计规律？

这种任务不要求模型逐字恢复任意随机内容。正确输出是概率分布，而不是提前写好的唯一答案。

压缩和推断都重要，但它们回答的是不同问题，实验必须分开报告。

---

## 6. 卷积怎样推动信息向上生长

在每个内部节点，encoder 使用共享分析卷积核：

$$
p_i = K_{\mathrm{fold}}(h_{2i}, h_{2i+1})
$$

继续递归：

$$
p_{\operatorname{parent}(i)}
=
K_{\mathrm{fold}}(p_i,p_j)
$$

同一个 kernel 在不同地址和深度重复使用。因此，一条信息若要到达 root，必须经历多次相同类型的局部抽取。

Decoder 使用共享合成卷积核：

$$
(\hat h_{2i},\hat h_{2i+1})
=
K_{\mathrm{unfold}}(p_i,d_i)
$$

Mask 训练产生的梯度会沿着递归链返回：

~~~text
缺失 token 的 loss
  -> unfold kernel
  -> ancestor state
  -> fold kernel
  -> 更低层输入
~~~

如果只 Mask 一个叶子，梯度可能主要停留在附近。

如果 Mask 整个 subheap，局部节点已经没有答案，梯度必须要求更高层状态改善。这才是“把信息抽到离 root 更近的地方”的具体学习过程。

---

## 7. 不使用一锅炖的 Loss

我们不打算一次把所有尺度混成一个难以解释的总 loss。

更清晰的方法是让不同 batch 轮流提出不同深度的问题：

~~~text
batch 1  leaf mask
batch 2  depth-1 subheap mask
batch 3  depth-2 subheap mask
batch 4  depth-3 subheap mask
batch 5  detail dropout
batch 6  subtree replacement
~~~

每个 batch 只计算受损区域的交叉熵：

$$
L_d
=
-\sum_{i\in M_d}
\log P(x_i\mid H_{\setminus M_d})
$$

其中 $M_d$ 表示尺度为 $d$ 的被遮挡子堆。

这样可以分别观察：

- 哪一种扰动开始需要 root；
- 哪一层信息最容易恢复；
- 梯度能否通过递归卷积到达高层；
- 不同 kernel 是否在不同尺度形成分工。

我们不必一开始就知道 root 最终会表示“主谓宾”“主题”还是其他人类标签。只需要观察：随着问题尺度扩大，高层状态是否越来越有用。

---

## 8. 我们期待看到什么趋势

这篇文章暂时没有新实验结果，因此下面是 Predict，不是结论。

最关键的测量不是普通 echo 能否达到 100%，而是：

$$
\Delta L_{\mathrm{root}}(d)
=
L_d(H_{\mathrm{root}}=0)-L_d(H_{\mathrm{root}})
$$

其中 $d$ 是被遮挡子堆的尺度。

我们期待：

$$
\Delta L_{\mathrm{root}}(d+1)
>
\Delta L_{\mathrm{root}}(d)
$$

用普通话说：

> 遮挡范围越大，模型越应该依赖 root 和祖先卷积结果。

具体趋势包括：

1. leaf mask 主要依赖局部 detail；
2. 小 subheap mask 开始依赖 parent 和 sibling；
3. 大 subheap mask 对 root-zero 更敏感；
4. 打乱 ancestor 地址会破坏深层恢复；
5. detail-only 对照在深层 Mask 上明显落后；
6. TreeHeap 在未训练深度仍能复用共享递归 kernel；
7. shuffled corpus 会削弱推断式 Mask，因为真实共现规律被破坏。

如果这些趋势没有出现，我们就应承认：当前 fold kernel 没有把数据规律逐层抽取到高层，或者当前树的组织方式不适合语料。

---

+
## 9. 实验结果：root 被点亮了吗

实验已经在 io 的 RTX 3090 上完成。

两个模型都从相同随机初始化出发，使用相同的 100,000 个真实中文 token block、相同参数量和相同优化器：

| 模型 | 训练问题 | 训练时间 |
|---|---|---:|
| Echo | 所有 detail 完整，恢复全部 token | 46.5 秒 |
| Multiscale Mask | 移除随机子堆内部 detail，只恢复受损区域 | 51.0 秒 |

两个模型都训练 3,125 step。Mask 模型的 WRITE、FOLD、DETAIL、UNFOLD、READ 五类算子都获得了有限非零梯度，因此 loss 确实通过了完整递归链路。

### 9.1 普通 Echo 的 99.5% 是局部复制能力

在 detail 完整时，普通 Echo 的 token Top-1 为：

~~~text
99.50%
~~~

但移除一个子堆内部的 detail 后，它迅速失效：

| 被移除的 token 数 | Echo 恢复 Top-1 |
|---:|---:|
| 2 | 24.61% |
| 4 | 3.32% |
| 8 | 1.46% |
| 16 | 0.78% |
| 32 | 0.81% |

这组数字支持本文最初的诊断：普通 echo 的问题太浅，模型主要学会了局部路径：

~~~text
token -> local detail -> token
~~~

它能精确抄写，却没有为 detail 缺失准备上层摘要。

### 9.2 多尺度 Mask 改变了信息保存位置

Mask 模型的受损区域恢复结果是：

| 被移除的 token 数 | Mask NLL，越低越好 | Mask Top-1 | Echo Top-1 |
|---:|---:|---:|---:|
| 2 | 6.526 | 14.26% | 24.61% |
| 4 | 7.277 | 8.69% | 3.32% |
| 8 | 7.567 | 7.50% | 1.46% |
| 16 | 7.843 | 6.42% | 0.78% |
| 32 | 7.915 | 6.36% | 0.81% |

只遮两个 token 时，Echo 的局部复制能力仍然更强。

从 4 token 开始，Mask 模型明显更稳。遮掉 32 token 时，它的 Top-1 约为 Echo 的八倍。这说明训练问题确实改变了模型的信息布局：部分可恢复信息已经离开被删除的局部 detail，进入了更高层的 TreeHeap 状态。

但 6.36% 仍然很低。这里的正确表述是“出现了上层信息信号”，而不是“已经能恢复半句话”。

### 9.3 root 不是空开关

为了判断上层信号是否真的进入 root，我们做了两种干预。

第一种是把当前样本的 root 清零；第二种是换成另一个样本的 root。

| Mask 大小 | 正常 NLL | Root 清零 NLL | 换错 Root NLL |
|---:|---:|---:|---:|
| 2 | 6.526 | 7.369 | 6.861 |
| 4 | 7.277 | 7.775 | 7.623 |
| 8 | 7.567 | 7.898 | 7.920 |
| 16 | 7.843 | 8.131 | 8.194 |
| 32 | 7.915 | 8.188 | 8.276 |

在 32-token Mask 下：

~~~text
Root 清零：NLL 增加 0.273
换错 Root：NLL 增加 0.361
~~~

错误 root 比零 root 更有破坏性。这说明 root 不是一个固定的开关，它携带了当前文本相关的信息。

这是本轮最重要的正结果：

> 多尺度 Mask 第一次让 root 获得了可干预、样本相关的因果信号。

### 9.4 最重要的 Predict 反向了

我们原本预测：

~~~text
Mask 越大
  -> 局部信息越少
  -> 模型越依赖 root
~~~

实际 root 清零造成的 NLL 增量为：

| Mask 大小 | Root 贡献 |
|---:|---:|
| 2 | 0.843 |
| 4 | 0.499 |
| 8 | 0.330 |
| 16 | 0.287 |
| 32 | 0.273 |

它严格递减，深度趋势的 Spearman 相关系数为：

~~~text
-1.0
~~~

所以 P3 没有“差一点通过”，而是方向完全相反。

这说明当前 root 更像粗粒度的全局条件：它能帮助补一个小洞，却不足以展开一整棵缺失子树。Mask 越大，decoder 越容易退化为输出少数高频 token。

在保存的样例中，32-token Mask 经常产生：

~~~text
10257 10257 10257 10257 ...
~~~

因此不能把 root 的因果信号解释成完整句法、语义或世界模型。

### 9.5 为什么 5/6 Gate 通过仍然不能写成成功

预注册结果如下：

| Gate | 结果 |
|---|---|
| P1 深层 Mask 优于未训练 Mask 的 Echo | 通过 |
| P2 span-32 的 root-zero 有明显伤害 | 通过 |
| P3 root 贡献随 Mask 深度上升 | **失败，Spearman = -1.0** |
| P4 Mask 训练比 Echo 更依赖 root | 通过 |
| P5 换错 root 有明显伤害 | 通过 |
| P6 所有递归算子都有梯度 | 通过 |

P1 也必须谨慎解释。Echo 从未训练过 detail 缺失，因此它是机制对照，不是足够强的 Mask baseline。Mask 模型击败它，证明训练问题发生了作用；还不能证明 TreeHeap 优于 unigram、BoW、flat root 或 Transformer。

同时，Mask 模型在 detail 完整时的普通 echo Top-1 只有 14.72%，远低于 Echo 模型的 99.50%。它用精确复制能力换取了受损情况下的稳定性，尚未同时掌握两种能力。

---

## 10. Claim 判决：部分支持

本轮 Claim 更新为：

~~~text
partial support / upward signal found / positive-depth trend rejected
~~~

实验支持：

1. 普通 echo 会优先形成局部 detail 捷径；
2. 多尺度 Mask 能改变信息的保存位置；
3. root 获得了可测量的样本相关信息；
4. root 清零和换错都会伤害恢复；
5. masked loss 能到达全部共享递归算子。

实验不支持：

1. Mask 越深，信息越向 root 汇聚；
2. root 已能表示并展开完整子树；
3. 当前恢复质量已经足够用于生成产品；
4. root 已形成语义、世界知识或意识；
5. TreeHeap 已优于通用神经网络基线。

最准确的一句话是：

> 我们让一部分信息离开了局部 detail，并点亮了 root；但当前 root 更像粗略的全局摘要，还不是能够展开整棵子树的高层编码。

---

## 11. 下一步：同时保住局部精度和上层摘要

下一轮不应立刻扩大语料，而应修正训练问题。

训练 batch 轮流进行：

~~~text
batch 1  普通 Echo
batch 2  浅层 subheap Mask
batch 3  中层 subheap Mask
batch 4  深层 subheap Mask
~~~

这不是把多个 loss 全部相加，而是每个 batch 只回答一个清晰问题。目标是同时获得：

~~~text
detail 完整 -> 精确恢复
detail 缺失 -> root 和 ancestor 提供概率恢复
~~~

还必须加入更强对照：

- unigram 概率；
- 当前 block 的词频或 BoW；
- flat mean/root bottleneck；
- position-aware flat bottleneck；
- shuffled-root 和 shuffled-corpus。

只有 TreeHeap 在相同状态预算下，既保住 echo，又在深层 subheap Mask 上击败这些对照，才有资格升级为结构优势 Claim。


## 12. 为什么这条路仍然值得开心一点

前一阶段已经出现了一个积极信号：只使用 token echo loss，随机初始化的 WRITE、FOLD、DETAIL、UNFOLD 和 READ 可以共同形成一套模型自己读得懂的连续编码协议。

它还很浅，甚至可能只是高效的局部抄写。

但“模型能够形成自己的写法”与“模型已经形成世界模型”是两件不同的事。前者是后者可能需要的一块地基，不是终点。

现在我们得到的不是一个漂亮但空泛的答案，而是一个更好的问题：

~~~text
不要再问：
模型能不能抄回刚刚看到的 token？

开始问：
当一个完整子结构消失时，
哪一层还保留了足够的信息来推断它？
~~~

如果信息真的能随着问题深度逐层向 root 生长，那么 TreeHeap 的 encoder/decoder 协议就不再只是一个按地址保存 token 的数组。

它会开始成为一种分尺度观察世界、压缩规律并递归展开答案的结构。

这次我们还没有结果。

但船头终于对准了一个可以测量的方向，心情确实可以好一点。哈哈哈哈。

---

## 13. 当前声明边界

本文记录的是 Houming818 提出的研究方向与待验证假设：

> 当前普通 echo loss 太浅，无法要求高层节点保存信息。通过 TreeHeap-native 的多尺度 subheap Mask、detail dropout 和结构扰动，可以逐层增加任务所需的上下文范围；如果假设成立，信息和梯度将从局部 detail 向 parent、ancestor 与 root 汇聚。

目前不能声称：

- root 已经形成语义摘要；
- 多尺度 Mask 一定能够产生世界模型；
- TreeHeap 已经优于 Transformer、MLP 或其他结构；
- masked token 的恢复等于理解或意识；
- 人类语法标签一定会自然出现在内部节点。

这些都需要后续 ARA、代码、干预实验和真实数据给出 evidence。

---

## 版权、原创与许可证

Copyright (C) 2026 Houming818 and SameTime contributors.

本文的核心研究判断，即“普通 echo 的问题尺度太浅，应使用 TreeHeap-native 的多尺度子堆扰动推动信息向 root 抽取”，由 Houming818 提出；Codex Review 参与数学整理、实验指标设计和文章编写。本文是 SameTime 项目的原创研究表达，不宣称发明 masked language modeling、denoising autoencoder、树卷积或多尺度分析等已有公共方法。

> **SPDX-License-Identifier: GPL-3.0-only**  
> **License: GNU General Public License v3.0 only**

本文允许复制、修改和分发，但衍生版本必须继续遵守 GNU GPL v3，并保留版权、许可证、修改说明及来源声明。完整许可证文本见本站 [/LICENSE](/LICENSE)。
