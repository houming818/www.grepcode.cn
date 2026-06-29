---
title: "[SPR-035] 一维数组如何折叠成 TreeHeap：先保序，再谈取模"
date: 2026-06-29
weight: 35
author: nio (Houming818) & Codex Review
description: "SPR-035 把一维有序数组折叠成 TreeHeap 的问题拆开：第一步必须保留叶子地址、路径和子树局部性；bag/root collapse 和过早 modulo fold 都会丢掉自然 internal readout。取模不是被否定，而是应该作为后续独立 folding kernel 研究。"
tags: [SPR, TreeHeap, ARA, S1, Fold Kernel, Ordered Structure]
---

# 一维数组如何折叠成 TreeHeap：先保序，再谈取模

SPR-034 修正了一个问题：

```text
internal node 不应该先预测任意 checksum。
它应该先读取 length / first / last / prefix 这种自然属性。
```

你随后指出一个更关键的点：

```text
residue 的引入有点生硬。
```

这个判断是对的。

你引入 residue，并不是为了让 SPR-034 证明模运算。
你真正想讨论的是：

```text
一维有序数组折叠成树结构时，
是否可能有模计算、周期、循环地址参与？
```

这是另一个问题。

所以 SPR-035 做一件更基础的事：

```text
把“一维数组 -> TreeHeap”的第一步说清楚。
```

我的结论先放前面：

```text
第一步必须保序。
也就是必须保留 leaf address、path、subheap locality。

取模可以研究，
但它应该是后续 folding kernel，
不能替代第一步的保序 TreeHeap fold。
```

## 为什么要先保序

假设有一个一维 token 数组：

```text
[a, b, c, d, e, f, g, h]
```

TreeHeap 把它写到叶子：

```text
              root
          /          \
      [a b c d]    [e f g h]
      /     \       /     \
   [a b]  [c d]  [e f]  [g h]
```

这个结构的关键不是“看起来像树”。

关键是每个 internal node 对应一个连续子区间：

```text
node 2 -> [a b c d]
node 3 -> [e f g h]
node 4 -> [a b]
node 5 -> [c d]
```

所以当我们问：

```text
node 5 的 first 是什么？
```

答案应该是：

```text
c
```

这依赖的不是语义，而是结构：

```text
一维顺序
+ 叶子地址
+ 树路径
+ 子树覆盖范围
```

如果第一步就把这些丢了，后面再做 read kernel、semantic decoder、probability collapse 都会很难。

## 三种折叠方式

这次 toy proof 比较三种 encoder。

### 1. ordered_tree_fold

这是正常 TreeHeap fold。

```text
token 按原始顺序写入 leaf
internal node 保存自己覆盖的子树摘要
```

它保留：

```text
地址
路径
左右结构
子树局部性
```

### 2. bag_root_fold

这是把整句话压成一个全局 bag/root summary。

```text
[a,b,c,d,e,f,g,h] -> 一个 root summary
```

它可能知道全局有哪些 token。
但它不知道：

```text
node 5 覆盖的是 [c,d]
```

所以它无法稳定回答局部子树问题。

### 3. modulo_fold

这是对你 residue 思路的一个诊断版本。

例如：

```text
position % 4
```

那么位置会被折叠成周期地址：

```text
0,4,8,... -> bucket 0
1,5,9,... -> bucket 1
2,6,10,... -> bucket 2
3,7,11,... -> bucket 3
```

这个操作不是错的。
它可能对周期任务、循环结构、某些 folding kernel 有意义。

但如果太早使用，它会把远处位置混在一起。
这会破坏自然子树 readout。

换句话说：

```text
modulo 是一个可能的后续算子，
不是第一步保序 fold 的替代品。
```

## 实验问题

我们用纯 toy 数据。
没有训练，没有 GPU，没有语义。

```text
samples = 5000
sequence length = 8..16
max_len = 16
vocab = 257
mod_base = 4
```

对每个序列，随机生成 token。
然后对 TreeHeap 的 internal node 提问：

```text
length
first
last
prefix0
prefix1
```

例子：

```text
seq = [172, 68, 175, 79, 147, 222, 130, 32,
       141, 188, 50, 187, 5, 6, 50, 254]

query_node = 6
span = [8, 12]
target = [141, 188, 50, 187]
```

正确答案：

```text
length  = 4
first   = 141
last    = 187
prefix0 = 141
prefix1 = 188
```

## 实验结果

结果如下：

| Model | Length | First | Last | Prefix0 | Prefix1 | Mean natural | Exact all |
|---|---:|---:|---:|---:|---:|---:|---:|
| `ordered_tree_fold` | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| `bag_root_fold` | 0.0888 | 0.3236 | 0.3236 | 0.3236 | 0.3235 | 0.2766 | 0.0888 |
| `modulo_fold_base4` | 0.0888 | 0.4032 | 0.4034 | 0.4032 | 0.4036 | 0.3405 | 0.0888 |

差距：

```text
ordered_tree_fold - bag_root_fold    = +0.7234
ordered_tree_fold - modulo_fold_base4 = +0.6595
```

这说明：

```text
保序 TreeHeap fold 可以精确读回自然子树属性。
bag/root collapse 不行。
过早 modulo fold 也不行。
```

## 这个实验证明了什么

这次 claim 是：

```text
S1-FOLD-C01:
Natural internal readout requires an order-preserving TreeHeap fold.
Leaf address/path structure must be preserved before any bag or modulo/cyclic folding is used.
```

状态：

```text
supported pilot
```

它证明的是一个演绎层面的结构事实：

```text
如果目标是自然子树 readout，
那么第一步 fold 必须保留一维顺序和树路径。
```

这不是深度学习结论。
它更像数学地基。

类似：

```text
如果你要从 321 里读百位、十位、个位，
你必须先保留位权结构。
```

TreeHeap 也是一样：

```text
如果你要读子树 first/last/prefix，
你必须先保留 leaf address/path/subheap。
```

## 这没有证明什么

它没有证明翻译。

它没有证明语义。

它没有证明 learned routing。

它没有证明 TreeHeap 胜过 Transformer。

它也没有证明 modulo 没用。

尤其最后一点很重要：

```text
modulo 没有被否定。
```

这次只说明：

```text
modulo 不应该替代第一步保序 fold。
```

如果后续任务本身具有周期结构，比如：

```text
循环地址
周期 pattern
ring buffer
某种 tree convolution 的 cyclic scan
```

那 modulo kernel 仍然可能有价值。

但那应该是另一个实验。

## 对 TreeHeap 路线的影响

现在 S1 的顺序更清楚了。

应该是：

```text
Step 1: ordered write
        一维 token 顺序写入 TreeHeap leaf

Step 2: ordered fold kernel
        internal node 保留自然子树属性

Step 3: probabilistic read kernel
        stop / left / right 走到目标节点

Step 4: natural readout
        length / first / last / prefix

Step 5: semantic decoder
        在自然结构 readout 上学习语义

Step 6: optional folding operators
        modulo / cyclic / mirror / conjugate / compression
```

这比之前更干净。

之前我们把 residue 混在 SPR-034 里，会让 claim 变得不好理解。

现在拆开后，逻辑是：

```text
保序 fold 是地基。
modulo fold 是候选算子。
```

## 下一步

我建议 SPR-036 做两条中的一条。

第一条，更贴近 S1：

```text
把 SPR-032 的 probabilistic route
接到 SPR-034/035 的 natural readout。
```

也就是端到端：

```text
arr[1]
-> stop/left/right collapse
-> target internal node
-> length/first/last/prefix
```

第二条，更贴近你的数学问题：

```text
专门设计 modulo/cyclic folding 任务。
```

但这个任务的目标不能再是普通子树 first/last。
它应该是一个真正周期性的目标。

比如：

```text
给定一个周期 kernel，
在 TreeHeap 地址空间里寻找同余类 pattern。
```

这样 residue 才是自然的。

## 总结

SPR-035 的一句话结论是：

```text
一维数组折叠成 TreeHeap 时，第一步必须保序。
```

保序意味着：

```text
leaf address
path
left/right
subheap locality
```

实验支持这个判断。

```text
ordered_tree_fold mean = 1.0000
bag_root_fold mean     = 0.2766
modulo_fold mean       = 0.3405
```

所以我们不再把 residue 强塞进 SPR-034。
它应该进入另一条更专业的线：

```text
cyclic / modulo folding kernel
```

今晚的推进是把地基重新摆正：

```text
先保序，再折叠；
先自然 readout，再语义 decoder；
先结构清楚，再研究 modulo。
```
