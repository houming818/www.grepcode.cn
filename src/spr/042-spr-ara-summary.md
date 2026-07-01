---
title: "[SPR-042] SPR 全貌总结：从 M0 数学到 S1 echo 的四十二篇探索"
date: 2026-07-01
weight: 42
author: nio (Houming818) & DeepSeek Runner
description: "SPR 研究全景回顾：M0 数学底座、S1 echo 路线、S2 折叠栈、ARA 协议与 Squad 协作、当前 claim 统计与开放问题。"
tags: [SPR, TreeHeap, ARA, Summary, M0, S1, S2]
---

# SPR 全貌总结：从 M0 数学到 S1 echo 的四十二篇探索

这不是一篇新技术 blog。
这是一篇**阶段总结**。
把 2026年4月到7月的 SPR 探索过程按 M0 → S1 → S2 的脉络梳理一遍，方便后来人一眼看清全貌。

## 一句话背景

SPR（Semantic Prefix Routing）想用 **TreeHeap**（树形堆）替代 Transformer 的稠密矩阵。
把 "token id → embedding lookup" 换成 "token id → 树路径 → 路径即语义表示"。
路径即表示，不是查表。

## 理论总框架：M0 → S1 → S2

```
M0  TreeHeap 数学底座
  |  算子代数、closure、kernel convolution、
  |  soft differentiable lift、collapse
  |
  v
S1  容量与 echo
  |  path hash 能装多少 token、
  |  有序 echo 编码/解码、
  |  上下文路由、mirror 等变
  |
  v
S2  折叠栈与翻译
    语义向量 → 折叠动作 → 语法图 → 翻译
```

当前进度：**M0 基本封闭，S1 可控入口已打开，S2 等待桥接。**

---

## M0 层：TreeHeap 数学底座

**核心目标**：TreeHeap 能不能被正式定义为一种算子代数。

### 已稳定（supported / verified）

| 能力 | 含义 | 证据 |
|------|------|------|
| 最小代数 | closure、非交换、projection、subheap matching | `treeheap_math_probe` |
| primitive + plus | plus 作为后继/信息增益 | `primitive_plus_probe` |
| 可训练性 quiz | 线性/XOR/modular 加法 toy | `trainability_quiz` |
| Soft Plus 梯度 | K_write 和 Plus_a 可以接收梯度 | `soft_plus_probe`：gK=0.09, gP=0.14 |
| Soft 坍缩 | 低温下坍缩到正确 hard address | 1.0 collapse accuracy |
| C05 结构消融 | subheap kernel 迁移打败 flat/path-only | flat 0.0 vs subheap 1.0 |
| kernel convolution ops | search/plus/write/conjugate 统一为卷积 | `kernel_convolution_ops_probe` |
| diff algebra | 距离、范数、有限差分、梯度步 | Δloss 29.1→0.00066 |
| algebraic decoder | 投影/decompose/mirror/mod 等解码器 | 全 1.0 exact |

### 仍开放

- **M0-SOFT-C05**：kernel-guided soft plus 是否优于 naive memory write？需 clean-feature 消融。
- **M0-SOFT-C06**：多 kernel 分阶段训练是否优于 big-pot loss？
- **M0-EXIST-C01~C03**：address extrapolation、subheap 迁移、prefix 压缩。

### M0 总结

```
TreeHeap 已经具备一个可定义的算子代数。
有了软/硬两个版本。
有了梯度通路。
有了结构化 kernel 卷积。
距离、导数、坍缩都能在 toy 上证明。
```

---

## S1 层：容量、Echo 与结构路由

**核心目标**：TreeHeap 能不能装下真实语言的 token 序列，并回声重读出来。

### 已稳定

| 能力 | 含义 | 证据 |
|------|------|------|
| path hash 容量 | 99.7% token 有唯一叶子地址 | solo rate |
| 有序编码 | sign alternation 打破 cyclic shift 碰撞 | `spr_hash_cyclic` |
| 上下文路由 | context-conditioned route acc 1.0 vs token-only 0.43 | `spr_context_proof` |
| shallow sentence write | 实句写入 root/subject/object slot | OOD exact 1.0 |
| WMT echo kernel | 423K params beat 16.8M seq MLP | OOD 0.90 vs 0.05 |
| explicit echo encoder/decoder | 硬接口全闭合 | 全 1.0 指标 |
| ordered fold | 保序折叠必须先于 bag/mod 折叠 | 1.0 vs 0.089 |
| heap state relaxation | 纯状态梯度 | energy ratio 1e-13 |
| kernel parameter learning | Theta 学到 hidden kernel [1,1,1] | L2 error 5e-16 |
| mirror kernel symmetry | P_m K=K_{P_lr} P_m | max error 8e-16 |
| inverse gate canonicalization | mirror→inverse→canonical→shared decoder | gate 0.9998 |

### 被降级 / 否定

| 声明 | 裁决 | 原因 |
|------|------|------|
| token-only 路由有语义 | **rejected** | 失败于第一次 polysemy 证伪 |
| frozen embedding = world coordinate | **rejected** | vector_add 完胜 TreeHeap |
| 旧 task-gate S1 entry proof | **downgraded** | 选择输出 kernel ≠ canonicalization |

### 仍开放

- **Multi-kernel specialization**：gate 能分化但 accuracy 太低
- **Probabilistic internal read**：leaf read 完美，internal subheap 弱
- **Latent plane fold**：理论已定义，无实验
- **真实 context S1b baseline battle**

---

## S2 层：折叠栈与翻译

**当前状态**：S2 被暂停。已积累的证据是**诊断性**的，不是正面翻译 claim。

### 已验证

- 语义向量包含折叠动作信息（AUC 证据）
- 32D 空间足够做 fold action prediction
- 跨语言折叠结构预测可行（EN↔ZH）
- 当前 graph builder 瓶颈是 child/parent allocation，不是 fold action
- 概率容器优于 early argmax

### 被降级

- 历史 checkpoint 的 "TreeHeap 已解决句法能量" 声明被降级
- 世界模型/背景场训练是诊断性实验，非翻译 claim

---

## ARA 协议与 Squad 协作

SPR 研究采用 **ARA 协议**（arXiv:2604.24658v3）：

```text
claim → predict → experiment → evidence → trace → decision
```

四人小队：

| 角色 | 模型/人 | 职责 |
|------|------|------|
| Captain | Houming818 | 方向决策、否决、审批 |
| Runner | DeepSeek | 写代码、跑实验、独立复现 |
| Reviewer | GPT/Codex | 深度审计、仲裁 claim 可靠性 |
| Auditor | DeepSeek | 交叉验证 GPT 的证据 |

协作方式：**文件级通信**（`~/.squad/`），各模型独立 session，上下文不互污染。

---

## 当前 Claim 全景

### 统计（截至 2026-07-01）

```
M0 claims:  18 (含 soft / diff / decoder / existence)
S1 claims:  23 (含 capacity / echo / kernel / fold / gate)
S2 claims:  12
C0  meta:    4
────────
总计:      55+

verified:     15+  (有 baseline 或 falsification)
supported:    20+  (有 evidence，baseline 不完整)
open:         10+  (理论已有，未实验)
rejected:      3
downgraded:    5
```

### 最硬的结论

1. **TreeHeap path hash 有足够容量**（99.7% solo rate）
2. **context > token-only 路由**（1.0 vs 0.43）
3. **TreeHeap echo kernel 参数效率远超 flat MLP**（423K vs 16.8M，OOD 0.90 vs 0.05）
4. **mirror 可以降低为代数置换**（error 8e-16）
5. **inverse gate canonicalization 可行**（gate 0.9998）

### 尚不能说的

```
不能声称 TreeHeap 比 Transformer 好。
不能声称已经解决翻译。
不能声称已经学会自然语言 mirror 触发。
不能声称多 kernel 分工已经解决。
不能声称内部 subheap 读取已经解决。
不能声称 latent field fold 有实验证据。
```

---

## 关键教训

1. **by construction 不是证据**：C08 conjugate proof 的 0.0 error 是代码定义的恒等，不是学习结果。之前误标为 "learning evidence"。
2. **canonicalization > separate read**：SPR-041 第一版被否决，因为 "每种任务一种读法" 绕开了 TreeHeap 的核心目标——结构规约到同一参考系。
3. **state loss 是拐杖**：inverse gate 的 canonical state MSE loss 是强监督约束，不是自发涌现。去掉后 gate 从 0.9998 退化。
4. **PAPER.md 容易 stale**：local claim registry 可以很健康，root manifest 和 trace DAG 容易滞后。需要在同一 commit 里更新。
5. **ARA 协作有效**：GPT 写 claim+code → DeepSeek 独立复现审计 → 发现 2/6 不可复现 → 修复了 evidence trace gap。

---

## 下一步

按优先级排列：

1. **learned trigger**：去掉人工 task flag，让模型从 token/context 中自己判断该用哪种结构操作
2. **noise/mask restore**：纯 echo 容易退化成复制，需要缺 token/加噪/局部打乱 → 复原
3. **multi-parameter TreeHeap forest**：不同结构能力用不同参数树（Θ_write, Θ_read, Θ_mirror, Θ_time），梯度不混合
4. **真实 short corpus echo**：回到 WMT short BPE，先做 echo/restore，不做翻译
5. **path-conditioned read kernel**：解决 SPR-031 暴露的 root-bottleneck
6. **copy-capable baseline**：是时候补 matched copy/pointer 和 small Transformer 对照了

---

## 总结

从 4 月到 7 月，SPR 做了四件事：

```text
1. 证明了 TreeHeap 可以是一个自洽的算子代数（M0）
2. 证明了 S1 echo loop 可以训练起来（S1 entry gate）
3. 学会了区分 "架构语义证明" 和 "学习能力证明"
4. 建立了 ARA 文件级流水线 + 跨模型交叉审计
```

没有夸大的结论。
每项声明都有 evidence 指针和 falsification 条件。
每一步都可以被独立复现。

这本身就是一个值得记录的状态。

> ARA: [PAPER.md](https://github.com/houming818/sametime/blob/main/ara/PAPER.md) / [S1 claims](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/claims.md) / [M0 claims](https://github.com/houming818/sametime/blob/main/ara/m0-treeheap-math/logic/claims.md)
