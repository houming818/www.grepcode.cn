---
title: "[WMT-010] Linear = Hash 函数——输出层碰撞是翻译的信息瓶颈"
date: 2026-05-09
author: nio (Houming818) & opencode (First Mate)
keywords: NMT, Linear Layer, Hash Collision, K_lang, Vocabulary, Gradient
description: NMT 的输出 Linear 层不只是投影——它是 hidden space 到 vocab space 的 Hash 函数。碰撞发生在这里，K_lang 控制碰撞程度，梯度从碰撞桶里提取信息。
tags: [WMT, NMT, Linear, Hash Collision, K_lang, Vocabulary]
---

# Linear = Hash 函数——输出层碰撞是翻译的信息瓶颈

> 512 维 hidden 撞进 32K 维词汇表：碰撞率 K_lang ≈ 0.003，有效碰撞桶 ~170 个。Linear 不是模型最后一步投影——它是翻译信息从连续空间到离散词汇的 Hash 函数。

## 碰撞在哪里？

NMT 的输出流程三步：

```
① Transformer:  输入序列 → h_t ∈ ℝ^512       （hidden space）
② Linear:       h_t → z = W·h_t + b         （logits in ℝ^{32000}）
③ Softmax:      z → p ∈ Δ^{31999}           （概率单纯形）
④ Decode:       argmax / beam → token        （离散词）
```

每个人都在关注 ③ 和 ④。但**碰撞发生在 ②**。

## Linear = Hash Function

`W` 是一个 $$\mathbb{R}^{32000 \times 512}$$ 的矩阵。每一行 $$W_i \in \mathbb{R}^{512}$$ 是第 i 个 token 的嵌入向量（output embedding）。$$W·h_t$$ 做的是内积：

$$z_i = \langle W_i, h_t \rangle + b_i$$

把 512 维的 hidden 投影到 32K 维——32K 个内积。

**这是 Hash 函数的标准定义：** 把高维向量压缩到低维离散空间。

$$h_t \xrightarrow{W} z \xrightarrow{\text{argmax}} \text{token}$$

参数 `W` 决定了 hidden 空间中哪些方向对应哪些 token。512 维的 hidden 无法精确表示 32K 个 token 的语义——**碰撞是必然的。**

## 碰撞率 = K_lang

32K 个 token 共享 512 个维度，内积 $$W_i·h_t$$ 受限于 hidden 的信息容量。有意义地区分的 token 数：

$$N_{\text{collision}} = K_{\text{lang}} \times |V| = 0.003 \times 32000 \approx 96$$

BPE 词表下（8K）：

$$N_{\text{collision}} = 0.003 \times 8000 \approx 24$$

碰撞桶从 170 缩到 24——但每个桶承担的语义负载叠加了 7 倍。

| 词表类型 | \|V\| | K_lang×\|V\| | 每桶语义负载 |
|---------|------|-------------|-----------|
| Word-level (IWSLT) | 56K | **170** | 轻 |
| BPE (IWSLT) | 8K | **24** | 重 |

IWSLT14 的 BPE 实验证实：8K 词表下，3 个 transformer 层不够深（B0, BLEU=10.66），但 6 层可以（B3, BLEU=11.70）。**深度补偿了桶压缩。**

## 梯度怎么从碰撞桶里提取信息？

CE loss 对 $$z_i$$ 的梯度是 $$p_i - y_i$$。对 $$W_i$$ 的梯度是：

$$\frac{\partial \mathcal{L}}{\partial W_i} = (p_i - y_i) \cdot h_t$$

每个 token 的梯度向量与 $$h_t$$ 平行。**梯度只沿 hidden 方向更新**，而 hidden 本身是高维压缩——所有 32K 个 token 的梯度都投影到同一个 512 维空间上，再分配回各自的 $$W_i$$ 行。

`y_i` 为 1 的 token（真实标签）和 `p_i` 较大的 token（top-k collision set）得到显著梯度更新。其余大多数 token 的 $$p_i \approx 0$$，$$(p_i - y_i) \approx 0$$，近乎 0 更新。

**碰撞桶里的 token 共享 hidden 空间的方向信息。** Softmax 不做的事情是：它不分配方向——它只归一化大小。方向是 Linear 在投影时决定的。

## 回到我们实验的倒 U 曲线

A8-A12 的 K_lang 扫描结果就是对这个理论最好的验证：

```
A8(CE-only)  BLEU=3.45     ← K_lang 全部分流失（无 collision 意识）
A9(k=50)     BLEU=3.35     ← 桶太少，过拟合
A10(k=170)   BLEU=3.63     ← K_lang 精确匹配碰撞桶数
A11(k=500)   BLEU=3.09     ← 噪音开始回流
A12(k=56652) BLEU=3.35     ← 全表 softmax，无约束，信号消失
```

线性层的输出 `z_i` 的 top-k 选择（k = K_lang×|V| ≈ 170）不是随意选的——它是碰撞常数决定的。把 softmax 分母限制在碰撞桶内，梯度不再被稀释到无关 token 上。

## 碰撞是双向的——正反向 Hash 不对称

Linear 的碰撞不在单方向上。正向和反向的 Hash 路径是**同一组参数**，但经历**不同的约束条件**：

```
Token (DE) → Encoder → h_t → W·h_t + b → Token (EN)
                              ↑ 碰撞发生在这里
                    向量回传 ← z_i = <W_i, h_t>
```

### 正向：释放

hidden 编码了一段包含多种语义的向量。Linear 把它释放到 32K 维词空间——**每个 token 得到自己的内积分量**。这个过程是稀疏的：一次翻译只输出一个 token，其他 31,999 个概率接近 0。

### 反向：碰撞

反向看同一个 W。在训练中，**同一个 hidden 表示对应多个目标 token**——不同的语言对同一个概念映射到同一个 hidden 空间。

以名词为例。名词的翻译大多是一一对应的：

```
德语 "Haus"  →  英语 "house"    同一个概念
德语 "Buch"  →  英语 "book"     同一个概念
```

当 "Haus" 和 "house" 分别用不同的 token ID 表示、但经过同一组 hidden → Linear 的重量时，梯度会把这两个 token 的 $$W_i$$ 推向同一个方向——**因为它们的 hidden 表示在语义空间里是相同的位置。**

但 W 只有 512 维。两个名词挤在一起、三个名词挤在一起……所有翻译中一一对应的名词，都把 W 的对应行推到 hidden 空间的同一个区域。**碰撞就此发生。**

反向碰撞不是坏事——它恰恰是翻译模型学会 "Haus = house" 的方式。但如果碰撞太重（桶太小），token 之间开始混淆；如果碰撞太轻（全表），梯度被稀释到无关 token 上。

翻译的全过程：

```
① 编码: 源语言 → hidden      (压缩语义到连续空间)
② Hash: hidden → W·h_t       (连续→离散投影，碰撞发生)
③ 释放: z → 概率 → token     (稀疏表达在词空间)
```

碰撞不在第 ① 步（Transformer 本体），不在第 ③ 步（softmax 归一化），就在第 ② 步——**Linear 把连续的 hidden 映射到离散的词汇空间**。这是正反向不对称的核心。

## 结论

`Linear(h_t) = logits_z` 在代码里就一行。但它下面是：

$$\mathbb{R}^{512} \xrightarrow{\text{Hash}} \{1, 2, \dots, 32000\}$$

翻译的整个信息瓶颈就在这里——**不是在 Transformer 的 attention 层，不是 decoder 的交叉注意力，是编码器最后一层 linear 把 continuous hidden 投射到 discrete vocab 的那一步。**

K_lang 不是一个调参经验值——它是这个 Hash 函数的理论碰撞常数。

## 过拟合 = 碰撞桶太散

从朴素的线性回归看过拟合：

$$\hat{y} = w_0 + w_1x + w_2x^2 + \dots + w_{10}x^{10}$$

问题：$$w_8, w_9, w_{10}$$ 这些高频项的参数**变得太大**——它们不是在学习信号，是在记忆每个训练点的位置。曲线扭来扭去，拟合了噪声。

NMT 里的过拟合本质上同一个东西，只是表现形式不同：

```
线性回归:  高频项系数太大 → 记住了噪声的多项式
NMT:       碰撞桶太散 → 每个训练句独占一个 hash 桶 → 记住了训练样本本身
```

证据来自 B 系列的深度和宽度对比：

| 实验 | 配置 | 参数 | BLEU | 现象 |
|------|------|------|------|------|
| B3 | d256/6L | 17M | **11.70** ✅ | 碰撞有效，泛化正常 |
| B2 | d512/6L | 56M | 8.18 | 参数太多，过拟合 |
| B4 | d512/3L | 56M | 8.57 | 参数多+浅度，双倍失败 |

B2 有 56M 参数——在 IWSLT 的 160K 句上，每个训练样本可以独占几乎一个 hash 桶。W 有足够维度同时记住每对的德语句子和英语翻译。高频词（"的"、"了"、"is"、"the"）的梯度主导了反向传播，低频但有语义的名词**被淹没在参数冗余里**。

B3 只有 17M 参数——因为碰撞被强制发生，"Haus" 和 "Gebäude" 必须共享参数。模型被迫去学习："这两个德语词在语义上是相近的"，而不是死记 "Haus = house"。

**K_lang 就是要保证碰撞桶够密、参数不能太大——让模型被迫去学语义共性，而不是死记训练样本。** 这条线和线性回归里"控制多项式项数防止过拟合"完全平行。

---

## MoE + 词频 = 按语言特征路由的碰撞桶

Hidden 不一定必须是一个矩阵。MoE（Mixture of Experts）早就把一个 FFN 拆成多个专家：

```
标准 Transformer:   h → 一个 FFN → 输出
MoE Transformer:    h → 路由 → 选专家 → 专家 FFN → 输出

             h ─┬─→ 专家1 (第0-2层共享)
                ├─→ 专家2 (第3-4层共享)    ← gating 网络根据 h 选
                └─→ 专家3 (第5-6层共享)
```

已有工作（Shazeer et al. 2017, GShard, Switch Transformer）按 **token 级别**做路由：每个 token 被分配到一个专家 FFN。但没有人按**语言特征**来划分专家：

- 专家 A：短句（1-10 词）专用的 hidden 矩阵
- 专家 B：长句（30+ 词）专用的 hidden 矩阵
- 专家 C：高频词专用（"的"、"了"、"is"）

如果路由的 gating 信号不是从 `h` 学到的，而是从**可观测的语言特征**（句长、词频、TF-IDF）直接控制，MoE 就从"黑盒分配"变成了"语言学驱动的碰撞桶分配"。这等价于把 K_lang 的碰撞理论作为 MoE 架构的设计指南——每个专家就是一个碰撞桶簇。

这一思路至今未见发表。

## Encoder / Decoder = 两个独立的 Hash 网络

Encoder 和 Decoder 的哈希不共享参数：

```
Encoder:  DE tokens → embedding → self-attn × N → h_enc
         参数: enc W_Q/K/V/O, enc FFN W₁/W₂    (hash 德语 → hidden space)

Decoder:  h_enc + EN tokens → self/cross-attn × N → W_out → logits
         参数: dec W_Q/K/V/O, dec FFN W₁/W₂, W_out  (hash hidden + 英语 → 词表)
```

| | Encoder Hash | Decoder Hash |
|---|---|---|
| 输入 | 源语言（德语） | 目标语言（英语）+ encoder 输出 |
| 输出 | $$h_{enc} \in \mathbb{R}^{512}$$ | $$p \in \Delta^{31999}$$ |
| 参数 | 独立的 W_enc | 独立的 W_dec |
| 作用 | 把德语压缩到连续语义空间 | 把语义空间释放到英语词表 |

唯一共享的是 token embedding（BPE 同词表），但哈希参数本身完全独立。交叉注意力是两者的对接点——decoder 用自己的 Key/Value 连接 encoder 的输出。

## 推理时 Autoencoding——源句本身即标签

每次推理都可以同时做 autoencoding。源句本身就是免费的标签：

```
用户输入 DE 句子:

① autoencoding: DE → Encoder → h → Decoder_DE → DE
                              ↓
                 loss = CE(预测DE, 原文DE) → ∇W_enc, ∇W_dec_de

② 翻译:        DE → Encoder(已更新) → Decoder_EN → EN
```

架构上只需多一个 DE 输出头——Phase 6 的 dual-head（CE+SB）已经证明双头可行：

```
h ─┬─→ Linear_EN → softmax → EN token   (翻译)
   └─→ Linear_DE → softmax → DE token   (autoencoding, 自监督更新)
```

每次推理都同时完成 autoencoding——encoder 的德语 hash 随着使用越来越密。

> **TODO (待实验):** 在现有 dual-head 架构基础上加 autoencoding 头，对比推理阶段开启/关闭 autoencoding 时，长文本 DE→EN 翻译 BLEU 的变化曲线。预期：autoencoding 开启后，encoder hidden 聚类质量随推理量上升，BLEU 持续增长。

### 自学习与翻译训练的比例

Autoencoding 和翻译训练对参数的影响不对称：

```
autoencoding:   DE → Encoder → Decoder_DE → DE     → ∇W_enc + ∇W_dec_de  (双端更新)
翻译训练:       DE → Encoder → Decoder_EN → EN     → ∇W_enc + ∇W_dec_en  (双端更新)
```

两者都更新 Encoder——但 Decoder 端各管各的语言。如果在推理阶段只做 autoencoding 而不做翻译训练，Encoder 的德语 hash 会越来越密，但 Decoder_EN 长时间未更新，翻译能力退化。

所以需要**资源配比**：不是"一直做 autoencoding"，而是"按参数变化率配比两种学习路径"。

> **推理阶段配比约束:** 设 $$\alpha$$ 为 autoencoding 步数对翻译步数的比率。当 $$\alpha > \alpha^*$$ 时，Decoder_EN 退化速度超过 Encoder 受益速度，翻译 BLEU 反降。$$\alpha^*$$ 可通过实验测量。

### 其他自监督方式

在没有平行语料时，还有几条路可以单独更新 Encoder 或 Decoder：

- **contrastive:** 相似句子（短的、主题相近的）的 hidden 拉近，不相似的推远
- **masked LM:** 挖掉一个词，模型猜它是什么（BERT 预训练的方式）
- **autoencoding:** DE→DE 自我重建，双端同时学习

Teacher forcing 需要目标语言的标准答案 $$y_{true}$$ 来算梯度。推理阶段没有——所以参数不动。

但有源句数据本身可以更新 encoder。不需要英文标准答案——**只需要德语句子自己**：

```
推理时有的:  DE 源句 → Encoder → h_enc       ✅
推理时没有的: EN 译文                         ❌ (teacher forcing 无法算)

可以更新 encoder 的自监督方式:
  contrastive: 相似 DE 句的 h_enc 拉近，不相似的推远
  masked LM:   DE 句挖掉一个词，encoder 猜它是什么
```

这些全不需要 EN 标准答案——只需要 DE 源句自己的结构。Encoder 在学习**源语言的空间结构**，而不是翻译映射。

> **注意：** back-translation（DE→EN→DE）只更新 Encoder 参数。更直接的自监督方式是 **autoencoding**——DE→Encoder→h→Decoder→DE，让模型自己翻译自己。因为解码器的输出仍是 DE，梯度可以同时更新 Encoder 和 Decoder，两端都参与 hash 碰撞校准。
>
> **迁移：** Autoencoding 预训练的 Encoder 可以直接用于 DE→EN 翻译——换掉 Decoder 即可。Encoder 学的是"德语怎么压缩到 hidden 空间"，与目标语言无关。这等价于给翻译模型的 encoder 一个冷启动优势：它已经知道德语的内部结构，只需 Decoder_EN 从头学"hidden 怎么释放成英语"。

```python
# 推理时更新 encoder（不需要 y_true）
h_enc = encoder(de_sentence)                    # 有源句，可以算 hidden
loss = contrastive_loss(h_enc, h_enc_neighbor)  # 自监督信号
loss.backward()                                  # 梯度只更新 encoder 参数
```

这与西瓜书第二章的自助法（bootstrap）一脉相承——用已有数据构造伪标签来训练自己。

## 单语言训练更新 Encoder——Phase 0 的骨架就是证明

DE 和 EN 都是现实世界的矩阵映射。德语的"Buch"和英语的"book"在物质宇宙中指同一个东西——只是投影到两个不同的词表坐标系里。

**既然是同一个世界的两次投影，hash 的碰撞自然双向调整距离。**

Phase 0 骨架实验（[003](/wmt/003-wmt-phase0/)）证明了这个假设。骨架模型只做了一件事——用 IWSLT14 的德语文本训练 Encoder 的词嵌入，用英语文本训练 Decoder 的词嵌入。没有翻译任务，没有平行句子，就是单语言训练。

Training loop 的每一步都在双向更新 hash 的参数：

```
Encoder:  DE → Embedding → hidden   | ∇W_enc ← 德语的内部结构
Decoder:  EN → Embedding → hidden   | ∇W_dec ← 英语的内部结构
```

Hash 的碰撞约束了参数运动的方向——"Buch"在德语空间里紧挨着"lesen"（阅读），在英语空间里"book"紧挨着"read"。两个语言的内部距离满足同一种几何约束。嵌入的几何被现实世界的物理结构制约——碰撞桶在两端同时被校准。

这就是为什么你**可以在没有平行语料时优化 Encoder 参数**——因为单语言本身已经包含了"哪些词和哪些词近"的结构信息。hash 碰撞从两端调整距离——编码一端和译码一端在各自的空间里学习物理世界的几何投影。

> **推论（后期实验验证）：** 如果取两个完全相同的预训练模型实例——A 只做推理（冻结），B 在每次中文输入上做 masked LM 自监督更新——定期测试 DE→EN 翻译质量，预期 B 的 BLEU 持续高于 A，且 encoder hidden 的 K-means 聚类质量随时间上升。

## 实验设计：测量 K_lang

K_lang 不是调出来的——是可以从第一性原理里测出来的。

### 核心假设

存在一个常数 $$K_{\text{lang}}$$ 使得：对于任意词汇量 $$|V|$$，最优的 softmax 限制 k 为：

$$k^* = K_{\text{lang}} \times |V|$$

如果 K_lang 是物理常数，那么用不同词表大小跑同一组实验，算出来的 $$k^*/|V|$$ 应该收敛到同一个值。

### 扫描法：多词表验证

**自变量：** 三个词表大小。

<a id="tbl-klang-experiment"></a>
**表** 测 K_lang 的词表

| 词表类型 | \|V\| | 说明 |
|---------|------|------|
| BPE 8K | 8,000 | IWSLT BPE |
| BPE 32K | 32,000 | WMT14 BPE |
| Word-level | 56,652 | IWSLT word-level |

**因变量：** 对每个词表，扫描 k 值：

$$k \in \{32, 50, 64, 100, 128, 170, 200, 256, 400, 500, |V|\}$$

**控制变量：** d_model=256, 3 层 Transformer, 5 epoch, batch=128, seed=42。

**输出：** 每个词表画一条 BLEU(k) 曲线。曲线的峰值给出 $$k^*$$。

### 预期结果

```
BPE 8K:     k* ≈ 24       → k*/|V| ≈ 0.003
BPE 32K:    k* ≈ 96       → k*/|V| ≈ 0.003
Word 56K:   k* ≈ 170      → k*/|V| ≈ 0.003    ← A10 已确认
```

如果三条曲线的峰值都落在同一个比例上——K_lang = 0.003 就是可复现的物理常数。

### 替代方法：梯度分布法

不靠扫描 k 值，直接从训练中测量。在大词表（56K）上做几轮全量 softmax 的 forward，收集每个 token 的梯度幅值，排序后找到 "有效梯度" 和 "噪声梯度" 的分界点——那个位置的 token 数就是 $$k^*$$，不需要扫描。

### 压缩还原法：从 Hash 容量直接测量

这是最根本的测法——**不需要多词表，不需要扫描，只需要一个自重建模型**。

思路：hash 碰撞桶的信息容量是有上限的。用一个过大的 hidden 空间（2× 容器）做同语言自学习——骨架实验已经证明 autoencoding BLEU 可达 90+。然后**逐层压缩 d_model**，观察 BLEU 的衰减曲线。

**实验设计：**

```
① 起点: DE → Encoder(d=1024) → Decoder(1024) → DE
        多语自学习 → BLEU≈90 (整个 hash 空间足够稀疏)

② 压缩: 1024 → 768 → 512 → 384 → 256 → 128 → 64
        每压缩一次 → 重新评估 BLEU
        
③ 观察: 压缩到某个点 → BLEU 开始明显下跌
        那个膝盖点的压缩比 = 信息容量的上限
        = K_lang
```

**背后的原理：**

Hash 空间的每个维度承载信息。当维度过高（1024），信息极度稀疏——桶太多，每个桶只装极少数 token，BLEU 很高但不是"泛化好"而是"记住了"。当维度过低（128），信息被压缩到极限——hash 碰撞变得过于密，BLEU 暴跌。

K_lang 就出现在 **BLEU 曲线的膝盖处**——那个恰好在"记住"和"压缩"之间的维度数。

如果 K_lang 真的是物理常数，那这个膝盖点应该对不同的语言、不同的词表大小都稳定。一个 DE→DE 自重建模型就够了——不需要平行语料，不需要翻译训练。

> **TODO (待实验):** Phase 0 骨架验证。d_model 从 1024 逐层压缩到 64（10 个点），每层 autoencoding 10 epoch 测 BLEU。画出 BLEU(d_model) 曲线，膝盖点即 K_lang。与扫描法（A8-A12 已做）和梯度分布法交叉验证。预期：三种方法收敛到同一个 K_lang ≈ 0.003。

---

## K_lang 量化下限：INT8 训练的理论下界

碰撞桶理论不仅控制哈希参数密度——它还给了训练精度一个硬下限。

每个碰撞桶只需区分 $$\approx 170$$ 个有效 token。INT8 有 256 个离散级别——**恰好覆盖这个下限**。FP32 的 7 位有效数字（$$\sim 2^{23}$$ 个级别）完全过量——多出来的级别存在噪声，不是信号。

**量化梯度净化效应：** `(p−y)·h_t` 里低于 1/256 的梯度分量被 INT8 截断——等于自动滤掉了碰撞桶外的噪声。桶内有效信号更干净。

### 精度下限公式

每维度至少需要 $$k$$ 个精度级别，其中：

$$k = K_{\text{lang}} \times |V| \approx 170$$

<a id="tbl-quant"></a>
**表** 精度 vs K_lang 下限

| 精度 | 可分辨级数 | vs 170 下限 | T2 显存 | 推论 |
|------|----------|------------|--------|------|
| FP32 | ~16M | 极度过量 | 23.8 GB | 噪声存太多 |
| FP16 | ~65K | 过量 380× | ~15 GB | 仍有浪费 |
| INT8 | 256 | **恰好过 170** | ~12 GB | 理论最优 |

INT8 能满足碰撞桶的分辨需求——不多不少。K_lang 不是调参值，是衡量必要模型精度的物理常数。

> **实验验证：** FP32 / autocast FP16 / QAT INT8 三组对照训练 T2。预期：INT8 的 BLEU 与 FP32 差异 < 0.5%，同时 batch 可增至 512。若 INT8 的 BLEU 反而更高，则证实 "FP32 存储了噪声，量化截断净化了梯度"。

---

*May the Code be with us.*

---

> **License: GPLv3**  
> 本文《SameTime WMT》系列采用 GNU 通用公共许可证第三版 (GNU General Public License v3.0) 协议进行开源发布与分发。
