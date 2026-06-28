---
title: "[SPR-017] TreeHeap 的存在性证明：把 Claim 说清楚"
date: 2026-06-21
weight: 17
author: nio (Houming818) & Codex Review
description: "修正 TreeHeap proof 的三个 claim：循环寻址不是普通加法，A 是学习器归纳边界，B 是子结构 kernel，C 是前缀压缩和概率容器。"
tags: [SPR, TreeHeap, Experiment, Proof, Architecture]
---

# TreeHeap 的存在性证明：把 Claim 说清楚

上一篇 `SPR-016` 讲了一件事：

```text
TreeHeap 不是要推翻机器学习。
TreeHeap 是把机器学习接到一种高维、可寻址、可组合的结构对象上。
```

所以它和 Transformer 在大范式上是相通的：

```text
固定数学算子
+ 可学习参数
+ loss
+ gradient
+ update
```

Transformer 里：

```text
matmul / softmax / residual add 是固定算子
Wq / Wk / Wv / FFN 是可学习参数
```

TreeHeap 里我们现在倾向于这样分层：

```text
plus / address / subheap / kernel_search / fold 是固定算子候选
arr.value / primitive basis / world model slots 是可学习参数
```

但这里必须非常谨慎。

我们上一版实验 A 把这个规则放进去了：

```text
target = (cursor + 1) mod base
```

这不是普通整数加法。

普通整数里：

```text
11 + 2 = 13
```

它不等于：

```text
3
```

只有当我们明确进入模系统时，才能说：

```text
13 ≡ 3 (mod 10)
```

也就是说，`mod base` 不是“加法天然要折叠”，而是一个有限容量系统里的回绕规则。它更像 circular buffer：

```text
cursor = (cursor + 1) mod base
arr[cursor] = value
```

所以当前实验 A 不能被说成：

```text
证明了 TreeHeap plus。
```

它只能被说成：

```text
证明了学习器在模地址回绕 toy task 上的归纳边界。
```

这篇文章就是把三个实验的 claim 重新钉牢。

## 三个实验到底在 Claim 什么

先给结论。

| 实验 | 当前真正测的东西 | 当前能 claim 什么 | 当前不能 claim 什么 |
|---|---|---|---|
| A | circular addressing toy task | 普通学习器从短样本模仿模地址规则时存在归纳边界 | 不能证明完整 TreeHeap plus/fold，不能证明 TreeHeap learner 已经赢 |
| B | subheap kernel relocation | 显式树堆地址上的局部 kernel 可以稳定迁移 | 不能证明语言结构已经学会 |
| C | prefix compression + probability container | 共享路径前缀可以压缩 toy 分布，并保留候选概率 | 不能证明真实语言翻译质量提升 |

这三个实验现在只是数学工具箱的第一层 toy proof。它们不是 WMT 证明，也不是 TreeHeap 语言模型证明。

## 实验 A：循环寻址规则的归纳边界

### 当前 A 实际做了什么

当前 A 的状态是一个有限容器：

```text
State = {
  arr,
  root = arr[0],
  cursor,
  base,
  summary
}
```

当前 A 的写入规则是：

```text
circular_write(H, p):
  target = (cursor + 1) mod base
  arr[target] = p
  cursor = target
  summary = summarize(arr)
  return H
```

这个规则有闭包：

```text
H 是有限状态容器
circular_write(H, p) 仍然是有限状态容器
```

但是它不是普通加法，也不是完整 TreeHeap plus。

更准确地说：

```text
plus:
  n -> n + 1
  不折叠。

mod plus:
  n -> (n + 1) mod base
  有限容量回绕。

fold plus:
  容量满后不是简单覆盖，而是把旧结构折叠进 summary / parent node。
```

当前 A 只做了第二种：`mod plus`。

### A 的训练操作

脚本生成很多 primitive 序列：

```text
[p0, p1, p2, ..., pn]
```

然后用固定规则生成答案：

```text
target_address = (length - 1) mod base
read_value = 最后一次写入 query_addr 的 token
```

训练时只给短序列：

```text
train length <= 8
```

测试时给：

```text
test length = 8 / 16 / 32 / 64
```

参与训练的模型是：

```text
flatten MLP
small Transformer
```

还有一个 `rule oracle`：

```text
rule oracle = 直接执行 circular_write 的参考实现
```

这个 `rule oracle` 不是训练出来的 TreeHeap 模型。它只是标准答案生成器。

所以 A 的有效证据不是：

```text
TreeHeap learner 取得 1.0。
```

而是：

```text
MLP / Transformer 在模地址规则上，从短样本外推到长样本时会出现边界。
```

### A 的 8 小时结果

flatten MLP 的读值能力：

| test length | read accuracy |
|---:|---:|
| 8 | 0.1827 |
| 16 | 0.0593 |
| 32 | 0.0567 |
| 64 | 0.0406 |

small Transformer 的 address accuracy：

| test length | address accuracy |
|---:|---:|
| 8 | 0.9997 |
| 16 | 0.9955 |
| 32 | 0.9804 |
| 64 | 0.9292 |

这说明：

```text
MLP 没有稳定学会 read-after-overwrite。
Transformer 更强，但在长长度上也有下降和失败样本。
```

### A 的准确 Claim

```text
Claim A:
在 circular addressing toy task 上，
普通学习器从短样本模仿规则时存在归纳边界。
```

A 不能 claim：

```text
完整 TreeHeap plus 已经成立。
完整 TreeHeap fold 已经成立。
TreeHeap learner 已经优于 Transformer。
```

下一步必须把 A 拆成：

```text
A1: unbounded successor
    11 + 2 = 13，不做 mod。

A2: bounded circular addressing
    13 ≡ 3 (mod 10)，这是有限容量回绕。

A3: fold write
    容量满后做结构折叠，不是简单覆盖。
```

这才是严谨的 TreeHeap algebra proof。

## 实验 B：子结构 Kernel 搜索

### B 实际做了什么

B 定义一个局部模式：

```text
      A
     / \
    B   C
```

在数组里就是：

```text
[arr[i], arr[left(i)], arr[right(i)]]
```

训练时 pattern 只出现在：

```text
train positions = {0, 1, 2}
```

测试时放到新地址：

```text
test positions = {6, 10, 13}
```

TreeHeap kernel 的做法是：

```text
for each address i:
  sub = subheap(H, i)
  score[i] = match(sub, K)

answer = max(score)
```

这就是树堆空间里的卷积。

### B 的 8 小时结果

| method | accuracy mean | min | max |
|---|---:|---:|---:|
| TreeHeap kernel | 1.0000 | 1.0000 | 1.0000 |
| flatten MLP | 0.4996 | 0.4258 | 0.5703 |
| sequence CNN | 1.0000 | 1.0000 | 1.0000 |
| small Transformer | 0.9846 | 0.6055 | 1.0000 |

这组结果不能被解释成“只有 TreeHeap 能做”。CNN 也满分，说明这个任务本质就是局部 kernel 迁移。

更准确的解释是：

```text
局部模式 + 可复用 kernel 是强归纳偏置。
TreeHeap 的价值在于把这种 kernel 从线性/网格空间推广到树堆地址空间。
```

### B 的准确 Claim

```text
Claim B:
如果局部模式定义在树堆地址上，
显式 subheap kernel 可以稳定做 relocation。
```

B 能支持：

```text
TreeHeap 可以拥有类似卷积的结构算子。
```

B 不能支持：

```text
语言结构已经学会。
复杂树变换已经解决。
TreeHeap 在所有结构任务上优于 Transformer。
```

下一步 B 要加难度：

```text
新深度
兄弟交换
局部噪声
缺失子节点
多 kernel 同时存在
kernel composition
```

## 实验 C：前缀压缩和延迟坍缩

### C 实际做了什么

C 构造共享前缀序列，例如：

```text
A B C X
A B C Y
A B D X
A B D Y
A E F X
```

普通序列会重复保存这些路径。

前缀树可以共享：

```text
A
├── B
│   ├── C
│   │   ├── X
│   │   └── Y
│   └── D
│       ├── X
│       └── Y
└── E
    └── F
        └── X
```

共享前缀意味着可以共享：

```text
存储
计算
summary
候选概率
```

给定前缀：

```text
A B C
```

后面可能是：

```text
X or Y
```

TreeHeap 可以在前缀节点上保留候选概率：

```text
A-B-C -> {
  X: 0.5
  Y: 0.5
}
```

这就是概率容器。它不急着 `argmax`，而是等待更多上下文。

### C 的 8 小时结果

| metric | value |
|---|---:|
| sequence_node_count | 800 |
| prefix_tree_node_count | 11 |
| compression_ratio_mean | 72.7273 |
| prefix_reuse_rate_mean | 0.98625 |
| new_branch_Z_probability_after_one_mean | 0.01249 |

这说明在这个 toy 分布里：

```text
800 个普通序列节点
可以压成 11 个前缀树节点。
```

新分支 `Z` 出现一次后，没有直接覆盖旧候选，而是以小概率进入候选容器：

```text
P(Z) ≈ 0.01249
```

### C 的准确 Claim

```text
Claim C:
共享路径前缀可以显著压缩 toy 分布，
并且可以在前缀节点保留候选概率。
```

C 能支持：

```text
TreeHeap 的路径不是普通 token 序列。
路径前缀可以成为存储、计算、概率容器的共享对象。
```

C 不能支持：

```text
真实语言中的前缀压缩率也这么高。
delayed collapse 已经提升翻译质量。
概率容器已经学会语义消歧。
```

下一步 C 要提高难度：

```text
更多分支
更高 entropy
更少重复
上下文反转候选概率
概率校准
delayed-collapse accuracy
```

## 总结：现在我们到底知道什么

现在最稳的结论是：

```text
TreeHeap 的存在性还没有被完整证明。
但是三个 toy 实验给出了三个方向的信号。
```

这三个方向分别是：

```text
A: 地址规则不应该完全靠模型从样本里猜。
B: 子结构 kernel 可以成为树堆空间的卷积工具。
C: 路径前缀可以成为压缩和概率容器。
```

更严谨地说：

```text
TreeHeap 的 claim 不是“我也能学习”。
Transformer 也能学习。

TreeHeap 的 claim 是：
如果把地址、子结构、路径前缀、概率容器做成显式数学对象，
模型可能获得更好的结构归纳偏置。
```

但这还需要下一轮 proof：

```text
A1/A2/A3: plus / mod / fold 拆分
B2: kernel composition 和结构变换
C2: 高熵概率容器和上下文坍缩
```

只有这些 proof 更稳以后，语言任务才应该站在这个数学工具箱上。

> **License: GPLv3**
