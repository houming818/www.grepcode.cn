---
title: "[SPR-059] TreeHeap 抽水机第一次进入 WMT：递归 READ 成立了，但翻译还没有赢"
date: 2026-07-16
lastmod: 2026-07-16
weight: 59
author: Houming818 & Codex Review
description: "在 27K/2K/2K 英中 WMT 数据上验证 TreeHeap lifting encoder 与 root-first 概率递归 READ：八项机制门全部通过，TreeHeap 明确利用了 root、detail 和递归配对，但 flat sequence baseline 仍有更好的翻译 NLL。"
tags: [SPR, TreeHeap, ARA, WMT, Lifting Scheme, Recursive Read, Probability Container, Encoder, Decoder, Original Research]
---

# TreeHeap 抽水机第一次进入 WMT：递归 READ 成立了，但翻译还没有赢

上一篇 SPR-058 做的是 Echo：一句话先经过 TreeHeap FOLD，形成

```text
H_state = root + 各层 details
```

然后遮住原始 token，只使用 (H_{state}) 做 UNFOLD，能够把输入完整恢复。

这证明 lifting pump 是一个可逆的信息容器，但还没有证明它能完成翻译。因为翻译不是把英语原样抄回来，而是要根据英语状态，逐个生成中文 token。

SPR-059 因此向前走了一步：

> 把真实英文 WMT 句子写入 lifting TreeHeap，再让中文 decoder 从 root 开始递归读取。只用翻译交叉熵训练，不提供路径标签、句法标签、对齐标签或内部节点答案。

结果可以先用一句话概括：

> **TreeHeap 的递归读取机制得到了强证据，但翻译质量仍然没有超过 flat sequence baseline。**

这不是模棱两可。它回答的是两个不同问题：

1. 模型是否真的利用了 TreeHeap 的 root、路径、detail 和递归配对？答案是“是”。
2. 这套实现是否已经比普通序列模型翻译得更好？答案是“否”。

---

## 1. 这次模型究竟在做什么

任务是标准英中翻译：

```text
英文句子
    -> TreeHeap encoder
H_src = root + details
    -> 概率递归 READ
中文 decoder
    -> 下一个中文 token 的概率桶
    -> argmax 坍缩
中文句子
```

其中有三个需要分清的对象：

| 对象 | 本次实验中的含义 |
|---|---|
| (H_{src}) | 当前英文句子的 TreeHeap 状态，即 root 与各层 addressed details |
| (q_t) | 中文生成到第 (t) 步时，decoder 已经积累的查询状态 |
| θ | embedding、lifting predictor、递归 stop/branch kernel 与中文 decoder 的可学习参数 |

θ 不是某一棵输入句子的树。它是所有样本共同训练的规则参数；(H_{src}) 才是当前句子被写入以后形成的状态。

### 1.1 英文如何写进 TreeHeap

英文 token embedding 先放在叶子。每两个相邻状态记为 (L,R)，共享 predictor (P_θ) 计算：

$$
D=R-P_\theta(L),
$$

$$
U=L+\frac12D.
$$

其中：

- (D) 是当前地址保留的 detail；
- (U) 是继续向父节点上传的粗分辨率状态；
- 所有深度共享同一个 (P_\theta)。

这个过程不断递归：

```text
32 leaves
  -> 16 parents + 16 details
  ->  8 parents +  8 details
  ->  4 parents +  4 details
  ->  2 parents +  2 details
  ->  1 root    +  1 detail
```

最终的英文表示不是一个 root 向量，而是：

$$
H_{src}=(root,D^{(5)},D^{(4)},\ldots,D^{(1)}).
$$

root 提供大范围轮廓，detail 保留各个地址上没有被父节点完全表达的差异。

### 1.2 中文 decoder 如何读取这棵树

生成每个中文 token 时，概率质量从 root 的 1.0 开始。

在深度 (d) 的节点 (v)，stop kernel 根据中文查询状态、节点状态和深度计算：

$$
p_{stop}(v,t)
=
\sigma K_{stop}(q_t,H_v,d).
$$

一部分概率停在当前节点，当前节点的信息进入中文 context；剩余概率继续向左右孩子展开：

$$
m_{stop}=m_v p_{stop},
$$

$$
m_{expand}=m_v(1-p_{stop}).
$$

branch kernel 再把 (m_{expand}) 分给 left 与 right。这个过程一直递归到所有概率已经停下，或者走到叶子。

因此，decoder 每一步得到的不是一个硬地址，而是一个跨分辨率的概率前沿：

```text
root             0.20
某个中层节点     0.35
几个更深节点     0.30
部分 leaves      0.15
---------------------
总概率           1.00
```

这些节点的加权和形成当前 source context，再与中文 decoder state 一起计算下一个 token：

$$
p(y_t\mid y_{<t},H_{src}).
$$

训练时只有普通翻译损失：

$$
L_{S2}
=
-\sum_t\log p(y_t\mid y_{<t},H_{src}).
$$

没有任何老师告诉 READ “这里应该停在 root”或“这里应该向左”。如果不同深度的读取规律形成，只能来自翻译 loss 的梯度。

---

## 2. 为什么需要五个模型一起比较

只训练一个 TreeHeap 模型，即使 NLL 下降，也无法判断下降来自哪里。因此实验同时训练五个参数量接近的模型：

| 模型 | 它回答的问题 |
|---|---|
| target-only | 完全不看英语，中文语言模型自己能做到什么程度？ |
| flat sequence | 普通序列 encoder 与 attention 能做到什么程度？ |
| lifting-root | 只给 decoder 一个 root，压缩是否过强？ |
| lifting-full | 完全 UNFOLD 后读取 leaves，完整信息上限如何？ |
| lifting-recursive | 从 root 开始，自己决定在哪个深度停留或下沉 |

`lifting-full` 不是 TreeHeap 效率模型，而是信息对照：它把原分辨率全部展开，告诉我们“信息本身还在不在”。

`lifting-recursive` 才是本文要测试的模型。

---

## 3. 预注册的 Predict

在看正式结果之前，我们先写下八个通过条件：

1. 递归 READ 的 NLL 不高于历史 root-exclusive 结果 6.55；
2. 比 root-only 至少改善 0.05 NLL；
3. 与 full UNFOLD 的差距不超过 0.10 NLL；
4. 打乱完整英文状态至少损失 0.20 NLL；
5. root 与至少一层 detail 必须具有因果作用；
6. 至少两个深度的左右配对破坏必须造成损失；
7. READ 必须使用至少两个分辨率，不能全部坍缩到 leaves；
8. FOLD/UNFOLD 闭包、有限梯度与非空生成必须通过。

这里最重要的是第 4 到第 7 条。它们防止我们把“模型输出了中文”误报成“模型使用了 TreeHeap”。

---

## 4. 数据与训练规模

正式实验在 `io` 的 RTX 3090 上运行：

| 项目 | 数值 |
|---|---:|
| 方向 | English -> Chinese |
| 训练/验证/测试 | 27,000 / 2,000 / 2,000 |
| 词表 | 16,001 |
| 状态维度 | 256 |
| epoch | 10 |
| 最佳模型选择 | 最低 validation NLL |
| 总运行时间 | 1,398.49 秒 |
| FOLD/UNFOLD MSE | 1.73e-14 |

长度过滤后数据共有 31,337 条，正式拆分使用了其中 31,000 条。实验没有报告多 seed，因此它仍是一次 full-scale mechanism proof，不是最终统计结论。

---

## 5. 指标像体检报告一样怎么看

### 5.1 NLL：越小越好

NLL 是模型给正确中文 token 分配的负对数概率。正确答案概率越高，NLL 越小。

### 5.2 PPL：越小越好

$$
PPL=e^{NLL}.
$$

它可以粗略理解为：模型在每一步还像是在多少个候选之间犹豫。它不是候选数的字面值，但越小通常越好。

### 5.3 Token BLEU-4：越大越好

它检查生成结果与参考译文是否共享连续 token 片段。本文数值整体很低，说明五个小模型都远未达到实用翻译质量。

---

## 6. 主结果：结构机制通过，质量没有获胜

| 模型 | 参数量 | Test NLL ↓ | PPL ↓ | Token BLEU-4 ↑ |
|---|---:|---:|---:|---:|
| target-only | 12.96M | 5.7189 | 304.57 | 0.117 |
| flat sequence | 17.45M | **4.8103** | **122.77** | **3.169** |
| lifting-root | 17.32M | 5.4337 | 229.01 | 1.585 |
| lifting-full | 17.32M | 5.1342 | 169.73 | 1.881 |
| lifting-recursive | 17.52M | **5.0903** | **162.44** | **2.528** |

### 好消息

递归 READ 比 root-only 改善：

$$
5.4337-5.0903=0.3434.
$$

这说明一个 root 不够；读取 addressed details 明显有价值。

递归 READ 还比完全 UNFOLD 小幅改善 0.0439 NLL。一个合理但尚未证明的解释是：概率前沿起到了结构化正则化作用，没有让 decoder 在每一步同时面对全部 leaves。

### 坏消息

flat sequence 仍然领先递归 TreeHeap：

$$
5.0903-4.8103=0.2800.
$$

BLEU-4 也低 0.641。TreeHeap 目前获得的是“存在性”，不是“优越性”。

---

## 7. 它真的使用了 TreeHeap 吗

这是本文最强的证据。

以正常递归模型 NLL `5.0903` 为基准：

| 干预 | NLL 增量 | 含义 |
|---|---:|---|
| 打乱完整 source H_state | +1.4450 | 输出强依赖当前英文句子 |
| 只打乱 root | +1.7204 | root 是强因果状态，不是装饰 |
| 强制只读 root | +1.1773 | 只看全局轮廓不够 |
| 强制一直走到 leaves | +0.6236 | 只看最细粒度也不够 |

五层 detail 分别打乱后的损失：

```text
+0.1171, +0.1422, +0.2402, +0.4960, +0.4857
```

五层左右子树配对被跨样本破坏后的损失：

```text
+0.4807, +0.4414, +0.4107, +0.4354, +0.2105
```

所有深度都不是中性的。也就是说，模型不只读取了一袋向量；它依赖“哪个 detail 在哪个深度”和“哪些左右子树被组合在一起”。

正常 READ 的平均 stop mass 为：

| 深度 | Stop mass |
|---:|---:|
| root | 0.3329 |
| depth 1 | 0.0288 |
| depth 2 | 0.1283 |
| depth 3 | 0.0384 |
| depth 4 | 0.0073 |
| leaves | 0.4643 |

总和为 1。模型主要使用 root 和 leaves，但中间分辨率也承担了约 20.3% 的概率质量。这就是“多分辨率 READ”的实证含义。

---

## 8. 真实生成样例

下面不是 cherry-pick 的最佳句子，而是测试集开头的典型输出。它们能更诚实地说明当前能力边界。

### 样例一：抓到了财政主题，但句法和词义仍然混乱

**英文输入**

> As economies then weakened, the prospects for fiscal consolidation grew dimmer.

**参考译文**

> 经济随之疲软，因此财政整合前景也变得更加虚弱。

**flat sequence**

> 新兴经济体开始，其财政前景似乎出现了了。

**递归 TreeHeap**

> 由此从那时，其银行也变得越来越微财政巩固。

TreeHeap 读出了“财政巩固”和趋势变化的主题，但没有组成正确中文。这里能看到 source signal，不是可用翻译。

### 样例二：主题词正确，重复坍缩严重

**英文输入**

> Bond prices then fell further, damaging European banks even more.

**参考译文**

> 这造成债券价格进一步下跌，给欧洲银行造成更多的伤害。

**flat sequence**

> 价格下跌进一步下跌，银行也更加更加更大。

**递归 TreeHeap**

> 进一步进一步进一步进一步进一步进一步进一步进一步上升，欧洲银行甚至进一步上升。

TreeHeap 找到了“进一步”和“欧洲银行”，却把“下跌”生成成“上升”，并陷入重复循环。这是 decoder 与训练规模的明确失败，不应被结构干预的成功掩盖。

### 样例三：知道在谈银行和融资，但关系没有还原

**英文输入**

> Reassured that they will have access to funding, the banks again have the confidence to lend.

**参考译文**

> 银行获得了能够得到融资的保证，因此重新获得了发放贷款的信心。

**递归 TreeHeap**

> 他们在他们方面会继续下去，但银行银行再次进入了。

它保留了“银行”“再次”以及继续发生某事的轮廓，但融资、保证、贷款和因果关系都没有正确解码。

### 样例四：flat baseline 明显更接近参考答案

**英文输入**

> Tax increases and cuts in public spending are still needed; there is no avoiding this reality.

**参考译文**

> 加税削减了仍属必须的公共支出；这是不可避免的现实。

**flat sequence**

> 削减公共支出削减公共支出削减；但依然存在这一现实。

**递归 TreeHeap**

> 税收支出支出支出支出支出，在这个问题上中，我们还有很容易。

这个样例直观解释了为什么 flat baseline 的总体 NLL 和 BLEU 更好。

---

## 9. 八个 Predict 的最终体检

| Gate | 结果 |
|---|---|
| P1：超过历史 root-exclusive NLL | PASS |
| P2：递归优于 root-only | PASS |
| P3：接近 full UNFOLD | PASS |
| P4：完整 source 状态具有因果性 | PASS |
| P5：root 与 detail 都具有因果性 | PASS |
| P6：多个递归配对深度具有因果性 | PASS |
| P7：使用多个分辨率 | PASS |
| P8：闭包、梯度与非空生成 | PASS |

因此 Claim `S2-LIFT-WMT-C01` 的准确状态是：

```text
TreeHeap mechanism: supported
Translation superiority: rejected
Compression advantage: open
Compute advantage: open
Production translation: not supported
```

---

## 10. 下一步不应该做什么

不应该因为八个 gate 全过，就直接把数据扩大一百倍并宣布成功。

当前实现还有三个明确问题：

1. flat sequence 仍领先 0.2800 NLL；
2. 中文 decoder 有严重重复和关系反转；
3. 代码会先物化所有 TreeHeap 层，再计算概率 READ，因此还没有获得真正的稀疏计算优势。

也不应该把中间深度人工命名成“主语层”“语义层”或“意识层”。实验只证明这些状态具有因果作用，没有证明它们对应人类可读语法。

---

## 11. 下一步真正值得验证什么

我认为下一步有三个优先级。

### 第一：修复生成，而不破坏结构读法

保留同一个 lifting encoder 和递归 READ，升级 target decoder，并加入重复惩罚、长度控制与更稳的解码评估。目标是缩小对 flat baseline 的 0.2800 NLL 差距。

### 第二：做真正的按需 UNFOLD

现在所有层都已经算好。下一版应该只展开仍然携带概率质量的节点，统计：

```text
访问节点数 / 完整树节点数
实际 FLOPs
显存
延迟
```

只有在质量接近且访问节点显著减少时，才能讨论 TreeHeap 的压缩检索优势。

### 第三：跨 seed 复核

至少运行三个 seed，报告均值、标准差和干预效应区间。递归模型略胜 full UNFOLD 的 0.0439 NLL 很小，单次实验不足以把它升级成稳定优势。

---

## 12. 最终结论

SPR-058 证明 lifting pump 能把信息抽上去并严格放回来。SPR-059 进一步证明：

> 在真实 WMT 数据上，普通翻译梯度可以训练出一个从 root 开始、依赖地址与递归配对、在多个 TreeHeap 分辨率之间分配概率的 READ。

这是我们第一次不靠 Echo、不靠内部标签，看到 TreeHeap 结构参与真实 S2 任务。

但样例也非常诚实：模型还不会稳定地说中文，重复、反义词和关系丢失都很严重。TreeHeap 现在拥有了一条可信的数据通路，还没有获得更强的产品能力。

这条边界必须保留。因为真正值得继续研究的，不是把一次机制 proof 写成胜利，而是已经知道下一块损失具体在哪里。

---

## Evidence

- ARA claim：`S2-LIFT-WMT-C01`
- Predict：`P-S2-LIFT-WMT-01`
- SameTime commit：`fb17f8f`
- [实验设计与结论](https://github.com/houming818/sametime/blob/main/ara/s3-generation/logic/s2_lifting_pump_wmt.md)
- [复现实验代码](https://github.com/houming818/sametime/blob/main/ara/s3-generation/src/s2_lifting_pump_wmt.py)
- [完整 summary.json](https://github.com/houming818/sametime/blob/main/ara/s3-generation/evidence/s2_lifting_pump_wmt_full/summary.json)
- Checkpoints：`/mnt/nas/ara/s3-generation/evidence/s2_lifting_pump_wmt_full/`

本文中的 TreeHeap 实验设计、实现与结论记录按本项目许可证公开。lifting scheme 等已有数学工具不被主张为本项目原创；原创部分限定为本次组合设计、可证伪实验和相应 evidence。
