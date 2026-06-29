---
title: "[SPR-032] TreeHeap 的概率读取核：从 arr[1] 开始的 stop/left/right 坍缩"
date: 2026-06-29
weight: 32
author: nio (Houming818) & Codex Review
description: "这篇记录 SPR-032：把 TreeHeap read 从 root bottleneck 改成 query-conditioned probabilistic read kernel。实验说明路径坍缩和叶子读取成立，但内部子堆摘要还没解决。"
tags: [SPR, TreeHeap, ARA, S1, WMT, Kernel, Read]
---

# TreeHeap 的概率读取核：从 arr[1] 开始的 stop/left/right 坍缩

SPR-031 的结论里有一个明显问题：

```text
我们让 root/subheap state 一次性吐出答案。
```

这会形成 root bottleneck。

如果答案在左子树、右子树、某个叶子，或者某个内部子堆里，那么更自然的做法不是让 root 背下所有东西，而是从 root 开始读取：

```text
arr[1]
  -> stop
  -> left
  -> right
```

每一步都由一个 kernel 决定。

所以 SPR-032 的问题是：

```text
TreeHeap read 能不能写成一个概率路径坍缩过程？
```

结论先说：

```text
路径坍缩成立。
叶子读取几乎成立。
内部子堆摘要还没成立。
```

ARA 状态：

```text
S1-READ-C01 -> open / mixed pilot
```

## 什么叫 read kernel？

我们先把 TreeHeap 当成一个数组堆：

```text
arr[1] = root
arr[2] = left(root)
arr[3] = right(root)
arr[4] = left(left(root))
arr[5] = right(left(root))
...
```

一个读取核可以写成：

```math
K_{read}(q, h_i, p_i) \rightarrow P(stop), P(left), P(right)
```

含义是：

- `q`：这次要读什么，也就是 query。
- `h_i`：当前节点的 TreeHeap state。
- `p_i`：当前节点的路径/地址信息。
- 输出：在当前节点停止、走左边、走右边的概率。

如果输出是硬选择，就是：

```text
while true:
    action = K_read(query, current_node)
    if action == stop:
        return current_node_state
    if action == left:
        current_node = current_node.left
    if action == right:
        current_node = current_node.right
```

这就是尾递归，也可以直接写成循环。

如果输出是概率，就不是只走一条路，而是维护一个 frontier：

```text
root mass = 1.0
每一层：
  一部分概率 stop 到当前节点
  一部分概率流向 left
  一部分概率流向 right
最后把所有 stop 的状态加权求和
```

这就是 soft read。

## stop 不是空操作

你之前说的这个例子很关键：

```text
root_left_right = [stop_0.5, left_0.3, right_0.2]
```

这里 `stop` 不是“什么也不做”。

它的意思是：

```text
就在当前节点读取。
```

如果当前节点是叶子：

```text
stop -> 读一个 token
```

如果当前节点是内部节点：

```text
stop -> 读一个子堆摘要
```

所以 TreeHeap 不是 B+ 树那种“只有叶子有数据”的结构。TreeHeap 的内部节点也应该有意义。

这次实验专门把内部 stop 做成可测量目标。

## 实验怎么做？

数据来自真实 WMT17 英文侧文本：

```text
/mnt/nas/datasets/wmt17/train.zh-en
```

切词模型：

```text
/mnt/nas/datasets/wmt17/sp_bpe.model
```

样本设置：

```text
samples = 3000
train/test/ood = 2400/300/300
token length = 4..8
vocab limit = 513
```

我们把一个短 BPE 序列写入 8 个叶子：

```text
tokens = [t0, t1, t2, t3, ...]

arr[8]  = t0
arr[9]  = t1
arr[10] = t2
...
```

然后随机给一个 query node。

如果 query 是叶子，比如 `arr[10]`：

```text
目标 = 这个叶子的 token id
```

如果 query 是内部节点，比如 `arr[2]`：

```text
目标 = arr[2] 覆盖的子堆 span 的 checksum bucket
```

checksum 是一个玩具摘要。它不是语言语义，只是为了让内部 stop 有一个明确答案。

也就是说：

```text
叶子 stop     -> 复制 token
内部节点 stop -> 输出子堆摘要
```

## 两个模型

第一个是 root baseline：

```text
root_query_decoder:
  TreeEncoder(tokens) -> root state
  root state + query node id -> answer
```

它必须从 root state 里猜所有答案。

第二个是概率读取核：

```text
probabilistic_read_kernel:
  TreeEncoder(tokens) -> all node states
  q + current node + path -> stop/left/right
  stop 后再 readout answer
```

它不是让 root 背下所有答案，而是根据 query 走到目标节点。

## Run A：128 个内部摘要桶

设置：

```text
checksum_buckets = 128
epochs = 40
labels = 641
```

结果：

| Model | Params | OOD acc | OOD internal | OOD leaf | Route acc |
|---|---:|---:|---:|---:|---:|
| `root_query_decoder` | 398,209 | 0.0638 | 0.0205 | 0.1066 | n/a |
| `probabilistic_read_kernel` | 499,588 | 0.6124 | 0.2214 | 0.9989 | 1.0000 |

这说明：

```text
read kernel 比 root bottleneck 强很多。
路径路由完全学会了。
叶子 token 几乎完全读对。
内部摘要仍然很弱。
```

## Run B：32 个内部摘要桶

为了判断是不是摘要桶太难，我们把 checksum 从 128 桶降到 32 桶：

```text
checksum_buckets = 32
epochs = 80
labels = 545
```

结果：

| Model | Params | OOD acc | OOD internal | OOD leaf | Route acc |
|---|---:|---:|---:|---:|---:|
| `root_query_decoder` | 373,537 | 0.1184 | 0.0765 | 0.1598 | n/a |
| `probabilistic_read_kernel` | 474,916 | 0.7177 | 0.4332 | 0.9989 | 1.0000 |

内部摘要有提升：

```text
0.2214 -> 0.4332
```

但仍然没有达到“解决”的程度。

所以这不是单纯训练不够的问题。更可能是：

```text
当前 compose state 很适合保留叶子地址读取，
但还没有被设计成稳定的内部子堆摘要。
```

## 为什么 hard read 和 soft read 一样？

这次 hard read 是一条确定路径：

```text
root -> left -> right -> stop
```

soft read 是概率流：

```text
root mass = 1.0
mass 分到 stop/left/right
下一层继续分
```

因为路由已经学到接近确定：

```text
route_acc = 1.0000
```

所以 soft frontier 最后也几乎坍缩成同一条路径。

这很好理解：

```text
概率容器在信息不足时保留多条路。
当模型非常确定时，它自然坍缩成一条路。
```

## 这次证明了什么？

证明一：

```text
从 arr[1] 开始的 stop/left/right 读取过程是可学习的。
```

证明二：

```text
这个读取过程可以写成尾递归，也可以写成 soft frontier 概率传播。
```

证明三：

```text
对于叶子 token copy，它明显优于 root-only decoding。
```

Run A 的 OOD 对比：

```text
root OOD acc = 0.0638
read OOD acc = 0.6124
提升 = 0.5486
```

Run B 的 OOD 对比：

```text
root OOD acc = 0.1184
read OOD acc = 0.7177
提升 = 0.5992
```

这说明 TreeHeap 的地址、路径、局部节点状态确实被利用了。

## 这次没有证明什么？

没有证明翻译。

没有证明世界模型。

没有证明无监督路由。

没有证明长句法。

也没有证明内部子堆摘要已经解决。

最关键的负结果是：

```text
internal OOD acc 最高只有 0.4332
```

这说明：

```text
stop at internal node 的机制是对的，
但 internal node state 里面应该保存什么，还没设计好。
```

## 下一步怎么走？

SPR-032 把问题拆开了。

之前我们以为问题是：

```text
怎么读 TreeHeap？
```

现在更准确：

```text
路径坍缩怎么读：基本解决。
内部节点读什么：还没解决。
```

下一步应该把内部摘要目标换成更符合 TreeHeap 组合性的东西。

比如：

```text
subheap length
first token
last token
bag checksum
ordered checksum
learned phrase vector
```

不要一开始就用任意 checksum 桶硬压。checksum 可以当压力测试，但不一定符合 TreeHeap compose 的自然代数。

还需要加 baseline：

```text
small Transformer read baseline
pointer/copy baseline
matched flat MLP
```

并且要测试：

```text
如果不给 teacher route，
只给最终 answer loss，
read kernel 能不能自己学会走路？
```

这才是从监督路径读取走向真正结构学习的下一步。

## 总结

SPR-032 的结论很清楚：

```text
TreeHeap read 不应该再压在 root bottleneck 上。
它应该是从 arr[1] 开始的概率路径坍缩。
```

这条路已经被实验支持：

```text
route acc = 1.0000
leaf OOD acc = 0.9989
```

但内部节点的世界还没打开：

```text
internal OOD acc = 0.2214 / 0.4332
```

所以 C32 不是终点，而是把下一个问题照亮了：

```text
TreeHeap 的 internal node state，应该如何学习成为一个真正的子堆摘要？
```

这会是 S1 接下来最重要的问题之一。
