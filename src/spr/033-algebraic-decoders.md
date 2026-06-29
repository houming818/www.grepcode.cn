---
title: "[SPR-033] TreeHeap 的代数 Decoder：internal state 不是没信息，而是需要正确读法"
date: 2026-06-29
weight: 33
author: nio (Houming818) & Codex Review
description: "SPR-033 回答 SPR-032 的一个关键问题：internal node state 如果像 hash 一样不可直观看懂，是否能从 TreeHeap 的数学结构中找到 decoder？实验支持 projection、decompose、mod、conjugate 等代数 decoder。"
tags: [SPR, TreeHeap, ARA, M0, Algebra, Decoder]
---

# TreeHeap 的代数 Decoder：internal state 不是没信息，而是需要正确读法

SPR-032 做了一个概率读取核实验。

它证明：

```text
从 arr[1] 开始，用 stop/left/right 走到目标节点，这件事可以学会。
```

但是它也暴露了一个问题：

```text
叶子节点很好读。
内部节点不好读。
```

当时我把问题说成：

```text
internal node state 没有学好。
```

这个说法不够准确。

你指出了更关键的一点：

```text
internal node state 可能已经编码了信息，
只是它像 hash / latent vector 一样，不能直接用眼睛看懂。
我们需要 decoder。
```

而且 TreeHeap 不是普通的训练数据集合。它应该是一个带数论和代数结构的集合。

所以 decoder 不应该只有：

```text
learned decoder = 训练一个 MLP 去猜
```

还应该有：

```text
algebraic decoder = 从 TreeHeap 的数学结构直接读
```

SPR-033 就是为了验证这件事。

## 两种 decoder

我们先把 decoder 分成两类。

第一类是学习 decoder：

```text
h_internal -> MLP -> label
```

比如：

```text
internal state -> checksum bucket
internal state -> phrase vector
internal state -> syntax label
```

SPR-032 里的 checksum decoder 属于这一类。

第二类是代数 decoder：

```text
h_internal -> projection / decompose / mod / mirror
```

它不是靠训练猜出来的，而是由 TreeHeap 的结构定义出来的。

类比十进制数字：

```text
321
```

你不需要训练一个神经网络去知道百位是 `3`、十位是 `2`、个位是 `1`。

因为十进制系统自带 decoder：

```text
hundreds decoder -> 3
tens decoder     -> 2
ones decoder     -> 1
```

TreeHeap 也应该类似。

如果 TreeHeap 有路径、地址、子堆、左右对称，那么它应该自带一些读法：

```text
left-subheap decoder
right-subheap decoder
path projection decoder
mod residue decoder
mirror/conjugate decoder
```

这就是 SPR-033 的核心。

## 实验设计

这次先不做语言，不做 WMT。

我们先做纯数学 toy。

定义一个有限域：

```text
field = Z_1000003
```

也就是所有计算都在一个大质数取模的数论空间里进行。

TreeHeap 设置：

```text
max_len = 8
channel_dim = 16
vocab = 257
samples = 5000
```

每个 token id 映射到一个确定的 primitive vector：

```math
token\_id \rightarrow v_{token} \in Z_p^{16}
```

然后把 token 写入叶子槽位：

```text
state[leaf_slot] = v_token
```

一个 internal node state 就是它覆盖的叶子槽位集合。

注意，这个 state 对人眼来说不好懂。

它不是：

```text
[cat, run, fish]
```

而是：

```text
Z_p 里面的一堆高维向量
```

所以它像 hash，或者说像 latent state。

问题是：

```text
能不能用 TreeHeap 的代数 decoder 把它读出来？
```

## 这次测哪些 decoder？

### 1. Projection Decoder

投影 decoder：

```text
project(H, node)
```

意思是：

```text
只保留某个 node 覆盖的子堆槽位。
```

比如：

```text
node = 2
span = [0, 4]
```

那就只读左半棵子树。

### 2. Decompose Decoder

分解 decoder：

```text
decompose(H, node) -> left_state, right_state
```

然后检查：

```text
compose(left_state, right_state) == project(H, node)
```

这就是 TreeHeap 的 compose/decompose 对偶。

### 3. Mod Residue Decoder

取模 decoder：

```text
residue(H, m)
```

比如 `m = 2`：

```text
偶数地址槽位聚合到 bucket 0
奇数地址槽位聚合到 bucket 1
```

这就是你之前说的取模思想。

它不是普通数组上的取模，而是：

```text
TreeHeap 地址空间上的取模。
```

### 4. Conjugate / Mirror Decoder

共轭 decoder：

```text
mirror(H)
```

它把左右结构翻转。

实验检查：

```text
mirror(mirror(H)) == H
```

这说明 mirror 不是随便改数据，而是一个代数对称操作。

### 5. Length Decoder

长度 decoder：

```text
norm0(H)
```

它数有多少个非空叶子槽位。

### 6. Ordered Slot Decoder

有序槽位 decoder：

```text
decode_ordered_tokens(H)
```

它不是靠 MLP 猜，而是用 primitive vector 的反查表读出每个槽位的 token。

这类似：

```text
从十进制数字里读取每一位。
```

## 实验结果

运行在 io：

```text
host = io.grepcode.cn
samples = 5000
field = Z_1000003
```

结果：

| Metric | Value |
|---|---:|
| `projection_exact` | 1.0000 |
| `decompose_recompose_exact` | 1.0000 |
| `mirror_involution_exact` | 1.0000 |
| `mod_residue_exact` | 1.0000 |
| `length_decode_exact` | 1.0000 |
| `ordered_token_decode_exact` | 1.0000 |
| `checksum_stability_exact` | 1.0000 |

ARA 结论：

```text
M0-DEC-C01 -> supported pilot
```

一条例子：

```text
tokens = [120, 142, 246, 0, 0, 0, 0, 0]
query_node = 2
span = [0, 4]
decoded_tokens = [120, 142, 246, 0, 0, 0, 0, 0]
subheap_length = 3
subheap_checksum = 914574
```

这说明：

```text
internal state 虽然不是人眼可读，
但可以通过代数 decoder 读出子堆、长度、顺序槽位、模余数和镜像关系。
```

## 这如何修正 SPR-032？

SPR-032 的 internal checksum 表现不好：

```text
128 bucket internal OOD acc = 0.2214
32 bucket internal OOD acc  = 0.4332
```

当时可能会误解成：

```text
internal node state 没有信息。
```

SPR-033 说明，这个结论太急了。

更准确应该是：

```text
internal node state 可能有信息，
但 checksum bucket 不是一个自然的 decoder。
```

TreeHeap 的第一组自然 decoder 应该来自代数：

```text
projection
decompose
mod residue
mirror
length
ordered slot
```

然后，语言 decoder 应该站在这些代数 decoder 上继续学习。

也就是说：

```text
先有数学读法。
再有语义读法。
```

## 和 MLP / Transformer 的区别

MLP hidden state 当然也可以训练 decoder。

Transformer hidden state 也可以训练 probe。

但 TreeHeap 的特点应该是：

```text
它的结构本身规定了一些 decoder。
```

比如：

```text
左子堆怎么取
右子堆怎么取
路径怎么投影
镜像怎么翻转
地址怎么取模
```

这些不是从数据里硬学出来的，而是 TreeHeap 的代数地基。

这可能就是 TreeHeap 的存在性之一：

```text
它不是一个完全不同于 ML 的东西。
它仍然可以训练。
但它比 flat hidden state 多了一组结构化、可解释、可组合的数学 decoder。
```

## 这次没有证明什么？

没有证明语言语义。

没有证明 WMT 翻译。

没有证明 learned decoder 不需要。

没有证明压缩最优。

没有证明带噪声的神经 encoder 写入后，代数 decoder 仍然稳定。

这次只证明：

```text
在一个有限域/path-address TreeHeap toy 中，
internal state 有一组精确的代数 decoder。
```

## 下一步

我认为 SPR-034 应该把 SPR-032 和 SPR-033 接起来。

也就是：

```text
不要再让 internal node 直接预测任意 checksum bucket。
```

而是让 internal read 先输出代数可读属性：

```text
subheap length
first token
last token
ordered prefix
bag sketch
mod residue
left/right projection
```

然后再训练 learned decoder：

```text
algebraic decoder output -> semantic decoder
```

这样 TreeHeap 的路线会更稳：

```text
M0: 数学 decoder
S1: 数据写入后保持 decoder 可读
S2: 在可读子堆上做结构折叠
S3: 翻译/生成
```

## 总结

SPR-033 的核心结论是：

```text
internal node state 不是必须直接被人看懂。
它可以是 hash/latent state。
关键是 TreeHeap 必须提供 decoder。
```

这次证明的是第一组 decoder：

```text
projection
decompose
mod residue
conjugate mirror
length
ordered slot readout
```

这让我们可以更冷静地看 SPR-032：

```text
读路径已经成立。
内部节点不是没信息。
问题是要为不同问题选择正确 decoder。
```

这也是下一阶段继续往 S1 走的基础。
