---
title: "TreeHeap 论文：架构、数学、证据与复现"
date: 2026-08-02
lastmod: 2026-08-24
author: Houming818 & Codex Review
description: "TreeHeap 中文论文全文入口：在一个网页中连续阅读设计演化、数学与数据流、WMT 实验证据、Claim 边界与复现方法。"
keywords: [TreeHeap论文, TreeHeap架构, 递归树堆, FOLD, UNFOLD, WMT, 私有协议, AI新架构, 可复现实验]
tags: [TreeHeap, Paper, Architecture, Mathematics, Evidence, Reproducibility]
---

# TreeHeap 论文

这篇论文面向第一次接触 TreeHeap 的研究者。它不是 85 篇实验日志的摘要拼接，而是把当前仍然成立的架构、数学、证据和边界整理成一篇可以连续阅读的完整论文。

## 直接阅读全文

[TreeHeap：可逆多分辨率树状态、稀疏通信与双语序列协议](/treeheap-paper/001-treeheap-emergent-protocol.html)

全文从摘要、研究问题和设计演化开始，依次给出形式化定义、数据流、实验设计、结果、Claim 边界、复现方法与符号表。页面自带目录，手机上打开一个地址即可从头读到尾。

## 辅助阅读

### 当前理论状态

[TreeHeap 当前理论状态与目标](/treeheap-theory.html) 是持续更新的非编号页面，集中维护当前采用的 Embedding/UNFOLD、多分辨率概率、统一状态、FOLD、READ 与 Decoder 理论。本文是版本快照；数字 SPR 保存研究过程；当前理论页回答“项目今天认为 TreeHeap 应当是什么”。

### 按章节拆分

需要分段阅读时，可以使用下面四篇短页面：

1. [问题与演化：TreeHeap 为什么不是把数组画成一棵树](/spr/077-treeheap-paper-origin-and-evolution.html)
2. [数学与数据流：一个句子怎样进入 TreeHeap](/spr/078-treeheap-paper-math-and-dataflow.html)
3. [实验证据：三种子 WMT 与双向 Dreams](/spr/079-treeheap-paper-evidence-and-dreams.html)
4. [边界与复现：如何审核 TreeHeap](/spr/080-treeheap-paper-boundaries-and-reproduction.html)

四篇拆分稿与全文回答相同的四个问题：为什么设计 TreeHeap、代码实际计算什么、目前获得了什么证据、哪些结论仍可能被推翻。

### 审核完整研究过程

请进入 [SPR 数字序列](/spr/)，从 SPR-001 开始按编号阅读。那里保留了理论修改、失败实验、代码审计、撤回结论和后续修复。SPR-077 至 SPR-080 正是论文四篇在完整时间线中的位置。

## 单文件论文与开放证据

- [完整中文论文 Markdown](https://github.com/houming818/sametime/blob/main/ara/papers/treeheap_emergent_protocol.zh.md)
- [SameTime 开放代码与 ARA evidence](https://github.com/houming818/sametime)
- [最新 TreeHeap 实验](/spr/085-treeheap-fold-energy-and-gradient-pressure.html)

## 阅读边界

论文记录的是当前证据允许的结论，不把探索中的猜想写成已证明事实。后续实验若推翻论文中的某个 Claim，SPR 会先保存失败记录，再更新论文版本。

> **作者：Houming818 与 Codex Review**  
> **开放方式：公开代码、公开证据、公开反证条件。**
