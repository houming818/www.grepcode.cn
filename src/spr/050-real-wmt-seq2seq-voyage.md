---
title: "[SPR-050] 第一次真实语言生成：TreeHeap 从英文到中文，但还不是问答"
date: 2026-07-11
lastmod: 2026-07-11
weight: 50
author: Codex Review
description: "记录首次真实 WMT 英中 seq2seq 运行：TreeHeap encoder-decoder 已能生成主题相关的中文句子，但当前落后 flat GRU；这验证的是 S3 表面生成通路，不是问答或翻译成果。"
tags: [SPR, TreeHeap, ARA, S3, Seq2Seq, WMT, Generation, Evidence]
---

# 第一次真实语言生成：TreeHeap 从英文到中文，但还不是问答

前面的很多实验都很小：echo、路由、内部节点读出、概率桶、受控符号任务。它们帮助我们确认 TreeHeap 的一些局部算子可以工作，但始终留下一个最实际的问题：

```text
TreeHeap 能不能真正参与自然语言的“输入一句话，输出另一句话”？
```

这次我们不再使用 toy token，也不读取历史上已经被降级的 TreeHeap checkpoint。我们直接在真实 WMT 英中平行语料上，从零训练一个最小的 seq2seq 系统。

先说结论：

```text
真实文本的 TreeHeap encoder -> decoder 通路已经跑通。
它能输出成句、主题相关的中文。
但当前它没有赢过普通 flat GRU，也不能称为翻译成果。
更重要的是：这仍然不是问答任务。
```

这是一份首航报告，不是庆功报告。

## 1. 为什么先拿 WMT 做 seq2seq？

最终目标不是机器翻译，而是：

```text
question + context
  -> TreeHeap encoder
  -> answer decoder
  -> answer
```

也就是问答。

但问答数据需要三元组：

```text
上下文、问题、答案
```

手头的 WMT 数据提供的是另一种真实的输入输出对：

```text
英文句子 -> 中文句子
```

它不能证明模型会回答问题，却很适合先验证一个更基础的门：

```text
TreeHeap 能否接收真实文本，
把它编码成可供 decoder 使用的状态，
并连续生成多步中文 token？
```

如果这一步都不成立，直接谈 QA 只会把 encoder、decoder、数据和评价混成一团。

所以这次 WMT 的身份是：

```text
真实语言 seq2seq generation gate
```

不是最终 QA benchmark。

## 2. 这次模型到底长什么样？

输入是英文 SentencePiece token。例如：

```text
English sentence
  -> [t1, t2, t3, ...]
```

每个 token 先写入 TreeHeap 的叶子。然后按 left/right 递归组合：

```text
        parent
       /      \
    left     right
```

局部组合不是简单相加：

```math
h_parent = Compose_theta(h_left + e_left, h_right + e_right)
```

`e_left` 和 `e_right` 是不同的槽位向量，所以：

```text
Compose(a, b) != Compose(b, a)
```

这保留了顺序。

经过多层递归后，模型同时拥有：

```text
叶子节点：具体英文 BPE token
内部节点：局部短语/子堆摘要
root：整句摘要
```

中文 decoder 每生成一个 token，都产生一个 query。它不是只读 root，而是在所有有效节点上分配概率：

```math
p(i | q_t, H) = softmax(K_theta(q_t, h_i))
```

再把各节点状态按概率混合成当前上下文：

```math
c_t = sum_i p(i | q_t, H) h_i
```

最后生成下一个中文 token。

这可以理解为：

```text
decoder 每说一个中文词，
都在 TreeHeap 的叶子和内部子堆之间做一次概率读取。
```

训练时只有标准的 teacher-forcing 交叉熵：

```math
L = sum_t CE(P(y_t | y_<t, H(x)), y_t)
```

没有人工句法树、没有 route 标签、没有类别标签、没有五个 loss 的大锅炖。

## 3. 真实数据与对照

数据：

```text
/mnt/nas/datasets/wmt17/train.zh-en
方向：English -> Chinese
训练 / 验证 / 测试：30,000 / 2,000 / 2,000
最大 BPE 长度：24
训练：10 epochs
GPU：io 的 RTX 3090，270W 限制保持不变
```

我们没有只跑 TreeHeap。三种 encoder 使用相同的自回归中文 decoder 与相同的翻译 loss：

| Encoder | 输入能保留什么？ |
|---|---|
| BoW | 英文 token 的平均向量，不保留顺序。 |
| Flat GRU | 有序英文 token 序列。 |
| TreeHeap | 英文叶子、递归内部子堆、root。 |

这使问题变得很朴素：TreeHeap 现在到底比无序词袋、比普通有序序列，做得怎样？

## 4. 数字结果

完整运行耗时：

```text
606 秒，约 10.1 分钟
```

| Model | Test NLL ↓ | PPL ↓ | token-BLEU4 ↑ |
|---|---:|---:|---:|
| TreeHeap | 5.129 | 168.8 | 1.48 |
| BoW | 4.948 | 140.9 | 1.43 |
| Flat GRU | **4.799** | **121.4** | **2.87** |

这里的 `token-BLEU4` 是脚本内的 BPE-token 近似指标，不是官方 WMT BLEU，不能拿来和论文榜单比较。

数字的诚实解释是：

```text
TreeHeap 已经能学习真实 seq2seq。
TreeHeap 的生成指标略高于 BoW，但差异很小。
TreeHeap 明显落后于 flat GRU。
```

所以这轮不能支持：

```text
TreeHeap 当前配置优于普通序列模型。
```

## 5. 输出到底像不像中文？

看几个测试集样例。下面没有润色。

```text
EN: In order to fund this spending, revenues must be raised.
REF: 为了支撑这笔费用,就必须增加政府收入。
TH : 鉴于这一观点,我们必须增加支出。
```

```text
EN: When it comes to economic policy, a fast, faulty decision is often better than inaction.
REF: 当谈到经济政策时,一个快速的、错误的决定通常是比无所作为要好。
TH : 鉴于经济决策,但通常比经济决策,因为其决策的境况通常是积极的。
```

```text
EN: Furthermore, the slow pace of European decision-making has compounded Greece's troubles.
REF: 此外,欧洲缓慢的决策过程也加深了希腊的麻烦。
TH : 此外,英国选民决定了欧洲国家,但英国退出投票。
```

这些结果同时说明两件事。

第一，正面信号：

```text
模型并非输出随机 token。
它学会了中文连接方式、部分句式、标点和主题领域词。
“欧洲 / 希腊 / 经济 / 决策 / 支出”等语义场会进入输出。
```

换句话说，S3 的表面语言 decoder 已经开始工作。它不再只是输出类别桶，也不只是复制输入。

第二，关键不足：

```text
主题相近，不等于关系正确。
```

模型经常把训练集中同一主题的短语拼接到一起：

```text
欧洲 -> 英国
财政刺激 -> 财政紧缩
决策缓慢 -> 退出投票
```

句子表面像中文，但事实关系、指代和谓词绑定仍然很不稳定。

## 6. TreeHeap 内部节点有没有参与？

我们还做了一个不重新训练的读取消融：

```text
full       可读叶子和所有内部子堆
leaf_only  隐藏内部节点，只读叶子
root_only  只读整句 root
```

greedy 生成的 token-BLEU4：

| Read mode | token-BLEU4 |
|---|---:|
| full | 1.48 |
| leaf_only | 1.26 |
| root_only | 0.037 |

这说明 root 不是一个足够的万能 hash：只给 root 时，生成几乎崩溃。完整 TreeHeap 比 leaf-only 有小幅提升，说明内部节点可能已经带来一部分可用信息，但增益仍然很弱。

有一个审计细节必须记录：当前脚本的 ablation NLL 仍错误地沿用了 full-memory 的 teacher-forcing 路径，因此 ablation 的 NLL 相同、不能解释。上表只使用实际走 ablation read path 的 greedy generation 指标。下一次应加载本次 checkpoint 修正后重算，不必重训。

## 7. 这不是 QA，但它为 QA 打开了什么？

问答任务应该是：

```text
[QUESTION] + [CONTEXT]
  -> TreeHeap
  -> answer tokens
```

这次 WMT 实验没有 question，也没有 answer span，因此不能叫 QA。

但它已经确认了 QA 所需的一条基础通路：

```text
真实文本
  -> TreeHeap encoder
  -> 多步 decoder
  -> 自然语言输出
```

下一步不是继续把翻译 BLEU 当最终目标，而是换成真实 QA 三元数据：

```text
context, question, answer
```

然后比较：

```text
TreeHeap encoder
BoW encoder
flat sequence encoder
```

评价也应换成 QA 的答案指标，例如 exact match、token F1、ROUGE 或 answer BLEU，而不是只看翻译分数。

## 8. 当前 ARA 状态

```text
S3-WMT-SEQ2SEQ-C01
  -> supported feasibility / negative comparative result
```

它支持的是：

```text
TreeHeap 可以从真实 WMT 文本端到端训练，
并驱动一个中文 seq2seq decoder 产生可读、主题相关的句子。
```

它不支持的是：

```text
TreeHeap 已优于 flat sequence。
TreeHeap 已完成翻译。
TreeHeap 已完成问答。
TreeHeap 已学到稳定世界模型。
```

这份边界不是泼冷水。它把下一步变得非常明确：先修正 internal-node ablation 的 teacher-forcing 评价，再接入真实 QA 数据，让 TreeHeap 的子堆读取回答“哪段 context 支撑当前答案”。

