---
title: "[SPR-002] S1 实验：Echo、顺序哈希与容量证据"
date: 2026-06-16
weight: 2
author: nio (Houming818) & Codex Review
description: "SPR S1 中已经成立的部分：顺序哈希修复、分解路由容量、Echo 复现。"
tags: [SPR, EchoTest, Evidence]
---

# S1 实验：Echo、顺序哈希与容量证据

S1 的任务是先证明路径结构能稳定工作。

它不处理完整语义，也不处理翻译。它只问：

> 路径机制能不能可靠地区分 token，并保留顺序信息？

## 实验脚本

复现脚本：

```text
holds/SameTime/experiments/spr_s1_reproduce.py
holds/SameTime/experiments/spr_s1_falsification.py
```

io 上运行：

```bash
cd /data/homecicd/sametime/code/wmt
sudo -n python3 spr_s1_falsification.py
```

## 1. pure roll 的顺序碰撞

设：

```text
我 = [1, 2, 3, 4]
你 = [5, 6, 7, 8]
```

如果父节点合并为：

```python
H = left + torch.roll(right, shifts=1)
```

会得到：

```text
我打你 -> [9, 7, 9, 11]
你打我 -> [9, 7, 9, 11]
```

两个方向完全相同。这说明 pure roll 不能独立承担顺序编码。

## 2. roll + sign_alt

修复方式是在右子树 roll 后加一个交替符号：

```python
def sign_alt(x):
    return x * [1, -1, 1, -1, ...]

H = left + sign_alt(torch.roll(right, shifts=depth+1))
```

同样的例子变成：

```text
我打你 -> [9, -3, 9, -3]
你打我 -> [9,  5, 9,  5]
```

实验输出：

```text
pure_roll_collision=True
sign_alt_separated=True
```

结论：

> S1 的顺序哈希需要非交换破缺。`roll + sign_alt` 是当前最小可用方案。

## 3. 分解路由容量

S1 把一个 64 维词向量切成 4 个 chunk：

```text
chunk0: dim 0..15
chunk1: dim 16..31
chunk2: dim 32..47
chunk3: dim 48..63
```

每个 chunk 走一棵深度 7 的树：

```text
2^7 = 128 leaves
```

四个 chunk 的叶子号组合：

```text
128^4 = 268,435,456 effective leaves
```

WMT14 英文词表规模：

```text
vocab=41429
```

结果：

```text
solo=41311/41429
solo_percent=99.72
bleu4=99.99
```

这说明几乎每个 token 都能独占组合叶子。

## 4. 这个结果证明了什么

它证明：

- 路径空间容量足够。
- 路径分配稳定。
- Echo 任务可以近乎无损。
- 顺序哈希可以避免最简单的反向碰撞。

它没有证明：

- token 理解上下文。
- path state 等于 semantic state。
- 同词多义会自动分流。

因此，S1 的正确定位是：

> Token Path Hash。

它是 SPR 的基础设施，不是完整语义路由。

> **License: GPLv3**
