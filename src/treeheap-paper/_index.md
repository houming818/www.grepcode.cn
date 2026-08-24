---
title: "TreeHeap 论文：架构、数学、证据与复现"
date: 2026-08-02
lastmod: 2026-08-24
author: Houming818 & Codex Review
description: "TreeHeap 中文论文的四篇网页版入口：设计演化、数学与数据流、WMT 实验证据、Claim 边界与复现方法。适合第一次接触 TreeHeap 的研究者连续阅读。"
keywords: [TreeHeap论文, TreeHeap架构, 递归树堆, FOLD, UNFOLD, WMT, 私有协议, AI新架构, 可复现实验]
tags: [TreeHeap, Paper, Architecture, Mathematics, Evidence, Reproducibility]
---

# TreeHeap 论文

这组论文面向第一次接触 TreeHeap 的研究者。它不是 85 篇实验日志的摘要拼接，而是把当前仍然成立的架构、数学、证据和边界压缩为四个连续章节。

## 两种阅读路线

### 想先理解当前 TreeHeap

按下面四篇连续阅读即可。每篇都能在手机浏览器中直接打开：

1. [问题与演化：TreeHeap 为什么不是把数组画成一棵树](/spr/077-treeheap-paper-origin-and-evolution.html)
2. [数学与数据流：一个句子怎样进入 TreeHeap](/spr/078-treeheap-paper-math-and-dataflow.html)
3. [实验证据：三种子 WMT 与双向 Dreams](/spr/079-treeheap-paper-evidence-and-dreams.html)
4. [边界与复现：如何审核 TreeHeap](/spr/080-treeheap-paper-boundaries-and-reproduction.html)

这条路线回答四个问题：为什么设计 TreeHeap、代码实际计算什么、目前获得了什么证据、哪些结论仍可能被推翻。

### 想审核完整研究过程

请进入 [SPR 数字序列](/spr/)，从 SPR-001 开始按编号阅读。那里保留了理论修改、失败实验、代码审计、撤回结论和后续修复。SPR-077 至 SPR-080 正是论文四篇在完整时间线中的位置。

## 单文件论文与开放证据

- [完整中文论文 Markdown](https://github.com/houming818/sametime/blob/main/ara/papers/treeheap_emergent_protocol.zh.md)
- [SameTime 开放代码与 ARA evidence](https://github.com/houming818/sametime)
- [最新 TreeHeap 实验](/spr/085-treeheap-fold-energy-and-gradient-pressure.html)

## 阅读边界

论文记录的是当前证据允许的结论，不把探索中的猜想写成已证明事实。后续实验若推翻论文中的某个 Claim，SPR 会先保存失败记录，再更新论文版本。

> **作者：Houming818 与 Codex Review**  
> **开放方式：公开代码、公开证据、公开反证条件。**
