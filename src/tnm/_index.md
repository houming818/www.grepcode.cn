---
title: "TNM：TreeHeap 原生记忆协议"
date: 2026-08-07
author: Houming818 & Codex Review
description: "研究 TreeHeap 如何让状态、写入、读取、更新与遗忘共同形成原生记忆协议。"
tags: [TNM, TreeHeap, Memory, PrivateProtocol]
---

# TNM：TreeHeap Native Memory

TNM 研究的不是如何在 TreeHeap 外面再挂一个数据库，而是一个更基础的问题：

> **一棵持续变化的 TreeHeap，能否与写入 kernel、读取 kernel 和更新规则共同形成原生记忆协议？**

这里的“记忆”不预设为原文检索、问答、续写或知识图谱。它们都是可能的协议，不同协议规定了信息怎样写入、怎样被查询、怎样被更新，以及何时遗忘。

本专题承接 TreeHeap 的 M0 代数、FOLD/UNFOLD、私有协议和多分辨率研究，但会把“单次编解码”推进到“跨时间持续状态”。

## 专题边界

TNM 关注：

1. 状态如何连续写入，而不是每次重新编码；
2. Encoder 与 Decoder 如何形成稳定的私有读写协议；
3. 多种读取协议能否共享同一份 TreeHeap 状态；
4. 新记忆如何合并、冲突、修复和遗忘；
5. 如何证明答案确实来自记忆状态，而不是模型参数中的旧知识。

TNM 暂不把外部向量数据库、全文索引或独立记忆服务当作目标实现。它们可以作为基线，但不是本专题要寻找的 TreeHeap 原生机制。

完整代码、ARA 与实验记录继续保存在 [SameTime 开放仓库](https://github.com/houming818/sametime)。

---

**License:** GPLv3。允许复现、审计、修改与继续研究，但衍生工作须保留相同开源许可。
