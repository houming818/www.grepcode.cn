---
title: "[SPR-074] 为什么 Loss 在下降，模型却只会一句话：C10 勘误与证据撤回"
date: 2026-07-28
lastmod: 2026-07-28
weight: 74
author: Houming818 & Codex Review
description: "公开说明 STONE-1 C10 的条件坍缩、teacher forcing 混杂与 EOS 尾部问题，并逐项界定哪些历史结论保留、哪些必须撤回。"
tags: [SPR, TreeHeap, ARA, STONE-1, Retraction, Teacher Forcing, Mode Collapse, NLL]
---

# 为什么 Loss 在下降，模型却只会一句话

这是一次正式勘误，不是给失败结果换一种好听说法。

C10 完成了约 `1.410B` 个目标 token 的训练，验证 NLL 从 `16.7848` 降到 `4.7275`。仅看曲线，模型似乎持续学习。然而 Houming818 用三个明显不同的英文输入测试同一个 checkpoint：

```text
The earth is round.
The apple is sweet
why is the window wet? because the sky cried
```

三个输出都迅速进入近乎相同的“一带一路”重复句式，而且 48 个输出 piece 内没有正常结束。这不是偶然误译，而是严重的**条件坍缩**：模型没有根据不同英文条件产生不同答案。

因此，C10 不能作为翻译成功、STONE-1 完成或私有协议形成的证据。

## 1. 为什么输出一样，训练 Loss 还能下降

训练和 CLI 实际执行了两个不同任务。

训练使用 teacher forcing。预测第 $t$ 个中文 token 时，decoder 会收到正确的中文前缀：

$$ p(y_t\mid y^{gold}_{\lt t},x) $$

这里 $x$ 是英文 source，$y^{gold}_{\lt t}$ 是答案中已经给出的正确中文前缀。

CLI 自由生成时没有答案可看，只能把自己刚刚生成的 token 喂回去：

$$ p(y_t\mid y^{model}_{\lt t},x) $$

假设训练样本分别是“苹果很甜”和“地球是圆的”。即使模型完全忽略英文，只要训练时已经看到“苹果很”或“地球是”，也可能比较容易猜出下一个字。因此 NLL 仍会下降。

自由生成从同一个 BOS 开始。如果第一步选中了高频逗号，后续预测就可能滑进训练语料中最强的中文模板。C10 进入的正是“一带一路”吸引子。

所以这条 NLL 曲线真实记录了优化过程，却回答错了研究问题：

```text
它测到了：给定正确中文前缀，能否继续中文。
它没证明：给定不同英文，能否生成对应中文。
```

## 2. 第二个问题：EOS 尾部淹没了英文

C10 的 TreeHeap 有 256 个可见 leaf，而 source 最多使用前 128 个位置。短句只有约 6 到 11 个有效 piece，其余大量位置被写成 EOS，并且仍作为可见节点参加递归 FOLD。

以 6-piece 输入为例，实际状态接近：

```text
6 个英文 piece + 250 个可见 EOS
```

不同英文句子的少量差异，被放进几乎相同的大面积 EOS 背景中。我们尚未完成定量消融，但从代码结构上看，这足以构成严重混杂，必须修复后重测。

## 3. 哪些结论撤回，哪些仍保留

| 历史内容 | 新状态 | 原因 |
|---|---|---|
| C10 是有效翻译 checkpoint | 撤回 | 三个无关输入生成同一模板 |
| C10 NLL 证明英文到中文学习 | 撤回 | teacher forcing 允许忽略英文 |
| C09 已完成 STONE-1 | 暂停 | 同族评测 gate 没有排除 source 忽略 |
| C08 可公开下载 | 保留 | 文件和复现价值仍在 |
| C08 是可靠翻译候选 | 暂停 | 需要重新做条件依赖审计 |
| detail shuffle 会改变 NLL | 保留观测 | 数字本身没有伪造 |
| detail shuffle 证明英文语义进入树 | 撤回外推 | 它只证明 decoder 依赖某些树状态 |
| M0 代数、mirror、compose/decompose proof | 不受影响 | 它们不依赖 C10 翻译 Loss |
| 旋转与预算训练假设 | 保留为开放假设 | 尚未被 C10 成功或失败直接验证 |

我们不会删除旧文章。主要受影响文章顶部会增加证据状态更新；仍在修订中的 SPR-073 由本文统一覆盖。这样外部读者能看到结论如何形成，也能看到它后来如何被反例推翻。

## 4. 为什么现有 BLEU 也没有及时拦住问题

早期实验确实记录过自由生成 BLEU、非空率和重复率，但这些汇总指标没有覆盖以下关键问题：

1. 不同 source 是否产生真正不同的输出；
2. 打乱 source 后 Loss 是否基本不变；
3. 清空 source 后 decoder 是否仍能依靠中文前缀预测；
4. 第一个输出 token 在尚无中文前缀时，是否随英文变化。

只测“输出非空”远远不够。一个复读机当然也能稳定输出非空文本。

## 5. 重启训练前必须通过的四道门

### Gate A：Source shuffle

固定中文 target 和正确前缀，只在 batch 内打乱英文 source。记正常 Loss 为 $L_{native}$，打乱后为 $L_{shuffle}$。

真正依赖英文的模型应满足：

$$ L_{shuffle}-L_{native}>0 $$

而且差异必须超过预注册门槛和多 seed 波动。

### Gate B：Empty source

把英文换成全 EOS 或严格 mask 的空输入。如果 NLL 几乎不变，说明 decoder 主要是中文语言模型。

### Gate C：First-step logits

生成第一个 token 时还没有中文历史，这是最干净的 source 依赖测试。不同英文输入的 first-step 概率分布必须出现可重复差异，而不是永远选择同一个逗号。

### Gate D：自由生成体检

固定测试集必须报告：

```text
unique-output rate
source-output conditional diversity
repetition rate
EOS arrival rate
BLEU / chrF
人工样例
```

这些 gate 未通过前，不再启动几十小时的扩容训练。

## 6. 代码应该怎样修

第一步不是立刻增加模型参数，而是恢复问题定义：

1. source 的可见长度只覆盖真实 token 和必要的结构节点；padding 不得伪装成大量有效 EOS；
2. 训练和验证保留 token 交叉熵，但增加 wrong-source 对照；
3. 每次验证同时运行 teacher-forced 与 free-running 两条路径；
4. checkpoint 选择不能只看 teacher-forced NLL；
5. 长训练前先用小规模数据证明 source shuffle 和 empty source 会显著恶化结果。

可以加入一个条件依赖约束：要求错误 source 的损失高于正确 source。若间隔为 $m$，则可写成：

$$ L_{dep}=\max\left(0,m+L_{native}-L_{wrong\ source}\right) $$

但它只是候选修复，必须先做消融，不能直接当成正确答案。

## 7. 本次真正得到的证据

这次最有价值的证据不是 `NLL=4.7275`，而是三个手工 CLI 输入。

它们指出：我们的自动 gate 没有覆盖最基本的产品问题。Houming818 的一句“它只会说这个，Loss 怎么可能还在降”，迫使代码审计回到训练函数本身，最终找到了 teacher forcing 与自由生成之间的断层。

因此当前航行状态是：

```text
C10 长训练：完成，但翻译 Claim 无效
C09 STONE-1 完成状态：暂停
C08 公开制品：保留，翻译身份待复审
下一步：先证明 source 真正进入计算，再谈规模化
```

公开错误不是项目的附属工作，而是 ARA 的核心功能。数据没有被删除，旧文章没有被偷偷改成“我们早就知道”，错误的结论也不会继续作为下一条 Claim 的地基。

> **License: GPLv3。本文的勘误、审计方法和后续 falsification gate 与 SameTime/ARA 一并公开。**
