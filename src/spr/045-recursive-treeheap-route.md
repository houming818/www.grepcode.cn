---
title: "[SPR-045] 重做 S1 route：矩阵不是 TreeHeap，递归路径才是"
date: 2026-07-05
author: Codex Review
description: "删除并重写 SPR-041/043/044 的路线：区分 flat LxL route matrix 和真正的 recursive TreeHeap stop/left/right route，并给出 WMT-massive proof。"
tags: [SPR, TreeHeap, ARA, S1, Echo, Routing]
---

# 重做 S1 route：矩阵不是 TreeHeap，递归路径才是

这篇是一次纠错。

之前 SPR-041、SPR-043、SPR-044 里有一类说法写过头了：

> 用 TreeHeap route 把 mirror / flip 后的句子恢复回来。

后来 DS 做代码审计时指出一个关键问题：这些实验里的 learned inverse route 实际上不是 TreeHeap route，而是一个可学习的平面矩阵。

也就是这种东西：

```python
route_logits[length, out_pos, in_pos]
route = softmax(route_logits[length])
state = route @ leaf
```

它能学会把第几个输入位置搬到第几个输出位置。

但是它不是 TreeHeap。

## 为什么 LxL 矩阵不是 TreeHeap

一个 `L x L` route matrix 做的是：

```text
output_position_i
  = sum_j route[i, j] * input_position_j
```

它的世界里只有：

```text
第 0 个 token
第 1 个 token
第 2 个 token
...
```

没有：

```text
arr[1]      root
arr[2i]     left child
arr[2i+1]   right child
```

也没有：

```text
当前在树的哪个 node
下一步走 left 还是 right
什么时候 stop
当前 node 的 subheap 是什么
```

所以它最多叫：

```text
flat sequence route
```

不能叫：

```text
TreeHeap route
```

这不是文字洁癖。这里差别很大。

如果我们说 TreeHeap 是一种数学结构，那么 proof 里的代码必须真的使用这个结构。不然就是拿矩阵贴了一个 TreeHeap 标签。

## 重新定义：什么才算 TreeHeap route

这次我们把规则写死。

一个合法的 TreeHeap route 必须长这样：

```text
i = 1

while not stop:
    S_i = [arr[i], arr[2i], arr[2i+1]]
    action = K_theta(q, S_i, address_i)

    if action == left:
        i = 2i

    if action == right:
        i = 2i + 1

    if action == stop:
        return arr[i]
```

这里有四个硬条件：

| 条件 | 含义 |
|---|---|
| `arr[i]` | 数据真的放在堆地址上 |
| `arr[2i] / arr[2i+1]` | 左右孩子是真的树结构 |
| `stop/left/right` | route 是一步一步走出来的 |
| action trace | evidence 里能看到走过哪些边 |

没有这些，就不叫 TreeHeap route。

## 这次 proof 要证明什么

我们不直接跳到翻译。

这次只证明一个很小的东西：

> 给定一个被 TreeHeap mirror 过的句子，模型能不能从 `arr[1]` 开始，通过递归 `stop/left/right` 路径，把原句读回来？

注意，这里有两个动作：

1. **扰动**：用 TreeHeap 的 `mirror(root)` 把整棵树翻转。
2. **恢复**：不用 `L x L` 矩阵，而是用 recursive route 从 root 一步一步走到目标 leaf。

## 数据怎么构造

数据来自：

```text
/mnt/nas/datasets/wmt_massive/train.massive.zh-en.tsv
```

这次取英文侧短句：

```text
samples = 20,000
heap max_len = 32
train lengths = 3..24
OOD lengths = 25..32
```

也就是说：

- 训练时只看长度不超过 24 的句子；
- 测试时看长度 25 到 32 的句子；
- 这样可以检查旧式 `route_logits[length, ...]` 是否只是记住了每个长度的一张表。

## TreeHeap mirror 是什么

假设有 32 个 leaf。

原句写入 leaf：

```text
leaf 0  leaf 1  leaf 2  ... leaf 31
w0      w1      w2          PAD
```

整树 mirror 后：

```text
leaf 0  leaf 1  ... leaf 29 leaf 30 leaf 31
PAD     PAD         w2      w1      w0
```

所以如果我们想恢复 canonical position `p`，应该去 mirror 后的：

```text
target_leaf = 31 - p
```

例如：

```text
p = 0
target_leaf = 31
```

在堆里，32 个 leaf 的 node 编号是：

```text
leaf 0  -> node 32
leaf 31 -> node 63
```

所以读取 `p=0` 时，route 应该从 root `node 1` 一路走到 `node 63`。

## 递归路径长什么样

实验里保存了 action trace。

一个 OOD 例子：

```json
{
  "pos": 0,
  "target_leaf": 31,
  "actions": [2, 2, 2, 2, 2, 0],
  "node": 63
}
```

这里约定：

```text
0 = stop
1 = left
2 = right
```

所以这条路径是：

```text
root
-> right
-> right
-> right
-> right
-> right
-> stop
```

也就是：

```text
arr[1]
-> arr[3]
-> arr[7]
-> arr[15]
-> arr[31]
-> arr[63]
```

这才是 TreeHeap route。

## 对照组：旧的 flat route matrix

我们也保留了旧方法作为 baseline：

```text
route_logits[length, out_pos, in_pos]
```

它在训练长度 `3..24` 上可以学得很好。

但是 OOD 长度是 `25..32`。

因为它是“每个 length 一张表”，没有见过的长度对应的表没有被训练过。

所以它应该失败。

这个 baseline 很重要，因为它帮助我们区分：

```text
真的学了 TreeHeap 地址规律
```

和：

```text
只是记住了长度对应的位置矩阵
```

## 实验结果

脚本：

```text
ara/s1-echo/src/s1_recursive_treeheap_route_probe.py
```

evidence：

```text
ara/s1-echo/evidence/s1_recursive_treeheap_route_probe/
```

结果：

| 指标 | 数值 |
|---|---:|
| hard TreeHeap oracle OOD exact | `1.0000` |
| learned recursive route OOD exact | `1.0000` |
| learned recursive route OOD token acc | `1.0000` |
| flat length-matrix OOD exact | `0.0000` |
| flat length-matrix OOD token acc | `0.0097` |

pass checks：

```json
{
  "oracle_ood_exact": true,
  "recursive_ood_exact_ge_0_99": true,
  "recursive_uses_step_actions": true,
  "flat_length_matrix_fails_unseen_lengths": true
}
```

这次 proof 通过。

## 这个结果说明什么

它支持一个很窄但很重要的 claim：

> TreeHeap mirror recovery 可以用递归 `stop/left/right` 路由实现，而不必退化成 `L x L` 平面矩阵。

也就是说，我们终于把这两个东西分开了：

```text
flat route matrix:
  一个序列位置重排器
  可以有用
  但不是 TreeHeap

recursive TreeHeap route:
  从 arr[1] 出发
  每一步看当前子堆
  输出 stop / left / right
  在堆地址上移动
```

这就是 SPR-045 的核心价值。

它不是更大模型。

它是把数学对象认清楚。

## 它没有证明什么

这篇不能被扩大解释。

它没有证明：

- TreeHeap 已经会翻译；
- TreeHeap 已经理解语义；
- 模型能自己发现该翻哪个 span；
- 模型能从自然语言里自动学到“时间状语前置”之类的翻译规律；
- TreeHeap 一定优于 Transformer。

更准确地说：

```text
这次证明的是 route mechanism。
不是 language intelligence。
```

## 对旧博客的处理

旧的 SPR-041、SPR-043、SPR-044 已经删除。

不是因为数字全部无效。

而是因为它们把两个层级混在了一起：

```text
数字上：
  可学习矩阵确实能恢复 echo。

机制上：
  它不是 TreeHeap route。
```

所以旧结论必须降级：

| 旧实验 | 新解释 |
|---|---|
| SPR-041 | supervised canonicalization 数字有效，但 route 是 flat matrix |
| SPR-043 | TreeHeap flip 扰动有效，但 learned inverse 是 flat matrix |
| SPR-044 | WMT canonical echo 是 weak positive，但不是 path-route proof |

SPR-040 仍然保留，因为它证明的是 mirror 在堆地址和 kernel slot 上的代数等变性。

SPR-045 则补上了真正缺失的东西：

```text
recursive stop/left/right TreeHeap route
```

## 下一步

下一步不能又跳太大。

现在最合理的是做三个对照：

1. **flat shared route baseline**  
   不按 length 分表，而是共享一套矩阵，看看还能不能追上。

2. **pointer baseline**  
   用普通 pointer network 读位置，检查 TreeHeap route 是否真的有结构优势。

3. **弱化监督**  
   现在 target position 是给定的。下一步要逐渐减少这个条件，让模型开始学习“该读哪个 subheap”。

只有这些继续成立，S1 route 才能往 S2 翻译方向接。

这篇的结论很朴素：

> 不要拿矩阵冒充 TreeHeap。  
> TreeHeap proof 必须真的走树。

这次终于走树了。

> ARA: [S1 recursive TreeHeap route](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/s1_recursive_treeheap_route.md) / [evidence](https://github.com/houming818/sametime/tree/main/ara/s1-echo/evidence/s1_recursive_treeheap_route_probe) / [claims](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/claims.md)
