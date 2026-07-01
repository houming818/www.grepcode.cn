---
title: "[SPR-041] S1-echo 入场门槛：token 写入、结构读取和坍缩能一起训练吗"
date: 2026-07-01
weight: 41
author: nio (Houming818) & Codex Review
description: "SPR-041 proof：一个受控 S1-echo 小实验，验证 token 信息、结构路由和 token 坍缩可以从交叉熵 loss 中一起训练。"
tags: [SPR, TreeHeap, ARA, S1, Echo, Kernel]
---

# S1-echo 入场门槛：token 写入、结构读取和坍缩能一起训练吗

这篇回答一个很实际的问题：

```text
现在能不能开始做 S1-echo？
```

我的判断是：

```text
可以开始。

但要叫：
受控 S1-echo v0。
```

为什么加“受控”两个字？

因为我们现在能证明的是：

```text
token 信息可以被梯度写入。
结构读取 kernel 可以被梯度训练。
token 可以从 TreeHeap state 中坍缩读回。
```

但还不能证明：

```text
模型已经从真实语言里自己发现什么时候该 mirror。
模型已经知道英文到中文什么时候该时间状语前置。
模型已经会 WMT 翻译。
```

这几个是后面的 S1/S2/S3 问题。SPR-041 只负责开门。

## 为什么不是直接上 WMT 翻译

如果现在直接做 WMT，跨度太大。

失败了，我们不知道是哪里失败：

```text
token 写不进去？
结构 kernel 不会读？
decoder 不会坍缩？
mirror 不会触发？
世界模型坐标不对？
loss 设计不对？
训练数据太少？
```

所以 SPR-041 做一个很小的受控任务。

它只问：

```text
能不能把 token 写入 TreeHeap，
再根据结构任务读出来，
最后坍缩成 token？
```

这就是 S1-echo 的最小闭环。

## 任务怎么设计

输入是 4 个 token：

```text
[t0, t1, t2, t3]
```

还有一个任务标记：

```text
task = echo
```

或者：

```text
task = mirror
```

如果是 echo，目标输出就是原序列：

```text
[t0, t1, t2, t3]
```

如果是 mirror，目标输出就是左右翻转：

```text
[t3, t2, t1, t0]
```

注意，这里 task 是给定的。

所以这个实验不是证明：

```text
模型自己知道什么时候该 mirror。
```

它证明的是更基础的一步：

```text
当结构任务给定时，
TreeHeap echo loop 能不能学会执行这个结构读取。
```

## TreeHeap 里发生了什么

我们把 4 个 token 写到 4 个有序叶子地址：

```text
leaf0 leaf1 leaf2 leaf3
```

每个 token 有一个可学习向量：

```text
E[token]
```

这就是 token 写入。

然后模型有两个结构读取 kernel：

```text
kernel_0
kernel_1
```

每个 kernel 都是一个 soft route：

```text
output slot -> input leaf address
```

例如 echo kernel 应该学到：

```text
out0 <- leaf0
out1 <- leaf1
out2 <- leaf2
out3 <- leaf3
```

mirror kernel 应该学到：

```text
out0 <- leaf3
out1 <- leaf2
out2 <- leaf1
out3 <- leaf0
```

再用一个 task gate 决定当前任务更应该使用哪个 kernel。

最后 decoder 把读出的向量坍缩回 token id。

整体是：

```text
token ids
-> TreeHeap leaf write
-> path-conditioned read kernel
-> task-conditioned structural route
-> token collapse decoder
```

## 数学写法

对每个 token：

```text
v_i = E[t_i]
```

对每个输出位置 `j`：

```text
r_{k,j,i} = P(input leaf i | kernel k, output slot j)
```

task gate 给出：

```text
g_k = P(kernel k | task)
```

那么读出的状态是：

```text
h_j =
\sum_k g_k
\sum_i r_{k,j,i} v_i
```

然后：

```text
logits_j = Decoder(h_j)
```

训练 loss 是普通 token cross entropy：

```text
L = CE(logits, target_tokens)
```

也就是说，梯度会同时进入：

```text
E[token]
route_logits
task_gate
decoder
```

这正是我们想看的：

```text
token 信息学习
结构 route 学习
token 坍缩学习
```

能不能在同一个 S1 echo loop 里发生。

## 为什么需要 baseline

如果没有 baseline，这个实验很容易被误解成：

```text
只是背了 token。
```

所以我们加了一个对照模型：

```text
no-task single-kernel baseline
```

它也有 token embedding 和 decoder。

但它只有一个固定 read kernel，没有 task gate。

也就是说，它必须用同一个读取方式同时解决：

```text
echo
mirror
```

这在结构上是不合理的。

如果 TreeHeap echo gate 真的利用了结构任务，它应该明显赢过这个 baseline。

## 实验结果

脚本：

```text
ara/s1-echo/src/s1_echo_entry_gate_probe.py
```

证据：

```text
ara/s1-echo/evidence/s1_echo_entry_gate_probe/
```

主机：

```text
io.grepcode.cn
```

结果：

| 指标 | 数值 |
|---|---:|
| pilot_pass | `true` |
| TreeHeap OOD token acc | `1.000000` |
| TreeHeap OOD exact | `1.000000` |
| TreeHeap route argmax ok | `1.000000` |
| echo task 选择 identity kernel 概率 | `0.968449` |
| mirror task 选择 mirror kernel 概率 | `0.810727` |
| no-task single-kernel baseline OOD exact | `0.090820` |

解释一下。

TreeHeap controlled echo 在 OOD 随机样本上：

```text
token 全对。
整句全对。
route argmax 全对。
```

baseline 只有：

```text
0.090820 exact
```

这说明一个固定读取 kernel 很难同时处理 echo 和 mirror。

而 TreeHeap 模型通过 task gate 和结构 read kernel，把两个任务分开了。

## 一个重要细节：mirror gate 没有完全硬坍缩

mirror task 选择 mirror kernel 的概率是：

```text
0.810727
```

不是：

```text
0.999999
```

这不是坏事。

在 SPR 的语言里，它更像一个概率容器：

```text
当前足够偏向 mirror，
但还没有完全硬坍缩。
```

因为 route 和 decoder 也参与了补偿，所以最后输出仍然完全正确。

因此这里的结论应该写准确：

```text
模型学到了足够强的结构偏好，
并且输出坍缩正确。
```

而不是夸张成：

```text
模型已经完美硬选择 mirror 操作。
```

## 这支持了什么

SPR-041 支持：

```text
S1-echo 可以启动。
```

更具体地说：

```text
TreeHeap 已经具备一个最小可训练闭环：

1. token 写入
2. 结构读取
3. 概率选择
4. token 坍缩
5. 交叉熵训练
```

它也连接了前几篇：

```text
SPR-038:
  heap state 可以通过梯度 relaxation。

SPR-039:
  kernel 参数 Theta 可以通过梯度学习。

SPR-040:
  mirror 的 left/right 槽位赋值可以通过 loss 学回。

SPR-041:
  token + 结构 route + collapse 可以放到一个 S1 echo loop 里训练。
```

所以，现在从 M0 走到 S1 是合理的。

## 还不能证明什么

这篇没有证明：

```text
WMT 翻译
真实语义理解
自然语言 mirror trigger
时间状语前置
递归 mirror 深度选择
Transformer superiority
长句法结构
```

最关键的边界是：

```text
task flag 是给定的。
```

也就是说，我们还没证明：

```text
模型能从 token/context 里自己判断该用哪个结构操作。
```

这就是下一步。

## 下一步怎么做

我建议 S1-echo 下一步分成三关。

### 第一关：去掉人工 task flag

现在是：

```text
task -> gate
```

下一步要变成：

```text
tokens + context -> gate
```

也就是让模型从输入内容里判断：

```text
该 echo？
该 mirror？
该 mask restore？
该局部 reorder？
```

这才开始接近真实语言。

### 第二关：加入 mask/noise restore

纯 echo 容易变成复制。

所以要加入：

```text
输入缺 token
输入 token 被噪声替换
输入顺序被局部打乱
```

然后要求模型复原。

这样才能测试：

```text
TreeHeap 是否真的学到了结构，
而不是只做原样拷贝。
```

### 第三关：回到短 WMT BPE

等受控任务过了，再回到：

```text
WMT short BPE
```

但仍然先做 echo / restore。

不要直接翻译。

翻译是 S2/S3 的事。

S1 先证明：

```text
真实 token 序列可以被写入、读取、修复、坍缩。
```

## 给 DeepSeek 的审核重点

DeepSeek 不需要发布前帮我们吹结论。

需要做三件事：

```text
1. 审核 S1-ECHO-GATE-C01 能否作为 S1-echo v0 entry gate。
2. 检查 evidence 是否支持 controlled pilot，而不是更强 claim。
3. 建议下一步 baseline：flat MLP、small Transformer、copy-capable seq model，哪个最该补。
```

验收条件很明确：

```text
如果 DS 同意：
  当前 claim 只能是 controlled S1 entry proof；
  不升级成 translation/trigger/semantic proof；
  evidence 文件完整；

那么再回来找 Codex 推进下一轮：
  learned trigger + noise/mask restore。
```

## 一句话总结

SPR-041 证明了一件小但关键的事：

```text
TreeHeap 的 S1 echo loop 可以训练起来：
token 能写入，
结构 route 能学习，
token 能坍缩读回。
```

所以：

```text
可以开始 S1-echo。
```

但现在只能说：

```text
受控 S1-echo v0。
```

下一步才是更难的问题：

```text
不再给 task flag，
让模型从 token/context 中自己学会选择结构操作。
```

> ARA: [S1 echo entry gate](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/s1_echo_entry_gate.md) / [evidence](https://github.com/houming818/sametime/tree/main/ara/s1-echo/evidence/s1_echo_entry_gate_probe) / [claims](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/claims.md)
