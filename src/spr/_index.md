---
title: "SPR：语义前缀路由研究档案"
date: 2026-06-16
author: nio (Houming818) & Codex Review
description: "SPR 的 ARA 风格研究档案：问题、证据、反证、proof、架构决策和下一轮实验。"
tags: [SPR, ARA, SemanticRouting, Falsification, Architecture]
---

## 这是什么

SPR（Semantic Prefix Routing，语义前缀路由）是一组研究实验，目标是回答一个问题：

> 能不能用“路径”替代 Transformer 里的一部分稠密矩阵搜索？

开放实验记录在 GitHub：

```text
https://github.com/houming818/sametime
```

其中 `ara/` 是公开版 ARA 研究记录，保留 logic、trace、轻量 evidence summary 和可公开脚本，方便人类和 AI 一起复盘这条路线。

这里的“路径”不是比喻。它指的是一个 token、短语或句子在递归树、折叠栈或结构图中走过的可计算轨迹。路径可以被组合、比较、压缩，也可以作为下游生成或结构判断的输入。

这套研究现在按 ARA（Architecture / Reasoning / Artifact）方式整理：每个结论都要有证据，每个强 claim 都要有反证标准。

## 当前结论

SPR 目前不能简单写成“路径即语义”。更准确的判断是：

| 层 | 名称 | 当前状态 |
|----|------|----------|
| S1a | Token Path Hash | 已成立：高容量、低碰撞、顺序可分 |
| S1b | Context-conditioned Routing | 受控 proof 已支持：仍需真实语料和基线战 |
| S2 | Fold Stack / Structure Routing | 有证据：语义能预测部分结构动作，但仍需基线对照 |

最重要的变化是：**Echo Test 不再被当作语义证明。**

Echo 证明系统能把输入还原出来。它证明容量和稳定性，但不证明系统理解了上下文里的含义。

## 推荐阅读顺序

1. [问题定义：为什么要研究路径路由](/spr/001-problem.html)  
   解释 SPR 想替代什么、不替代什么。

2. [S1 实验：Echo、顺序哈希与容量证据](/spr/002-s1-evidence.html)  
   重做 S1 实验，确认哪些结果可靠。

3. [S1 反证：token-only 路由不是语义路由](/spr/003-s1-falsification.html)  
   用多义词实验说明当前 S1 的边界。

4. [架构决策：把 SPR 拆成三层](/spr/004-architecture-decision.html)  
   给出新的架构划分和接口。

5. [S2 结构路线：Fold Stack 的位置](/spr/005-s2-fold-stack.html)  
   解释 S2 为什么不是 Echo 的延长线，而是结构生成路线。

6. [下一轮实验计划](/spr/006-next-experiments.html)  
   列出下一步怎么让路径真正吃上下文。

7. [S1b proof：上下文条件路由到底证明了什么](/spr/007-context-proof.html)  
   用受控 proof 审计历史结论，明确哪些说法可以保留，哪些必须降级。

8. [S2 策略审计：TreeHeap、Role Slots 和概率容器](/spr/008-s2-strategy-audit.html)  
   用 ARA 方式解释 S2 实验数据，说明为什么下一步转向 Role Slots 和 Probability Container。

9. [世界模型与参考系：TreeHeap 术语统一](/spr/009-world-model-frames.html)
   统一世界模型、参与乘积、参考系、latent slot 和概率容器术语，为下一步 predict 做准备。

10. [世界模型守夜训练：新 checkpoint 给了什么证据](/spr/010-world-model-night-run.html)
    用 ARA 方式记录 10 小时新 checkpoint 训练，明确它证明了什么、没有证明什么。

11. [TreeHeap 代数：先做数学闭包，再谈语言推理](/spr/011-treeheap-algebra.html)
    把 TreeHeap 从乘法层推进成代数系统，定义闭包、转置、逆树堆、投影和能量。

12. [子堆核搜索：TreeHeap 里的卷积式推理](/spr/012-subheap-kernel-search.html)
    把矩阵卷积里的局部核匹配，改写成 TreeHeap 上的 SubHeap Kernel Search，用来讨论拓扑搜索和局部推理操作。

13. [M0 纯数学实验：先让 TreeHeap 成为工具箱](/spr/013-treeheap-math-probe.html)
    记录第一轮合成 toy 实验，说明为什么先验证闭包、非交换、逆操作和子堆核匹配，再进入 Echo 和 S2。

14. [基元与 plus：TreeHeap 有序性的来源](/spr/014-primitive-plus-order.html)
    把卷积问题继续下压到基元、plus、ordered orbit 和 mod base，说明为什么先找语义空间里的“1”和“+”。

15. [primitive plus 实验：把 proof 变成可测的 TreeHeap toy](/spr/015-primitive-plus-probe.html)
    用本科数学口径解释 P-MATH02 实验：arr[0]、plus、mod base、信息量增长、循环窗口和 kernel 匹配。

## 证据入口

对应的 ARA 文件在仓库中：

```text
ara/s1-echo/logic/claims.md
ara/s1-echo/logic/experiments.md
ara/s1-echo/trace/research_dag.yaml
ara/s1-echo/evidence/README.md
```

关键脚本：

```text
holds/SameTime/experiments/spr_s1_reproduce.py
holds/SameTime/experiments/spr_s1_falsification.py
holds/SameTime/experiments/spr_context_proof.py
s2_strategy_audit.py
s2_overnight_io.py
```

关键复现实验结果：

```text
collision=True
sign_alt=True
solo=41311/41429
bleu4=99.99
token_polysemy=0.43
keyword_polysemy=1.00
context_route=1.00
context_route_shuffled=0.48
```

这组结果的含义是：

- `collision=True`：pure roll 确实有顺序碰撞。
- `sign_alt=True`：`roll + sign_alt` 修复了这个碰撞。
- `solo=41311/41429`：路径空间足够大，几乎每个 token 独占组合叶。
- `bleu4=99.99`：Echo 近乎完美。
- `token_polysemy=0.43`：token-only route 不能区分多义上下文。
- `keyword_polysemy=1.00`：这个多义词任务本身不是不可解，只是 S1 当前没吃上下文。
- `context_route=1.00`：受控上下文信号进入 route 后，同词多义可以被路径分开。
- `context_route_shuffled=0.48`：打乱标签后优势消失，说明 proof 没有只靠标签分布取巧。

## 阅读提醒

旧版 SPR 文章是实验史，曾经混合了探索、猜想和阶段性判断。新版专题只保留当前架构上仍然成立的叙事，并把过强结论降级为待验证假说。

> **License: GPLv3**
