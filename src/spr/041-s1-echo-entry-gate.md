---
title: "[SPR-041] S1-echo 纠错：mirror 不是另一种读法，而是要先扭回 echo"
date: 2026-07-01
weight: 41
author: nio (Houming818) & Codex Review
description: "SPR-041 corrected proof：把错误的 task-gate 读法降级，改为 inverse gate canonicalization：mirror 输入先规约成 canonical echo state，再由同一个 decoder 读取。"
tags: [SPR, TreeHeap, ARA, S1, Echo, Kernel]
---

# S1-echo 纠错：mirror 不是另一种读法，而是要先扭回 echo

这篇是一次纠错。

我上一版 SPR-041 写错了方向。

上一版做的是：

```text
task = echo   -> 选择 identity read kernel
task = mirror -> 选择 mirror read kernel
```

看起来能跑，指标也好看。

但 Houming818 指出，这不是 TreeHeap 想要的结构。

真正应该做的是：

```text
如果输入是 mirror 结构，
先用一个对向 gate / inverse gate，
把 mirror 扭回 canonical echo state，
然后再用同一个 echo decoder 读取。
```

也就是说，不是：

```text
mirror -> mirror decoder/read
```

而是：

```text
mirror -> inverse mirror -> echo state -> echo decoder
```

这个差别非常关键。

## 为什么上一版是错的

上一版的模型可以选择不同 read kernel：

```text
echo 用 echo read。
mirror 用 mirror read。
```

这当然可以解决 toy task。

但它绕开了 TreeHeap 的核心目标：

```text
结构变换应该把输入规约到同一个参考系。
```

如果每种结构都用一种特殊 read kernel 直接读出，那就变成：

```text
为每种任务准备一个读法。
```

这不够好。

我们真正需要的是：

```text
先做结构规约，
再共享读取。
```

类比语言：

```text
I arrived home at 7 o'clock.
我七点到家了。
```

这里不是 decoder 背一个“英文尾部时间 -> 中文前置时间”的读法。

更合理的是：

```text
发现时间短语位置需要重排；
用一个结构 kernel 把它移到目标参考系；
然后统一读出。
```

所以 SPR-041 必须改。

## corrected 任务怎么设计

我们定义一个 canonical 序列：

```text
canonical = [t0, t1, t2, t3]
```

输入可能是 identity：

```text
observed = [t0, t1, t2, t3]
```

也可能是 mirror：

```text
observed = [t3, t2, t1, t0]
```

但目标永远是 canonical：

```text
target = [t0, t1, t2, t3]
```

所以任务不是：

```text
给 mirror，输出 mirror。
```

而是：

```text
给 mirror，先扭回 canonical，再输出 canonical。
```

这才是 inverse gate。

## 模型结构

模型有四个部分：

```text
E[token]
inverse_route_logits[op,out,in]
inverse_gate[transform,op]
echo_decoder
```

含义分别是：

```text
E[token]:
  token 写入 TreeHeap leaf 的向量。

inverse_route_logits:
  结构逆操作的路由 kernel。

inverse_gate:
  当前输入结构选择哪个 inverse operator。

echo_decoder:
  只负责从 canonical state 读 token。
```

整体流程是：

```text
observed tokens
-> leaf embeddings
-> inverse gate
-> canonical TreeHeap state
-> shared echo decoder
-> canonical tokens
```

注意最后只有一个 decoder。

这就是 corrected 版和上一版的根本区别。

## 数学写法

输入 token 写成 leaf 向量：

```text
v_i = E[observed_i]
```

inverse gate 给出：

```text
p(k | transform)
```

其中 `k` 是某个 inverse kernel。

每个 inverse kernel 给出一个 route：

```text
p(i | k, j)
```

表示 canonical slot `j` 应该从 observed leaf `i` 读取。

于是 canonical state 是：

```text
h_j =
sum_k p(k | transform)
sum_i p(i | k,j) v_i
```

然后统一 echo decoder：

```text
logits_j = EchoDecoder(h_j)
```

训练目标不是只有 token CE。

这次我们加入 canonical-state loss：

```text
L =
  CE(logits, canonical_tokens)
  + lambda_state * ||h - E[canonical_tokens]||^2
  + lambda_entropy * entropy(gate/routes)
```

为什么要加这个？

因为第一次 corrected proof 只用 CE 时，模型已经能把 token 输出对，但隐藏状态没有真的变成 canonical state。

换句话说：

```text
decoder 可以补偿。
```

这正是我们要避免的。

所以 corrected proof 必须要求：

```text
不仅输出 token 对，
中间 canonical state 也要接近真实 canonical leaf embedding。
```

这才是在证明“mirror 被扭回 echo”。

## 实验结果

脚本：

```text
ara/s1-echo/src/s1_echo_inverse_gate_probe.py
```

证据：

```text
ara/s1-echo/evidence/s1_echo_inverse_gate_probe/
```

主机：

```text
io.grepcode.cn
```

结果：

| 指标 | 数值 |
|---|---:|
| pilot_pass | `true` |
| canonical echo OOD exact | `1.000000` |
| inverse route argmax ok | `1.000000` |
| identity gate -> identity inverse | `0.999794` |
| mirror gate -> mirror inverse | `0.999784` |
| canonical state MSE | `0.000988962` |
| no-inverse baseline OOD exact | `0.218750` |

解释：

```text
identity 输入几乎完全选择 identity inverse。
mirror 输入几乎完全选择 mirror inverse。
route 的 argmax 全部对齐 identity/mirror 地址。
中间 state 接近 canonical leaf embedding。
同一个 echo decoder 可以读回 canonical token。
没有 inverse gate 的 baseline 明显失败。
```

这才是我们想要的 proof。

## 旧 proof 怎么处理

旧 proof 不删除。

它保留在：

```text
ara/s1-echo/evidence/s1_echo_entry_gate_probe/
```

但状态改为：

```text
downgraded / misdirected pilot
```

意思是：

```text
它证明了一件能跑但方向不对的事。
```

它的价值是提醒我们：

```text
高分不等于正确结构。
```

如果 loss 只看输出 token，它很容易让模型走捷径。

因此，TreeHeap 的 S1 loss 不能只问：

```text
输出对不对？
```

还要问：

```text
中间 TreeHeap state 是否真的进入了我们定义的参考系？
```

这就是这次纠错最重要的收获。

## 这说明了什么

SPR-041 corrected 支持：

```text
受控 S1-echo v0 可以开始。
```

但支持的是这个版本：

```text
observed structure
-> inverse/canonicalization gate
-> canonical TreeHeap state
-> shared echo decoder
```

而不是这个版本：

```text
task
-> choose separate output read kernel
-> decode
```

这和 TreeHeap 的产品逻辑更一致：

```text
先用结构算子把世界规约到参考系，
再在参考系里读取和坍缩。
```

## 还没有证明什么

这篇仍然没有证明：

```text
WMT 翻译
真实语义理解
自然语言自动触发 mirror
时间状语前置
递归深度选择
Transformer superiority
长句法结构
```

最关键的边界还是：

```text
transform flag 是给定的。
```

也就是说，模型现在知道：

```text
这个输入是 identity 还是 mirror。
```

下一步要让它从 token/context 中自己判断。

## 下一步

下一步不是再做一个“输出好看”的 echo。

下一步应该是：

```text
learned trigger + inverse canonicalization
```

也就是：

```text
tokens/context
-> trigger/gate
-> inverse structural operator
-> canonical state
-> shared decoder
```

再往后才是：

```text
mask/noise restore
variable-length WMT BPE
短句结构重排
S2 fold / translation
```

## 一句话总结

SPR-041 的正确结论是：

```text
mirror 不应该被当成另一种读法；
mirror 应该先被 inverse gate 扭回 canonical echo state。
```

corrected proof 表明：

```text
这个逆向规约可以被梯度学会，
中间 state 也能接近 canonical TreeHeap 表示，
然后由同一个 echo decoder 读回 token。
```

这才是 S1-echo 应该站上的入口。

> ARA: [S1 echo entry gate](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/s1_echo_entry_gate.md) / [corrected evidence](https://github.com/houming818/sametime/tree/main/ara/s1-echo/evidence/s1_echo_inverse_gate_probe) / [claims](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/claims.md)
