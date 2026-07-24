---
title: "[SPR-071] STONE-1 Candidate C08 发布：第一个可以下载运行的 TreeHeap 翻译模型"
date: 2026-07-24
lastmod: 2026-07-24
weight: 71
author: Houming818 & Codex Review
description: "SameTime 首次公开可执行的固定根 TreeHeap 翻译 checkpoint、CLI、校验文件和完整实验边界；它是 STONE-1 候选版，不是完成声明。"
tags: [SPR, TreeHeap, SameTime, STONE-1, Release, Checkpoint, WMT, CLI, ARA]
---

# STONE-1 Candidate C08 发布：第一个可以下载运行的 TreeHeap 翻译模型

今天，我们把 **SameTime STONE-1 Candidate C08** 的源码、checkpoint、tokenizer、命令行程序和实验记录一起公开。

这是第一个可以由读者下载并实际输入英文句子的 TreeHeap 翻译候选版。它不是概念图，也不是只在训练脚本里存在的指标。

但请先看清名称：

> **Candidate 表示候选版。我们没有宣布 `STONE-1: COMPLETE`。**

当前结果已经跨过预先登记的单种子产品阈值，但多随机种子稳定性、正式延迟统计和同一 checkpoint 的完整结构因果审计仍未完成。

---

## 1. 下载

SameTime Release：

- [STONE-1 Candidate C08 下载页](https://repos.grepcode.cn/houming818/grepcode-sametime/releases/tag/stone1-candidate-c08)
- [GitHub 源码镜像与标签](https://github.com/houming818/sametime/tree/stone1-candidate-c08)

发布包：

```text
sametime-stone1-candidate-c08.tar.gz
大小：673,397,070 bytes
SHA-256：78b11e04ff94a54c559084c3ed7a65458bed4c9f6fcef102fcbe66f0bb9e570f
```

压缩包包含：

```text
encoder-growth-step62500.pt
decoder-eos-tail.pt
sp-bpe-massive.model
MODEL_CARD.md
README.md
LICENSE
SHA256SUMS
```

训练语料没有随包再发布。源码和模型包使用 GPL-3.0，模型没有生产可用性保证。

---

## 2. 它到底是什么

C08 是一个英译中的研究 POC。输入英文 SentencePiece token 后，系统执行：

```text
英文 token
  -> 写入固定 64-leaf TreeHeap
  -> encoder 从 leaf 向 root 递归 FOLD
  -> 保存 root 和六层有地址的 detail
  -> decoder 按多个分辨率读取 H_state
  -> 自回归生成中文 token
```

短句不会改变树根的位置。空余 leaf 使用重复 EOS 填充，而且 EOS 对 encoder 可见。这相当于给模型一张固定尺寸的纸：句子变短时，不重新裁纸，而是在剩余位置写入统一的结束符。

本次发布冻结了已经训练好的 C04 encoder，只训练 C08 decoder。decoder 在六个可见深度上都保留至少 2% 的读取权重，防止梯度通道在训练早期彻底关闭。

这里的 2% 不是“正确答案”，而是一根最低水压管。它保证 decoder 有机会收到来自深层节点的学习信号；各层真正贡献多少，仍由训练决定。

---

## 3. 正式测试结果

正式任务在 io 的 RTX 3090 上执行，C08 decoder 使用一百万对 WMT-massive 英中样本训练 15,625 个更新步。

| 指标 | 测试结果 | 趋势 |
|---|---:|---|
| Test NLL | 3.4517 | 越低越好 |
| Token BLEU-4 | 13.8713 | 越高越好 |
| 非空生成率 | 1.000 | 越高越好 |
| 严重重复率 | 0.015 | 越低越好 |
| 峰值显存 | 2.27 GiB | 资源记录 |

### NLL 是什么

NLL 可以粗略理解为“模型对正确下一个 token 有多意外”。正确 token 的预测概率越高，NLL 越低。

NLL 不能单独代表翻译质量。模型可能词序自然却翻错关系，也可能意思接近但选词不同。因此我们同时报告 BLEU、非空率、重复率，并公开实际输出。

### BLEU-4 是什么

BLEU-4 检查生成文本中的 1 到 4 token 片段与参考译文有多少重合。13.87 说明模型已经不是随机吐字，但距离可靠翻译仍很远。

---

## 4. 实际能说出什么

对下面的输入：

```text
Artificial intelligence can help people understand the world.
```

记录的 checkpoint 输出：

```text
聪明人可以理解世界。
```

它抓住了“智能、帮助理解世界”的轮廓，但把“人工智能”错误压缩成了“聪明人”。这正好说明当前状态：

- 模型能够生成通顺的中文短句；
- 模型能够恢复部分语义轮廓；
- 模型仍会错译实体、关系、数字、修饰语和罕见词；
- 它不是通用问答模型，也没有资格用于生产翻译。

---

## 5. 如何运行

解压发布包，在对应标签的 SameTime 仓库中安装 PyTorch 和 SentencePiece，然后运行：

```bash
python3 ara/s3-generation/src/treeheap_fixed_root_cli.py translate \
  --encoder-checkpoint /path/to/encoder-growth-step62500.pt \
  --decoder-checkpoint /path/to/decoder-eos-tail.pt \
  --tokenizer /path/to/sp-bpe-massive.model \
  --text "Artificial intelligence can help people understand the world."
```

交互模式：

```bash
python3 ara/s3-generation/src/treeheap_fixed_root_cli.py translate \
  --encoder-checkpoint /path/to/encoder-growth-step62500.pt \
  --decoder-checkpoint /path/to/decoder-eos-tail.pt \
  --tokenizer /path/to/sp-bpe-massive.model \
  --interactive
```

---

## 6. 这次真正证明了什么

截至 C08，证据支持以下较窄结论：

1. 固定 64-leaf framing 可以完成真实英中语料上的训练和非 teacher-forcing 生成；
2. 重复 EOS 尾部比确定性随机 token 尾部更容易形成稳定协议；
3. 冻结 encoder 后，带 2% 深度下限的 decoder 可以跨过当前单种子产品阈值；
4. SameTime 已经具备可复现 checkpoint、CLI 和模型包，不再只是实验草图。

我们暂时不能据此声称：

- TreeHeap 已经优于 Transformer；
- EOS 是普适的噪声修复算法；
- decoder 已自然学会最佳停止深度；
- TreeHeap 私有协议已经完成；
- STONE-1 已通过。

特别是，当 EOS-trained decoder 切回 clean masked input 时，验证 NLL 恶化 0.3256。这说明它学到的是一种**固定 framing 协议**，不是可以修复任意尾部噪声的通用能力。

---

## 7. STONE-1 还缺哪三项

把候选版升级为正式里程碑，至少还要关闭三个 Gate：

1. **三种子稳定性**：不是只在一颗随机种子上达到阈值；
2. **正式延迟 P50**：把模型加载和纯生成耗时分开测量；
3. **同 checkpoint 结构审计**：破坏左右地址、递归 detail 或读取深度后，性能必须按预测下降。

第三项尤其重要。一个模型把向量放在树形数组里，不等于它真的利用了树。只有结构干预能稳定改变结果，我们才有资格说 TreeHeap 参与了计算。

---

## 8. 如何审核

完整 Claim、实验设计、反证条件和原始 evidence 位于 SameTime：

```text
ara/s3-generation/logic/stone1_fixed_root_noise_repair.md
ara/s3-generation/evidence/s3_stone1_fixed_root_noise_repair/
ara/s3-generation/src/treeheap_fixed_root_cli.py
```

发布标签：

```text
stone1-candidate-c08
```

我们选择现在公开，是因为研究对象终于可以被别人运行、批评和复核。候选版的价值不在于把未完成的工作包装成答案，而在于把下一步争论变成可执行的实验。

