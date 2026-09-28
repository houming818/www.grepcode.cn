---
title: "TreeHeap 论文：概率下坠、多分辨率状态与生成协议"
date: 2026-08-02
lastmod: 2026-09-28
author: Houming818 & Trinity (Codex)
description: "TreeHeap 当前完整理论入口：连续阅读背景概率场、概率下坠 Embedding、Monte Carlo 与可微路由、统一 TreeState、保序 FOLD、READ/Decoder、证据边界和发布目标。"
keywords: [TreeHeap论文, 概率Embedding, 下坠模型, Monte Carlo, F函数, FOLD, UNFOLD, READ, 私有协议, 消费级AI]
tags: [TreeHeap, Paper, Architecture, Probability, Mathematics, Evidence, Reproducibility]
---

# TreeHeap 论文

这篇论文面向第一次接触 TreeHeap 的研究者。它不按实验时间线复述研究，而是把 2026-09-28 当前采用的理论、算法、证据边界和下一阶段目标整理成一篇可以连续阅读的完整论文。

## 直接阅读全文

[TreeHeap：概率下坠、多分辨率状态与可训练生成协议](/treeheap-paper/001-treeheap-emergent-protocol.html)

全文从语料背景场开始，依次说明概率下坠、局部主轴、Monte Carlo 与梯度搜索、概率 FOLD、统一状态、保序序列 FOLD、READ/Decoder、当前证据、架构断点、Release 分级与反证条件。页面自带目录，手机上打开一个地址即可从头读到尾。

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
