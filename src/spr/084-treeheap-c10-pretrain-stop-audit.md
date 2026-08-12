---
title: "[SPR-084] 预训练成功迁移，STOP 却没有学会停止：TreeHeap C10 最近进展审计"
date: 2026-08-12
lastmod: 2026-08-12
weight: 84
author: Houming818 & Codex Review
description: "TreeHeap C10 完成自然语料预训练、WMT 迁移与三轮读取审计：预训练带来明确收益，但递归 READ 退化成了 Butterfly 变换后的叶层软池化。"
tags: [SPR, TreeHeap, Pretraining, WMT, Butterfly, FOLD, STOP, LeafPooling, ARA]
---

# 最近航到了哪里

距离上一篇公开进展已经有一段时间。这期间我们没有继续堆更多概念，而是把一个完整训练管线跑通，然后反过来审计模型到底学会了什么。

这次的 C10 管线分三步：

```text
自然语料预训练
    -> 同样的 TreeHeap checkpoint 进入 WMT 中英任务训练
    -> 用概率后验、路径干预和 STOP 分辨率实验做 proof check
```

结果不是简单的成功或失败，而是两个同时成立的事实：

1. **预训练确实把可迁移信息写进了 TreeHeap 参数。**
2. **递归 Decoder 没有学成我们期待的多分辨率读取协议，而是几乎把全部概率质量送到了 leaf。**

这两个结果并不矛盾。模型可以学到有用信息，却通过一条比预期更浅的读出路径使用它。

## 1. C10 实际训练了什么

C10 不是 Transformer，也不是把一个矩阵改名为 TreeHeap。模型合同记录为：

| 项目 | 配置 |
|---|---:|
| 模型类 | `ButterflyRecursive` |
| 参数量 | 34,448,396 |
| state / hidden | 256 / 256 |
| 最大 heap width | 256 |
| 地址通信 | XOR Butterfly |
| FOLD | learned lifting |
| READ | recursive probability container |
| 生成器 | GRU 自回归 Decoder |

数据首先写到 leaf。Butterfly 按地址执行可逆的信息交换，然后 learned lifting 逐层把左右子节点合成为 parent，同时保存 detail。Decoder 再从 root 开始，通过 STOP 和左右分支概率读取不同深度的节点。

因此需要分清三个问题：

```text
问题 A：H_state 里有没有学到信息？
问题 B：Butterfly 和 FOLD 是否真的参与了计算？
问题 C：READ 是否学会了有意义的分层读取？
```

最近实验给出的答案分别是：**有、参与了、没有学成。**

## 2. 预训练迁移是明确的正结果

预训练阶段读取 `/home/nio/datasets/pretrain` 的自然语料，并混入 25% 的 WMT 单语文本。模型训练了约一亿 token：

| 指标 | 数值 |
|---|---:|
| pretrain steps | 97,657 |
| pretrain tokens | 100,000,768 |
| 初始 valid NLL | 10.7237 |
| 最佳 valid NLL | 5.6804 |
| 墙钟时间 | 4.85 小时 |

随后我们构造两条完全等算力的 WMT 任务训练臂：

* `PT`：从预训练 checkpoint 开始；
* `SC`：从相同初始随机状态直接学习 WMT。

两条任务臂使用相同的数据流哈希、25,000 step 和 20,198,612 个任务 token。

| 任务结果 | PT，预训练后 | SC，从零训练 | PT 改善 |
|---|---:|---:|---:|
| test NLL，越低越好 | **5.4037** | 6.2920 | -0.8883 |
| token BLEU4，越高越好 | **5.0654** | 1.1711 | +3.8943 |

这组比较可以支持一个有限 Claim：

> 在相同 WMT 训练预算下，先用自然语料预训练的 TreeHeap 比从零开始更快得到较低的测试 NLL 和较高的 token BLEU。

它不能证明模型已经会可靠翻译。实际生成仍有错译、重复和关系混乱。这里证明的是**协议可以迁移**，不是产品已经完成。

## 3. 后验 proof 看到了条件信息，但信号仍弱

我们又比较了模型给出的下一 token 概率桶与语料经验分布。

| 模式 | JS，越低越接近语料 | 候选集合概率质量，越高越好 |
|---|---:|---:|
| Native source | **0.6094** | **0.0620** |
| Wrong source | 0.6380 | 0.0388 |
| Unigram baseline | 0.6410 | 0.0333 |

换错 source 后，78.6% 的 greedy token 发生改变；破坏最底层左右配对后，58.3% 的 greedy token 发生改变。模型不是完全无视输入，也不只是复读全局最高频逗号。

但 `0.6094` 距离理想分布仍然很远，候选质量也不高。它更适合被描述为“已经出现 source-conditioned signal”，还不能写成“形成了完整世界模型”。

## 4. 真正的问题出在 READ

TreeHeap 的编码方向是从 leaf 向 root：

```text
token leaves
    -> Butterfly 地址通信
    -> FOLD：leaf -> parent -> root
    -> 得到 root + 多层 details
```

生成时的读取方向相反：

```text
root
    -> 判断 STOP，或继续到 child
    -> 左右分支分配概率
    -> 直到某个深度停止
    -> 形成 context，送给 GRU Decoder
```

当前 STOP 不是硬开关。对到达节点的概率质量 `a`，程序计算：

```text
stop_mass     = a * sigmoid(stop_logit)
continue_mass = a * (1 - sigmoid(stop_logit))
```

只要 `stop_logit` 是有限数，sigmoid 就不会严格等于 0 或 1。程序也没有“低于某个数就视为停止”的观察精度。到达 leaf 后，才被强制全部停止。

C10 在训练早期就把内部 STOP 压到了近乎零。第 1,000 step 时，约 99.9936% 的读取质量已经到达 leaf；最终测试时，平均 leaf 质量约为：

```text
0.9999999963
```

也就是说，数学上还有极小的中间层尾巴，工程上却已经等于一路走到底。

## 5. 强制 leaf 后，模型几乎完全不变

我们在 256 条 held-out WMT 样本、5,226 个目标 token 上做了运行时干预。checkpoint 和所有参数保持不变，只改读取方式。

| READ 干预 | NLL | 相对 Native 变化 |
|---|---:|---:|
| Native learned STOP | 5.299829634 | 0 |
| Force leaf | 5.299829704 | +0.000000070 |
| Uniform branch | 5.403492 | +0.103662 |
| Runtime Identity，拿掉 Butterfly | 5.660286 | +0.360457 |
| Break depth-0 pair | 5.690986 | +0.391156 |

`Native` 与 `Force leaf` 在数值误差范围内相同。这说明 learned STOP 实际已经等价于 leaf-only read。

另一方面，拿掉 Butterfly 或打乱最底层 FOLD 配对会明显增加 NLL。这说明结构变换仍然改变了 leaf 内容，不能说整个网络只是未经处理的原始数组。

最精确的描述是：

> C10 学到的是“经过 Butterfly/FOLD 结构变换的叶层读出”，不是“能在 root、parent 与 leaf 之间按语义选择分辨率的 TreeHeap READ”。

## 6. 它是不是只沿一条链表路径读取

Houming818 随后提出了一个重要反问：既然都走到 leaf，会不会只剩一条固定路径，TreeHeap 退化成了一条链表？

我们没有靠猜测回答，而是重建每个生成 step 的 leaf 权重，并逐级裁剪。

如果它真是一条单路径，Top-1 leaf 应该占据绝大部分概率，保留 Top-1 后 NLL 也不应明显变差。实验却得到：

| 读取叶集合 | 覆盖的平均概率质量 | NLL 增量 |
|---|---:|---:|
| Top-1 | 21.04% | +4.0048 |
| Top-2 | 33.69% | +1.5362 |
| Top-4 | 51.10% | +0.5050 |
| Top-8 | 72.22% | +0.1383 |
| 删除 Top-1 | 其余质量 | +0.0829 |

单路径假说因此被否定。有效 leaf 数约为 15.85，每条样本在生成过程中平均出现 6.72 个不同的 argmax leaf，地址平均跳跃 6.30 格。它不是顺序游标，也不是只盯着一个 leaf。

可是另一个结果同样重要：把所有有效 leaf 改成均匀平均，NLL 只增加 `0.0271`；逐层把左右分支改成均匀分配，大部分 NLL 变化也只有千分位。

所以它也没有形成强而清晰的“语义树索引”。当前更像下面这个过程：

```text
Butterfly/FOLD 改写 leaf state
    -> READ 把很多 leaf 分配一个较宽、较弱的概率桶
    -> 加权求和为 context
    -> GRU 根据 context 逐 token 生成
```

若第 `i` 个变换后 leaf 是 `L_i`，第 `t` 个生成 step 的读权重是 `alpha_ti`，那么 context 可以写成：

```text
c_t = sum_i(alpha_ti * L_i)
```

这就是本文所说的 **leaf pooling**。它不是“所有 leaf 都相同”，而是“Decoder 主要在叶层对许多 leaf 做软加权”。

## 7. 观察者分辨率假说，解决了哪一部分

Houming818 提出了一个很具体的物理类比：

> 现实中的停止不要求光通量严格等于零。只要信号低于观察者能够分辨的极限，工程上就应该把它当作零。

我们据此加入一个不训练参数的诊断规则：如果某条活动路径的质量小于等于 `epsilon`，就在当前节点停止，不再展开它的两个孩子。

第一次 smoke 因统计张量发生别名污染而产生不可能的质量总和，我们将该结果作废，并重新执行。有效重跑覆盖 128 条 held-out WMT 样本和 2,532 个 token。

| epsilon | NLL 增量 | 少访问的节点 | 仍到达 leaf 的质量 |
|---:|---:|---:|---:|
| 0 | 0 | 0% | 99.999999% |
| 0.0001 | +0.000057 | 6.23% | 99.999262% |
| 0.001 | +0.001791 | 8.24% | 99.987412% |
| 0.003 | +0.010178 | 10.11% | 99.932139% |
| 0.01 | +0.069846 | 14.06% | 99.495583% |

这个实验支持一半，也否定一半：

1. **支持**：有限观察精度可以安全剪掉一部分数学上非零、实际贡献极小的尾路径。
2. **未通过正式门槛**：没有一个点同时达到“至少省 10% 节点”且“NLL 增量不超过 0.001”。
3. **否定充分性**：即使 `epsilon=0.003`，仍有 99.93% 的质量到达 leaf。阈值能清理尾巴，却不能把主流量抬回 parent。

因此，C10 同时存在两个现象：

```text
现象一：sigmoid 产生了永不严格归零的数值尾巴
现象二：训练本身把绝大部分有效质量送到了 leaf
```

观察者分辨率解决的是第一个问题，不是第二个。

## 8. 现在到底可以声明什么

### 已有证据支持

1. 自然语料预训练可以迁移到同一 TreeHeap 的 WMT 任务训练；
2. Butterfly 地址通信和 FOLD 配对对 held-out NLL 有可测量的因果作用；
3. source、错误 source 与配对破坏会改变概率后验；
4. 有限分辨率可以剪掉 6% 到 10% 的低质量路径，代价可测量。

### 已被当前证据否定

1. C10 的 Native READ 不是有效的多分辨率 STOP 协议；
2. 它不是只沿一条固定链表路径读取；
3. 单纯增加一个小阈值，不能把 leaf collapse 修成语义分层读取。

### 仍然开放

1. 如何让内部节点在任务 loss 中获得不可替代的价值；
2. STOP 如何在不依赖手写固定深度的情况下学会有限分辨率；
3. root、parent、detail 与 leaf 能否形成稳定的私有编解码协议；
4. 这种协议能否最终改善完整翻译与逻辑对照，而不只是降低平均 NLL。

## 9. 下一步不再盲目加训练时间

C10 已经说明，单纯继续喂更多 token 可能只会把 leaf-only 读法训练得更熟。下一步首先要做的是一个等数据、等 step 的形成机制实验，而不是直接再开一次长训练。

最小实验应比较：

```text
A. 当前自由 soft STOP
B. 训练时加入有限观察分辨率，但不指定固定停止深度
C. 在训练中随机限制可见最大深度，检查内部节点能否获得可读信息
```

三条臂都要同时报告：

```text
任务 NLL 与完整生成质量
每层 stop mass
force-depth 因果损失
uniform-leaf 与 Top-K leaf 损失
Butterfly / pair-break 损失
实际节点访问量
```

其中 C 不是最终架构承诺，只是诊断压力：如果内部节点在被迫读取后仍学不到有用信息，问题可能在 FOLD state；如果能学到，问题则主要在自由优化器总能选择更容易的 leaf 路径。

## 10. 一句话进展

> 我们已经证明 TreeHeap 能从自然语料获得可迁移参数，也证明 Butterfly/FOLD 确实参与预测；但 C10 的自由 STOP 没有形成多分辨率私有协议，而是退化为对变换后 leaf 的宽分布软池化。观察者分辨率能剪尾，不能独自纠正主流量。下一阶段的核心已从“再训练多久”变成“什么形成条件能让 parent 真正值得被读取”。

ARA 设计、代码和结构化 Evidence 将继续整理到 [SameTime 开放仓库](https://github.com/houming818/sametime/tree/main/ara/s3-generation)。所有失败路径保留，不用事后改写故事。

---

**License:** GPLv3。本文中的 Claim、反证条件、实验过程与数据可自由复现、审计和修改。
