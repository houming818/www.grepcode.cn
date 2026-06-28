---
title: "[SPR-013] M0 纯数学实验：先让 TreeHeap 成为工具箱"
date: 2026-06-18
weight: 13
author: nio (Houming818) & Codex Review
description: "记录第一轮 M0 TreeHeap Math toy 实验：为什么先不做 WMT，怎么验证闭包、非交换、逆操作、投影和子堆核匹配。"
tags: [SPR, TreeHeap, Algebra, ARA, Math]
---

# M0 纯数学实验：先让 TreeHeap 成为工具箱

这篇文章记录一件更底层的事：

```text
先不要直接做 WMT。
先证明 TreeHeap 作为数学对象能不能被操作。
```

WMT 是最终任务。

但它不是好的早期诊断工具。

因为如果直接训练翻译系统，最后 BLEU 没涨，我们很难知道失败来自哪里：

```text
算子设计不对
世界模型没学到
loss 不合适
decoder 太弱
数据不够
训练没收敛
评估太粗
```

所以这次我们先建立一个更小的 ARA 主题：

```text
ara/m0-treeheap-math/
```

它的目标不是证明 TreeHeap 会语言推理。

它只问一个问题：

```text
TreeHeap 能不能先成为一个数学工具箱？
```

## 公开记录

公开实验仓：

```text
https://github.com/houming818/sametime
```

对应 ARA 入口：

```text
ara/m0-treeheap-math/logic/predicts.md
ara/m0-treeheap-math/logic/solution/algebra.md
ara/m0-treeheap-math/src/treeheap_math_probe.py
ara/m0-treeheap-math/evidence/treeheap_math_probe/summary.json
```

主仓内部路径：

```text
/home/nio/log/ara/m0-treeheap-math/
```

## 为什么这是 toy 实验

toy 不是玩具。

toy 的意思是：

```text
把问题缩小到刚好能看清楚。
```

如果我们要验证卷积核，第一步不会直接拿 ImageNet。

会先拿一个很小的矩阵：

```text
1 0 1
0 1 0
1 0 1
```

看看核匹配到底能不能找到局部模式。

TreeHeap 也是一样。

这次我们不使用：

```text
token
语法标签
WMT
BLEU
真实 checkpoint
```

只使用几个合成符号：

```text
A, B, C, D, E, R, T
```

然后构造几棵小树：

```text
H_ab = root(R, left=A, right=B)
H_ba = root(R, left=B, right=A)
H_cd = root(R, left=C, right=D)
H_nested = root(T, left=H_ab, right=E)
```

这个 toy 足够小。

小到我们知道正确答案。

也足够有用。

因为它能测试 TreeHeap 最基本的数学性质。

## 最小 TreeHeap 对象

第一版对象定义成：

```text
H = (name, v, head_v, slot, q, children)
```

字段含义：

| 字段 | 含义 |
|---|---|
| `name` | 合成对象名字，比如 `H_ab` |
| `v` | 整棵 TreeHeap 的结构向量 |
| `head_v` | root/head 参考向量 |
| `slot` | 当前节点的结构槽位 |
| `q` | 概率质量 |
| `children` | 子堆 |

这里最关键的是：

```text
v != head_v
```

`v` 是整体结构坍缩后的向量。

`head_v` 是根节点自己的参考量。

这个区别是实验跑出来的，不是预先拍脑袋定的。

## 这次测试哪些工具

第一批工具箱：

```text
compose
decompose
transpose
inverse_transpose
project
unproject
energy
match_subheap
probability container
```

对应要问的问题：

| 工具 | 问题 |
|---|---|
| `compose` | 两个子堆能不能合成一个合法 TreeHeap |
| `decompose` | 合成后能不能拆回子堆 |
| `transpose` | 左右结构交换后是否仍然可追踪 |
| `inverse_transpose` | 转置两次能不能回来 |
| `project` | 降维后是否还保留结构排序 |
| `energy` | 正确结构和扰动结构能不能拉开距离 |
| `match_subheap` | 小子堆核能不能在大树里找到对应部分 |
| `probability container` | 匹配结果能不能形成稳定概率分布 |

## 非交换性：AB 不等于 BA

如果 TreeHeap 只是普通加法：

```text
A + B = B + A
```

那它没法表达结构顺序。

所以我们给左右位置不同的结构基：

```text
v(H) = normalize(root + L @ left + R @ right)
```

其中：

```text
L != R
```

于是：

```text
H_ab = root(R, left=A, right=B)
H_ba = root(R, left=B, right=A)
```

会得到不同向量。

这就像数字：

```text
12 != 21
```

不是因为 1 和 2 变了。

而是因为位权变了。

实验结果：

```text
noncomm_margin = 0.7117
```

这说明左右交换后，结构空间里确实拉开了距离。

## 第一次失败：只有 v 不够

第一版实现里，我只保存了整体向量：

```text
H = (name, v, slot, q, children)
```

结果 `transpose` 出问题了。

我们希望：

```text
inverse_transpose(transpose(H)) ~= H
```

但第一次跑出来：

```text
transpose_inverse_error = 0.6248
```

这说明一个重要问题：

```text
只有坍缩后的整体向量 v，不足以支持精确逆操作。
```

原因很直接。

当一棵树已经合成为整体向量后，这个整体向量混合了：

```text
root
left
right
```

如果再拿它当 root 去重组，就会把整体误当成局部。

于是转置两次也回不来。

这不是坏事。

这是 toy 实验的价值。

它告诉我们 TreeHeap 对象定义漏了一个必要参考量。

## 修正：加入 head_v

修正后对象变成：

```text
H = (name, v, head_v, slot, q, children)
```

其中：

```text
head_v = root/head 自己的向量
v      = 整棵树合成后的向量
```

这样 `transpose` 时可以用原来的 head 重新组装，而不是把整体向量错当 root。

修正后：

```text
transpose_inverse_error = 0.0
```

这个结论很重要：

```text
TreeHeap 不能只是一个 collapsed vector。
它至少需要保留 root/head reference。
```

这也是从纯数学实验里得到的第一个设计约束。

## 子堆核匹配 toy

我们构造：

```text
H_nested = root(T, left=H_ab, right=E)
```

也就是：

```text
        T
       / \
    H_ab  E
    /  \
   A    B
```

然后用 kernel：

```text
K = H_ab
```

去 `H_nested` 里找匹配。

结果：

```text
subheap_hit_at_1 = 1.0
subheap_hit_at_3 = 1.0
```

匹配分数最高的是：

```text
H_ab
```

对应概率：

```text
0.9999798803
```

这说明在 toy 条件下：

```text
match_subheap(H_nested, H_ab)
```

能找到正确子堆。

## role swap 为什么看 margin

我们还测试了反向 kernel：

```text
K = H_ba
```

但 `H_nested` 里并没有真正的 `H_ba`。

这时系统仍然必须返回一个 top-1，因为概率容器总要在候选里排序。

它会把最接近的错误候选排前面。

所以不能只看：

```text
top1 是谁
```

还要看分数差。

结果：

```text
gold score = 1.0
role-swapped score on gold = 0.09085
role_swap_margin = 0.9091
```

这说明：

```text
H_ab 和 H_ba 在结构空间里不是同一个东西。
```

这正是我们想要的。

## 本轮结果

实验命令在 ni 上执行，CPU 即可，不使用 GPU。

结果摘要：

```text
pilot_pass = true
closure_ok = true
noncomm_margin = 0.7117
transpose_inverse_error = 0.0
compose_decompose_error = 0.0
projection_top1_preserved = true
projection_order_agreement = 0.8333
subheap_hit_at_1 = 1.0
subheap_hit_at_3 = 1.0
role_swap_margin = 0.9091
prob_mass_error = 0.0
```

对应证据文件：

```text
ara/m0-treeheap-math/evidence/treeheap_math_probe/summary.json
ara/m0-treeheap-math/evidence/treeheap_math_probe/README.md
ara/m0-treeheap-math/evidence/treeheap_math_probe/matches.jsonl
```

## 这证明了什么

它证明了一个很小但很关键的点：

```text
TreeHeap 可以先作为数学对象被操作。
```

至少在合成 toy 空间里，它支持：

```text
闭包
非交换
精确转置逆
compose/decompose
投影保持
子堆核匹配
概率容器归一
```

这给下一步 Echo 提供了更干净的地基。

## 它没有证明什么

它没有证明：

```text
TreeHeap 懂语言
TreeHeap 会翻译
TreeHeap 已经形成世界模型
SubHeap kernel 能处理真实句子
WMT 会涨分
```

这只是 M0。

但 M0 的意义是：

```text
先把尺子做出来。
```

没有尺子，直接看 BLEU，就像还没造好温度计就讨论天气。

## 下一步

路线应该是：

```text
M0 纯数学 TreeHeap
  -> M1 approximate inverse
  -> M2 TreeHeap-object echo
  -> M3 structure invariant
  -> S2 translation
```

下一步不应该直接回 WMT。

应该做：

```text
exact inverse
↓
approximate / learned inverse
```

也就是看看：

```text
不直接保存 children 的时候，
模型能不能从 TreeHeap 表示里近似拆回结构。
```

如果 M1 过了，再做 Echo。

Echo 也不再是旧的 token echo。

而是：

```text
TreeHeap object
↓
operator transformations
↓
reconstruct TreeHeap object
```

这样顺序更干净：

```text
数学成立
信息可保留
结构可识别
语言再利用
```

> **License: GPLv3**
