---
title: "[SPR-069] STONE-1 航行报告：Encoder 已经抽水，Decoder 水压终于接通"
date: 2026-07-23
lastmod: 2026-07-23
weight: 69
author: Houming818 & Codex Review
description: "从 C01 到 C05 复盘 STONE-1：TreeHeap encoder 如何把路径信息压入 root，为什么 decoder 长期只读 root，以及冻结 encoder、强制打开递归水管后得到的正式证据。"
tags: [SPR, TreeHeap, ARA, STONE-1, Encoder, Decoder, Recursive Routing, WMT, NLL, BLEU]
---

# STONE-1 航行报告：Encoder 已经抽水，Decoder 水压终于接通

> STONE-1 还没有完成，但我们终于把一个长期混在一起的问题拆开了：不是 TreeHeap 深层没有信息，而是 decoder 的递归水管一直没有获得有效梯度。

这篇文章总结 STONE-1 从 C01 到 C05 的进展。

我们先给出最重要的结论：

1. TreeHeap encoder 确实执行了有左右顺序的递归折叠；
2. 训练得到的 root 不是简单词袋，而是路径敏感的压缩状态；
3. 原生 decoder 长期只读 root，继续增加训练步数也没有自行打开深层路径；
4. 冻结 encoder、强制打开递归路径后，decoder 能学会读取深层信息；
5. 在同等追加训练预算下，递归读取最终略好于 root-only；
6. 但读取深度仍然是人为固定的，所以 STONE-1 仍未完成。

这不是终点，但它把下一步从“继续猜架构”推进到了一个很具体的工程问题：

> **如何让 decoder 在保证梯度通道畅通的前提下，自己学习何时停止、何时继续向下读取。**

---

## 1. STONE-1 到底想证明什么

普通 seq2seq 模型可以把输入编码成一个向量，然后用神经网络生成输出。仅仅把这个向量放进数组的第零项，再给它取名叫 TreeHeap，并不能证明树结构有用。

STONE-1 要求更严格：

```text
输入 token
  → 写入 TreeHeap leaf
  → 逐层 FOLD
  → 形成 root 与各层 detail
  → decoder 按 TreeHeap 层级读取
  → 生成目标句子
```

其中至少需要回答三个问题。

### 1.1 Encoder 是否真的使用树

如果交换 left/right、破坏某层配对或替换 FOLD kernel，最终结果应当发生可测变化。

### 1.2 Decoder 是否真的读取树

如果打乱 decoder 正在读取的 detail 或地址，生成损失应当恶化。

### 1.3 使用树是否带来功能收益

结构参与计算还不够。递归读取至少应当达到 root-only 对照的水平，最好带来更低 NLL、更高 BLEU 或更稳定的生成。

STONE-1 不是“代码能跑”的里程碑，而是这三类证据必须同时成立。

---

## 2. 什么叫 Encoder 抽水机

一棵二叉 TreeHeap 的叶子保存局部 token 状态：

$$
H^{(0)}_1,H^{(0)}_2,\ldots,H^{(0)}_n
$$

相邻左右节点经过同一个局部 FOLD kernel：

$$
\left(H^{(d+1)}_i,D^{(d)}_i\right)
=
\operatorname{FOLD}_{\theta}
\left(H^{(d)}_{2i},H^{(d)}_{2i+1}\right)
$$

这里：

- $H^{(d+1)}_i$ 是向上一层传递的 parent 状态；
- $D^{(d)}_i$ 是这一层留下的 detail；
- $\theta$ 是可学习 codec 参数；
- left/right 地址和递归顺序是固定的 TreeHeap 数学骨架。

不断递归之后：

```text
leaf → parent → grandparent → root
```

这就是我们所说的信息抽水机。

“抽水”不意味着 root 能无损保存所有 token。它表示局部信息通过同一种递归规则逐层汇聚。root 更像一个高压压缩状态，各层 detail 保存折叠过程中没有继续上传的差异。

完整状态不是只有 root：

$$
H_{\text{state}}
=
\left(
H_{\text{root}},
D^{(0)},D^{(1)},\ldots,D^{(L-1)}
\right)
$$

因此，讨论 TreeHeap 时必须区分：

- `root`：最高层压缩结果；
- `H_state`：root 加全部层级 detail；
- `theta`：执行 FOLD、READ 和生成的学习参数。

---

## 3. C01 到 C04：我们排除了什么

### C01：自由学习方向没有形成稳定协议

C01 让模型自由学习局部方向 gate。结果 learned 版本反而弱于 identity 和 frozen-random 对照。

但交换左右地址会明显损伤 NLL。这说明：

> 地址有用，但自由漂移的坐标协议不稳定。

所以后续采用固定手性和固定代数骨架，不再让左右方向本身随意变化。

### C02：固定骨架加可学习残差

C02 使用固定的 `0.4/0.6` parent 规则和可学习连续残差。learned codec 的平均结果优于固定代数和固定随机对照：

| 方案 | NLL，越低越好 | BLEU-4，越高越好 |
|---|---:|---:|
| 固定代数 codec | 4.1138 | 10.7937 |
| 可学习残差 codec | **4.0538** | **11.2865** |
| 固定随机 codec | 4.0910 | 10.6865 |

结构干预也产生明显损伤。C02 支持 codec、地址和层级参与计算，但多 seed 稳定性和产品质量仍未通过。

### C03：直接扩大参数失败

C03 比较约 28M 和 50M 参数。相同更新预算下，50M 没有更好：

| 模型 | NLL | BLEU-4 |
|---|---:|---:|
| 28M，延长训练 | **3.7495** | **12.7444** |
| 50M，相同更新预算 | 4.1469 | 10.1225 |

这否定了“参数越大，私有协议自然越完整”的简单假设。

更重要的是，50M decoder 的 route mass 全部停在 root。root-only 与 full-depth 的结果相同，root 形成后再交换 child 地址也没有影响。

当时我们只能确认 decoder 没有读取 child，却不能确认 encoder 是否把路径信息压进了 root。

### C04：更多训练没有打开 Decoder

C04 把同一个 50.27M 模型连续训练到 62,500 次更新：

| Update | Valid NLL | 非 root route mass |
|---:|---:|---:|
| 15,625 | 4.1879 | 0 |
| 31,250 | 3.8867 | 0 |
| 46,875 | 3.7331 | 约 0 |
| 62,500 | 3.6613 | 约 0 |

训练质量持续改善，但 decoder 始终只读 root。

因此，“只是训练时间不够”被否定了。

---

## 4. C04 的关键证据：Root 不是词袋

如果在 root 已经形成后交换下层 child，NLL 没有变化。这只能说明 decoder 没读 child，不能说明 encoder 没用路径。

C04 增加了一个更严格的干预：

> 在某一层 FOLD **之前**交换左右 subheap，然后重新计算上层状态和 root。

最终 62,500 步 checkpoint 的结果：

| Pre-FOLD mirror depth | NLL 损伤 |
|---:|---:|
| 0 | 0.1678 |
| 1 | 0.1106 |
| 2 | 0.1336 |
| 3 | 0.3908 |
| 4 | **0.6747** |
| 5 | 0.4783 |

强制关闭 learned codec、退回固定代数 codec，还会造成 `+1.3456` NLL 损伤。

因此 C04 支持：

```text
有序 leaf
  → 路径敏感的递归 FOLD
  → 压缩 root
  → root-only surface decoder
```

这不是 Bag of Words。左右顺序、折叠路径和 learned codec 都进入了 root。

问题出在另一边：decoder 没有把 `H_state` 重新展开。

---

## 5. 为什么不能说“优化器选择了捷径”

我们一度把 root-only 解释成优化器选择了更容易的路径。这个表述不够准确。

当前 decoder 每生成一个 token，会计算：

```text
当前 query
  → 在当前节点决定 stop 或继续
  → 如果继续，计算 left/right 概率
  → 进入下一层
```

但 C04 训练后，stop probability 在 root 附近饱和。最终 route mass 大致是：

```text
[1.0, 0, 0, 0, 0, 0]
```

这意味着深层 branch 几乎不参与输出，也就没有有效梯度。

实际计算图是：

```text
token loss
  → root readout
  → H_root
  → encoder FOLD
  → leaf
```

缺少的是：

```text
token loss
  → decoder 深层 branch
  → child/detail
  → 逐层读取
```

所以更准确的诊断是：

> **Encoder 抽水机已经工作；Decoder 的向下释压通道处于关闭状态。**

---

## 6. C05：冻结 Encoder，只打开 Decoder 水管

C05 不再同时调整 encoder 和 decoder。

我们加载 C04 的最终 checkpoint，冻结全部 encoder 参数和完整 `H_state` 生成方式，然后复制两个相同 decoder：

### Root control

每次读取都固定停在 root：

```text
route mass = [1, 0, 0, 0, 0, 0]
```

### Leaf pressure

禁止提前 stop，强制经过每个可见层级，在每层学习 left/right route：

```text
route mass = [0, 0, 0, 0, 0, 1]
```

两组实验：

- 使用相同的一百万对 WMT 训练数据；
- 从同一个 C04 checkpoint 开始；
- 每组只训练 decoder 15,625 次更新；
- batch、学习率和随机种子相同；
- encoder 校验和在训练前后必须完全相同。

这样就只回答一个问题：

> 冻结的 C04 `H_state` 中，是否存在能够被递归 decoder 学会读取的信息？

---

## 7. 正式结果：五个 Gate 全部通过

训练在 io 的 RTX 3090 上完成，总时间约 66.5 分钟，峰值显存约 1.67 GiB。

| 指标 | Root control | Leaf pressure | 趋势 |
|---|---:|---:|---|
| 初始 valid NLL | 3.6613 | 4.6301 | 递归臂开始时不会读 |
| 最终 valid NLL | 3.5875 | **3.5496** | 递归臂反超 |
| Test NLL | 3.5149 | **3.4636** | 越低越好 |
| Test PPL | 33.61 | **31.93** | 越低越好 |
| BLEU-4 | 13.5999 | **13.9564** | 越高越好 |
| 严重重复率 | 2.60% | **1.95%** | 越低越好 |
| 完全匹配率 | 0.60% | **0.65%** | 越高越好 |

递归臂的 valid NLL 改善：

$$
4.6301-3.5496=1.0805
$$

最终递归臂相对 root 对照的 Test NLL 优势：

$$
3.5149-3.4636=0.0513
$$

BLEU-4 提升：

$$
13.9564-13.5999=0.3565
$$

提升不算巨大，但方向一致：NLL、PPL、BLEU 和重复率都更好。

更关键的是机制指标：

| Gate | 结果 |
|---|---|
| 递归 NLL 至少改善 0.30 | 通过，改善 1.0805 |
| branch kernel 获得非零梯度 | 通过，观测比例 100% |
| detail shuffle 至少损伤 0.10 | 通过，最大损伤 0.6909 |
| encoder 保持冻结 | 通过，checksum 完全一致 |
| 递归臂不比 root 对照差 0.10 以上 | 通过，而且略胜 |

因此 C05 的正式状态是：

> **支持 frozen TreeHeap state 上的强制递归 decoder 通道，单种子证据。**

---

## 8. 哪些层真的携带信息

我们逐层打乱 frozen detail，再观察 NLL 损伤：

| Detail depth | NLL 损伤 | 当前可说的结论 |
|---:|---:|---|
| 0 | 0.0000 | 本次读取几乎不依赖 |
| 1 | 0.0942 | 弱影响 |
| 2 | 0.1633 | 有因果信息 |
| 3 | 0.5632 | 强因果信息 |
| 4 | **0.6909** | 最强因果信息 |
| 5 | 0.0826 | 弱影响 |

这说明信息并不是平均分布在所有深度，也不是只有 root 有用。中间层 detail 对 decoder 最重要。

但请注意，我们还不能把这些层直接翻译成：

```text
depth 2 = 词法
depth 3 = 短语
depth 4 = 句义
```

实验只证明这些层具有因果作用，没有提供人类可读的语法标签。私有协议仍然是模型自己形成的编码。

---

## 9. 看几个生成样例

### 样例一

输入：

```text
Integrated, standards-based certification labeling and reporting
```

参考：

```text
集成的、基于标准的认证标签和报告
```

递归 decoder：

```text
集成认证的标准、报告和报告
```

结构基本合理，但出现了“报告”重复。

### 样例二

输入：

```text
POWER TRANSISTORS DARLINGTON NPN SILICON
```

参考：

```text
Epitaxial Planar NPN Silicon Transistors
```

递归 decoder：

```text
SILICON NPN EPITAXIAL TRANSISTORS
```

它抓住了器件描述的主要术语，但没有忠实对应全部参考内容。

### 样例三

输入：

```text
Adobe Dreamweaver CSS Grafisk design HTML Webbdesign $90 (Avg Bid)
```

参考：

```text
Adobe Dreamweaver CSS 平面设计 HTML 网站设计 $708 (Avg Bid)
```

递归 decoder：

```text
Adobe Dreamweaver CSS 平面设计 HTML 网站设计 $166 (Avg Bid)
```

句式和类别基本正确，具体数字错误。这类样例说明模型已经具有统计生成能力，但事实复制仍不可靠。

---

## 10. 当前 STONE-1 进度表

| 阶段 | 回答的问题 | 当前结论 |
|---|---|---|
| C01 | 自由学习左右方向是否稳定 | 不支持；地址有效，但自由 gate 不稳定 |
| C02 | 固定手性加 learned codec 是否有效 | 结构机制正向，产品门槛未过 |
| C03 | 增加参数是否自然改善 | 否定；50M 在等预算下更差 |
| C04 | 增加训练步数是否自然长出递归读取 | 否定；形成路径敏感 root 压缩 |
| C05 | 冻结 encoder、打开水管后能否递归读取 | **支持；递归臂略胜 root 对照** |

C05 的单次结果已经达到早期 STONE-1 数值线：

- Test NLL `3.4636`，低于 `3.90`；
- BLEU-4 `13.9564`，高于 `13.5`。

但 STONE-1 仍不能宣布完成，原因有三点：

1. 目前只有一个随机种子；
2. route depth 是人为强制到最深层，不是模型自己学会；
3. 当前生成仍有数字错误、重复和语义偏差。

所以这次是**机制突破**，还不是产品完成。

---

## 11. 下一步不该继续盲目扩容

C03 已经告诉我们，直接增加参数不可靠。C04 也告诉我们，继续增加训练步数不会自动打开没有梯度的水管。

下一步应当保持 C05 已经验证的条件：

```text
每个 decoder 层级都有非零梯度通道
```

然后逐步放开深度控制：

1. 先从固定最深读取，改为固定的非零下行压力；
2. 允许模型在保持最小流量的条件下学习 stop；
3. 记录每层梯度、route mass 和 detail 因果损伤；
4. 用多 seed 验证递归收益是否稳定；
5. 只有机制稳定后，再恢复 encoder-decoder 联合训练。

这里不能再次允许 stop gate 把全部概率压回 root。否则我们只会重演 C04。

---

## 12. 一句话总结

此前我们看到的是：

```text
Encoder 把结构信息抽进 root，
Decoder 却只在井口取水。
```

C05 做的事情很简单：

```text
冻结水源，
打开向下水管，
让 decoder 的每一层都收到梯度。
```

结果表明，深层 TreeHeap state 不但能被读取，而且在同等追加训练预算下略好于 root-only。

因此现在最准确的结论是：

> **TreeHeap encoder 已经形成路径敏感的递归压缩；decoder 的递归读取能力也可以被训练出来。尚未解决的是如何让水压和停止深度在不关闭梯度通道的前提下自然学习。**

ARA 证据已经保存于 SameTime：

- Claim：`S3-STONE1-FROZEN-PRESSURE-C05`
- Evidence：`ara/s3-generation/evidence/s3_stone1_frozen_encoder_pressure_decoder/`
- 结果提交：`6257395`

研究仍在航行，STONE-1 仍然诚实地保持未完成状态。
