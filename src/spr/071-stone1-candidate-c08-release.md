---
title: "[SPR-071] STONE-1 Candidate C08：第一个可公开下载的 TreeHeap 模型"
date: 2026-07-24
lastmod: 2026-07-24
weight: 71
author: Houming818 & Codex Review
description: "SameTime 首次通过对象存储与 CDN 公开 TreeHeap checkpoint、tokenizer 和 CLI；本文说明下载、运行方法、实验结果以及尚未通过的 STONE-1 Gate。"
tags: [SPR, TreeHeap, SameTime, STONE-1, Checkpoint, CDN, WMT, CLI, ARA]
---

# STONE-1 Candidate C08：第一个可公开下载的 TreeHeap 模型

> **发布状态更新（2026-07-28）：该下载包保留为可复现实验制品，但暂停称为“英译中模型候选”。后续同族 C10 checkpoint 在三个无关英文输入上生成了近乎相同的“一带一路”循环；代码审计发现 teacher forcing 与可见 EOS 尾部可能掩盖 source 忽略。C08/C09 必须通过新的条件依赖审计后，才能恢复 STONE-1 候选或完成状态。详见 SPR-074。**

SameTime 现在有了第一个可以被外部读者直接下载、运行和审核的 TreeHeap 模型：

> **STONE-1 Candidate C08**

它是一个英译中的研究原型。它可以读取英文句子，在固定容量的 TreeHeap 中递归编码，再生成中文。

请特别注意名称中的 **Candidate**：

> 这是 STONE-1 候选版，不是 `STONE-1: COMPLETE`。

我们公开它，是为了让研究从“只能看文章和指标”前进到“任何人都可以运行 checkpoint”。公开下载不等于 Claim 已经完成。

---

## 1. 公网下载地址

模型文件放在腾讯云对象存储，通过 `www.grepcode.cn` 的 CDN 公开分发。

- [下载模型包，约 643 MiB](https://www.grepcode.cn/models/stone1-candidate-c08/sametime-stone1-candidate-c08.tar.gz)
- [下载 SHA-256 校验文件](https://www.grepcode.cn/models/stone1-candidate-c08/sametime-stone1-candidate-c08.sha256)
- [查看 GitHub 公开源码和版本标签](https://github.com/houming818/sametime/tree/stone1-candidate-c08)

研发使用的 Gitea 位于局域网，不是公共发布站点，因此本文不提供 Gitea 下载链接。

模型包的公开信息：

```text
文件：sametime-stone1-candidate-c08.tar.gz
大小：673,397,070 bytes
SHA-256：78b11e04ff94a54c559084c3ed7a65458bed4c9f6fcef102fcbe66f0bb9e570f
```

Linux 下可以这样检查文件：

```bash
sha256sum sametime-stone1-candidate-c08.tar.gz
```

只有输出与上面的 SHA-256 完全一致，才能确认下载文件没有损坏或被替换。

---

## 2. 压缩包里有什么

```text
encoder-growth-step62500.pt
decoder-eos-tail.pt
sp-bpe-massive.model
MODEL_CARD.md
README.md
LICENSE
SHA256SUMS
```

其中：

- `encoder-growth-step62500.pt`：把英文 token 递归压入 TreeHeap 的 encoder；
- `decoder-eos-tail.pt`：从 TreeHeap 多层状态生成中文的 decoder；
- `sp-bpe-massive.model`：32K 词表的 SentencePiece tokenizer；
- `MODEL_CARD.md`：用途、限制和训练信息；
- `SHA256SUMS`：包内文件的独立校验值。

训练语料没有包含在发布包中。源码和模型包使用 GPL-3.0，没有生产可用性保证。

---

## 3. 这个模型怎样工作

C08 不是把整句直接塞进一个普通数组，然后给数组换一个 TreeHeap 名字。

它的主要数据流是：

```text
英文句子
  -> SentencePiece token
  -> 写入固定 64 个 leaf
  -> 从 leaf 向 root 递归 FOLD
  -> 形成 root 和六层有地址的 detail
  -> decoder 读取多个分辨率的 H_state
  -> 自回归生成中文 token
```

### 固定 64-leaf 是什么意思

无论输入句子有 12 个 token 还是 30 个 token，物理树根都不移动。

短句没有用完的 leaf 使用重复 EOS 填充。EOS 是“序列已经结束”的统一标记。它类似固定尺寸表格里的空白栏位：表格坐标不变，模型可以学习哪些位置已经超出正文。

### 2% depth floor 是什么意思

decoder 可以在 root 停止，也可以继续向更深层读取细节。

早期实验发现，如果完全交给优化器选择，decoder 很容易只读 root，深层路径因为没有梯度而永久关闭。C08 因此给每个可见深度至少 2% 的读取概率。

这 2% 像一根最低水压管：

- 它不规定哪一层一定正确；
- 它只保证每一层都有机会收到梯度；
- 剩余读取权重仍由训练学习。

本次发布使用冻结的 C04 encoder，只训练 C08 decoder。这样可以把“encoder 写入了什么”和“decoder 能否读出来”分开检查。

---

## 4. 正式测试结果

C08 在 io 的 RTX 3090 上运行，decoder 使用一百万对 WMT-massive 英中样本训练 15,625 个更新步。

| 指标 | 测试结果 | 方向 |
|---|---:|---|
| Test NLL | 3.4517 | 越低越好 |
| Token BLEU-4 | 13.8713 | 越高越好 |
| 非空生成率 | 1.000 | 越高越好 |
| 严重重复率 | 0.015 | 越低越好 |
| 峰值显存 | 2.27 GiB | 资源记录 |

### NLL 是什么

NLL 可以理解为：模型看到正确答案时有多意外。

如果正确的下一个 token 得到更高概率，NLL 就会下降。但 NLL 不是完整的翻译质量评价。一个模型可能语句通顺却翻错人物、数字或关系。

### BLEU-4 是什么

BLEU-4 比较生成句子和参考译文中的 1 到 4 token 片段。

`13.8713` 说明模型已经不是随机吐字，也能生成部分正确短语；但它距离可靠翻译仍然很远。

---

## 5. 一个真实输出

输入：

```text
Artificial intelligence can help people understand the world.
```

这个 checkpoint 的输出：

```text
聪明人可以理解世界。
```

它保留了“智能帮助理解世界”的大致轮廓，却把“人工智能”错译成了“聪明人”。

这个例子很好地说明了模型目前的能力边界：

- 已经能够生成通顺的中文短句；
- 能恢复一部分语义轮廓；
- 仍会错译实体、关系、数字、名称和修饰语；
- 不是通用问答模型；
- 不适合生产翻译或高风险场景。

---

## 6. 如何运行

首先下载并解压模型包，再检出 SameTime 的对应 GitHub 标签。安装 PyTorch 和 SentencePiece 后运行：

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

这不是在线聊天服务。CLI 在运行机器本地加载 checkpoint 并执行推理。

---

## 7. C08 支持了什么

当前 evidence 支持以下较窄结论：

1. 固定 64-leaf TreeHeap 可以在真实英中语料上训练；
2. 模型可以进行非 teacher-forcing 生成；
3. 重复 EOS 比确定性随机 token 尾部更容易形成固定 framing 协议；
4. 冻结 encoder 后，带深度下限的 decoder 能学习使用多层 `H_state`；
5. checkpoint、tokenizer、CLI 和原始 evidence 已经可以独立分发和复核。

但 C08 没有证明：

- TreeHeap 已经优于 Transformer；
- EOS 是通用噪声修复方法；
- decoder 可以在没有最低水压时自然维持深层读取；
- 模型已经获得通用世界知识；
- STONE-1 已经完成。

EOS-trained decoder 切回 clean masked 输入时，验证 NLL 恶化 `0.3256`。这意味着它学到的是特定输入约定，不是可以处理任意尾部形式的通用修复能力。

---

## 8. 为什么仍叫 Candidate

STONE-1 正式完成至少还缺三项：

1. **三种子稳定性**：不是只有一次训练达到指标；
2. **正式推理 P50**：把模型加载时间与纯生成时间分开统计；
3. **同 checkpoint 结构审计**：破坏左右地址、递归 detail 或读取深度后，性能必须按照预注册预测下降。

第三项很重要。把参数存进树形数组并不能自动证明模型利用了树。只有结构干预产生稳定、可重复的损失，TreeHeap 的因果作用才成立。

---

## 9. 公开发布架构

这次发布把三个职责分开：

```text
GitHub
  -> 公开源码、版本标签和 CLI

腾讯云对象存储
  -> 保存大体积 checkpoint 和校验文件

www.grepcode.cn CDN
  -> 向公众提供下载
```

博客部署使用独立的站点文件清单，只删除已经从站点中移除的 HTML 和静态资源，不清理 `/models/`。因此删除旧博客时，线上 HTML 仍会同步删除，而模型文件不会被下一次博客部署误删。

这种分离也明确了安全边界：内网 Gitea 负责研发协作，不承担公网下载。

---

## 10. 如何审核

公开源码中的关键材料：

```text
ara/s3-generation/logic/stone1_fixed_root_noise_repair.md
ara/s3-generation/evidence/s3_stone1_fixed_root_noise_repair/
ara/s3-generation/src/treeheap_fixed_root_cli.py
release/stone1-candidate-c08/MODEL_CARD.md
```

GitHub 标签：

```text
stone1-candidate-c08
```

这次发布的意义不是宣布 TreeHeap 已经成功，而是把一个长期研究对象变成了别人真正能够下载、运行、质疑和复测的软件。
