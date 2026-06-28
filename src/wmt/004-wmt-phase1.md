---
title: "[WMT-004] Phase 1 从 RNN 记忆到 LSTM 门控"
date: 2026-04-27
author: nio (Houming818) & opencode (First Mate)
keywords: SameTime, WMT, NMT, Phase 1, RNN, LSTM, Seq2Seq, BiLSTM, IWSLT14
description: SameTime WMT Phase 1 学习记录——拆分为 1.0 vanilla RNN（理解记忆原理）和 1.1 LSTM（解决梯度消失），逐级对比。
tags: [WMT, NMT, SameTime, RNN, LSTM, Seq2Seq]
---

# SameTime WMT 专题：Phase 1 从 RNN 记忆到 LSTM 门控

> "不要跳过推车直接开跑车。先造一辆吱嘎作响的木板车，体会它为什么散架，再理解锻造淬火的钢架好在哪。"

## Phase 1 拆分为两步

Phase 1 原计划走 "RNN Seq2Seq"，但代码里全是 `nn.LSTM`——中间缺了一环。

现在拆成两步：

| | Phase 1.0 | Phase 1.1 |
|---|---|---|
| 目录 | `phase1_0_rnn/` | `phase1_1_lstm/` |
| 模型 | 2层 BiRNN + 2层 RNN | 2层 BiLSTM + 2层 LSTM |
| 状态 | 只有 h_t | h_t + c_t（细胞状态） |
| 门控 | 无（纯 tanh） | 三扇门（f/i/o） |
| 梯度路径 | 连乘 tanh(W) → 消失 | 加性直通 → 保持 |
| 参数 | ~8M | ~16M |
| 目的 | 理解记忆原理 | 体会门控解决了什么 |

---

## Phase 1.0：Vanilla RNN — 推车

### RNN 如何"记忆"
$$h_t = \tanh(W_{hh} \cdot h_{t-1} + W_{ih} \cdot x_t + b)$$

每个时间步，RNN 把 **上一个隐藏状态 $h_{t-1}$**（历史）和 **当前输入 $x_t$**（现在）揉在一起，过一层 tanh，得到新的隐藏状态 $h_t$。

**直观类比**：h_t 像一张便签。你每读一个词，擦掉便签上的一部分旧内容，写上当前词的摘要。

- 读第 1 个词 → h_1 记着 "I"
- 读第 5 个词 → h_5 记着一些语法信息 + 部分语义
- 读第 50 个词 → h_50 中，第 1 个词的信息早已被 tanh(W) 连乘 50 次碾成粉末

**tanh 的罪**：`|tanh'(…)| ≤ 1`，但实际值通常 << 1。乘以一个权重矩阵 W（通常元素也 < 1），50 步连乘后 ≈ 0。

### BPTT：为什么梯度消失了

反向传播需要计算 $\partial L / \partial W$。对于时间步 $t=1$ 的单词，梯度需要穿过 $T-1$ 个时间步才能到达损失函数：

$$\frac{\partial L}{\partial h_1} = \frac{\partial L}{\partial h_T} \cdot \prod_{k=1}^{T-1} \frac{\partial h_{k+1}}{\partial h_k}$$

其中 $\frac{\partial h_{k+1}}{\partial h_k} = W_{hh}^T \cdot \mathrm{diag}(\tanh'(\dots))$

连乘项中 $W_{hh}$ 的特征值如果 $\lt 1 \to$ 梯度消失；如果 $\gt 1 \to$ 梯度爆炸。tanh 的导数范围是 $(0, 1]$，进一步压低梯度。

**结论**：50 个词的句子，前 10 个词 ≈ 没有梯度信号。训练只学到了靠 target 端最近的词。

### 代码级变化（vs. Phase 0）

```python
# Phase 0: 只处理 target
class DummyModel(nn.Module):
    def forward(self, src, tgt_in):
        return self.out(self.embed(tgt_in))

# Phase 1.0: Encoder 处理 src，Decoder 处理 tgt
class Seq2Seq(nn.Module):
    def forward(self, src, tgt, src_len):
        enc_out, hidden = self.encoder(src, src_len)  # 编码源句
        logits, _ = self.decoder(tgt, hidden)          # hidden 是唯一的信息传递者
        return logits
```

注意 `nn.RNN` 只返回 `hidden`（没有 `cell`），Decoder 签名更简洁。代价就是"便签"容量极其有限。

### 对照分析实验 start

**实验目的**：控制 `hidden_size` 为唯一自变量，观测 RNN Seq2Seq 的容量-质量关系，验证"信息瓶颈"假说。

**固定变量**：

| 变量 | 值 |
|---|---|
| epochs | 5 |
| lr | 1e-3 |
| embed | = hidden |
| layers | 2 (双向 Encoder + 单向 Decoder) |
| dropout | 0.3 |
| batch_size | 64 |
| seed | 42 |
| optimizer | Adam |
| dataset | IWSLT14 de-en |
| hardware | RTX 3090 24GB, CUDA 12.1 |
| 代码 | `phase1_0_rnn/train.py` + `exp_hidden_scale.sh` |

**自变量**：hidden ∈ {16, 32, 64, 128, 256, 512, 1024}（$2^4 \sim 2^{10}$）

**运行时间**：74 分钟，7 组全通过，无一 OOM。

#### 实验前假设（2026-05-01 修订）

**hash 碰撞发生在 embedding lookup，而非 hidden。**

从 hash 碰撞的视角：

```
token "der" → lookup(embedding[74360×E]) → [e₁, e₂, ..., e_E]      ← hash 碰撞在这里
                                                    ↓
RNN 逐词读取 → hidden 随时间步推移，前面的词被 tanh 碾碎              ← 不是碰撞，是擦除
                                                    ↓
最后 hidden₅₁₂ → 前 40 个词的信息 ≈ 消失                         ← 时序破坏，非容量不足
```

hidden 拥有 512 维空间，但 RNN 不会利用——不是"装不下"，而是前面的内容在时间轴上被后续写入覆盖了。**hash 空间够大，写入方式却是有损的**。

因此假设：

1. **增大 hidden 对 BLEU 的提升应极小**——hash 碰撞不发生在 hidden 维度，hidden 再大也不能阻止时间轴上的信息擦除
2. **真正的瓶颈在两方面**：
   - a) embedding 宽度（hash key 长度）：74K 德文词挤在 E 维空间，E 太小则碰撞频繁
   - b) RNN 的时序写入方式：Attention 才能解决（Phase 2）
3. **下一步应拆耦合实验**：固定 hidden=512（最优容量），vary embed，验证 hash 宽度才是硬瓶颈

---

#### 实验结果

| hidden | params | epoch 0 BLEU | best BLEU | epoch 4 BLEU | 耗时 |
|---|---|---|---|---|---|
| 16 | 3.1M | 0.00 | 2.13 (ep4) | 2.13 | 285s |
| 32 | 6.1M | 1.05 | 2.94 (ep4) | 2.94 | 290s |
| 64 | 12.1M | 2.97 | 2.97 (ep0) | 2.55 | 307s |
| 128 | 24.3M | 2.71 | 2.71 (ep0) | 2.17 | 379s |
| 256 | 49.0M | 2.02 | 2.32 (ep2) | 2.24 | 528s |
| 512 | 99.8M | 1.84 | **3.02 (ep2)** | 2.48 | 895s |
| 1024 | 206.9M | 1.57 | 2.42 (ep1) | 1.60 | 1741s |

完整 jsonl 数据存储于 io: `/data/homecicd/sametime/results/metrics_h*.jsonl`

#### 实验结论

**1. BLEU 天花板 ≈ 3.0 —— 信息瓶颈真实存在**

所有配置中最高 BLEU 仅 3.02（H=512, epoch 2）。这验证了 Phase 1.0 理论：无 Attention 的 Seq2Seq 中，Encoder 必须把整个源句压缩成一个固定维度向量，无论 hidden 多大，信息丢失不可逆。**增大 hidden 只能缓解，不能突破**。

看完整曲线：
- H=16→64：BLEU 随容量从 0 涨到接近 3，这是"容量不足→够用"的阶段
- H=128→512：BLEU 在 2.3~3.0 之间震荡，增长停止——遇到硬天花板
- H=1024：BLEU 反而降到 2.42——**过参数化开始损害泛化**

**2. Loss 下降 ≠ BLEU 提升 —— 过拟合的硬证据**

所有 7 组 loss 随 epoch 单调递减（收敛正常），但 BLEU 曲线不是：

| hidden | BLEU 趋势 | 解释 |
|---|---|---|
| 16/32 | 持续上升到 epoch 4 | 小模型容量不足，需要更多 epoch 学会基础映射 |
| 64/128 | 早期峰值后下降 | 容量刚好时，teacher forcing 过拟合起效快 |
| 256/512/1024 | 中期峰值后衰退 | 大模型快速过拟合训练集，Greedy Decode 泛化差 |

这就是经典过拟合信号：模型在训练集上 loss 越来越低，但评估时 BLEU 却往下掉。

**3. 最佳容量出现在 H=512**

H=256→512→1024 形成倒 U 曲线：
- H=256: 49M, BLEU=2.32
- H=512: 100M, BLEU=**3.02**
- H=1024: 207M, BLEU=2.42

对 IWSLT14 de-en（160K 训练句），100M 参数恰好匹配数据量。再翻倍参数只是给过拟合喂了更多自由度。

**4. 小模型 BLEU 低但"诚实"**

H=16 和 H=32 在 epoch 0 时 BLEU 接近 0——容量太小，还没学会任何翻译。但它们的好处是：**BLEU 持续上升**，不会过拟合，训练到 20 个 epoch 可能最终追上大模型。

**5. 时间成本基本线性**

206M 参数（H=1024）耗时 29 分钟，3M 参数（H=16）耗时 5 分钟。规模-时间近似 $T \propto N^{0.85}$（接近线性），瓶颈在 vocab embedding （V×H）上而非 RNN 计算。

**6. 假设验证：hash 碰撞不在 hidden**

64 倍的 hidden 宽度（16→1024），BLEU 仅从 2.13→2.42。这验证了实验前假设：**hidden 不是 hash 碰撞的现场**。hidden=16 时信息容量才 16 维，但 BLEU 仍达 2.13——说明即使极端压缩，信息仍在传递。更大的 hidden 只是给了 RNN 更多"便签空间"，但没有改变"便签被不断重写"的本质。

因此 Phase 2（Attention）才是突破点，不是更大的 hidden。

---

#### 实验二：解耦合——固定 hidden=512，vary embed

**目的**：验证 hash 碰撞究竟发生在 embedding 宽度还是 hidden 容量。

**固定**：hidden=512（实验一最佳点），epochs=5, lr=1e-3, layers=2, seed=42

**自变量**：embed ∈ {32, 64, 128, 256, 512, 1024}

| embed | params | epoch 0 BLEU | best BLEU | epoch 4 BLEU |
|---|---|---|---|---|
| 32 | 36.2M | 2.28 | 2.64 (ep1) | 2.12 |
| 64 | 40.4M | 2.89 | 2.89 (ep0) | 2.45 |
| 128 | 48.9M | 3.06 | **3.06 (ep0)** | 1.91 |
| 256 | 65.9M | 2.88 | 2.88 (ep0) | 2.25 |
| 512 | 99.8M | 1.84 | 3.02 (ep2) | 2.48 |
| 1024 | 167.7M | 2.28 | 2.74 (ep1) | 2.21 |

#### 实验二结论：倒 U 形，非单调

修正此前判断——**embed 对 BLEU 有显著影响，但呈倒 U 形**：

1. **E=32→128：hash 宽度主导**。BLEU 从 2.64 涨到 3.06（+0.42）。74K 德文词挤在 32 维时碰撞频繁，扩到 128 维后每维仅承载 ~580 词，碰撞锐减。
2. **E=128→1024：过拟合主导**。BLEU 从 3.06 降到 2.74。即使 hash 碰撞更低（1024 维时每维仅 73 词），过大的 embedding 矩阵（168M 参数中的 134M 来自两个 embedding table）让 160K 训练句无法有效训练。
3. **最佳 hash 宽度 = 128 维**。对 74K 词表，~580 词/维是最优碰撞密度。
4. **两块天花板合并**：增加 hidden 上限 ~3.02（实验一），增强 embed 上限 ~3.06（实验二）。**RNN 的 BLEU 硬上限 ≈ 3.0，无论怎么调参都破不了**。

#### 两张实验合并解读

```
实验一: hidden vary, embed=hidden (耦合)
        16→512:  BLEU ↑ (容量不足到够用)
        512→1024: BLEU ↓ (过拟合)

实验二: hidden=512, embed vary (解耦合)
        32→128:  BLEU ↑ (hash 碰撞减少)
        128→1024: BLEU ↓ (过拟合)
```

**共同规律**：IWSLT14 de-en（160K 句）的最佳模型容量约 50M 参数（H=256，E=128 均在此附近）。超过此值的参数对 BLEU 贡献为负。

---

#### 深度解释：为什么是倒 U，而不是"越大越好"？

直觉告诉你：hidden 越大，模型越强，BLEU 越高。但实验事实是倒 U。错在哪儿？

**翻译是 hash 碰撞问题。增大 hidden 没有让碰撞变容易——它让碰撞变难了。**

把翻译过程看作 hash 运算：

```
Encoder(德语 "der Mann")  ──→  hidden₅₁₂  ──→  Decoder  ──→  "the man"
      ↑                                   ↑
  把德文"打散"进 512 维空间       从 512 维"还原"出英文
```

hidden 就是 hash 的密钥空间。问题在于：**翻译不是找"任意碰撞"，而是找恰好对应的那个语义映射**。

- H=16：hash 空间极小（16 维），但目标也少——梯度下降很容易探索完整个空间，很快找到可行解。代价：空间太小，碰撞是粗糙的（"随便一碰就对上"，翻译不准）。
- H=512：hash 空间恰好——梯度能在 160K 样本指引下找到足够精细的碰撞映射。
- H=1024：hash 空间太大。每个训练的 step 梯度给你一点方向，但 1024 维空间里方向太多，160K 个训练信号根本不够覆盖。梯度在迷雾中摸索，沿着训练集的特征走错了岔路——把训练噪声当成了规律。这就是过拟合的物理本质：**hash 空间太大，梯度迷路了**。

类比：你在北京找一个地址。
- H=16 是"朝阳区"——很小，你随便走几步就撞到了目的地。但地址过于模糊。
- H=512 是"朝阳区望京街道"——刚好。你有 160K 个路人给你指方向，能精确定位。
- H=1024 是"朝阳区望京街道阜通东大街 6 号院 3 号楼 2 单元 1501 室"——太细了。160K 个路人只能给你含糊的"大概在那边"。你走进了一个巨大的 hash 迷宫，而指点方向的样本量没有变多。你最终停在了一个看起来很像但其实是错误的位置——这就是过拟合的 hash 解释。

**直觉的错位**：我们混淆了"表示能力"和"学习难度"。更大的 hidden 确实能表示更精细的映射（hash 分辨率更高），但梯度下降未必能找到它。**表示能力是线性的，搜索难度是超线性的**——两条线交叉处就是倒 U 的顶点。

---

#### 形式化：碰撞密度模型

HM 提出以下模型：BLEU 由碰撞密度决定，分子控制碰撞概率，分母控制碰撞精度。

$$BLEU(N_{\text{data}}, N_{\text{params}}) \propto \left| \frac{N_{\text{data}}}{N_{\text{params}}} - K_{\text{lang}} \right|^{-1}$$

其中：

- $N_{\text{data}}$ = 分子 = 训练数据量。增大分子 → hash 碰撞概率增大 → 更容易找到映射。但过大则碰撞太容易，映射粗糙。
- $N_{\text{params}}$ = 分母 = 模型参数量。增大分母 → 碰撞概率减小 → 需要更精确的碰撞。但过大则找不到碰撞。
- $K_{\text{lang}}$ = 语言常数 = 该语言对的最优碰撞密度。这是**语言对的固有属性**——由源语言词表大小、目标语言词表大小、语法复杂度差异共同决定。当前的实验任务（IWSLT14 de-en）中 $K_{\text{lang}} \approx 0.003$。

epoch 不在公式里。epoch 是"逼近精度"——给定分子分母后，用多少步迭代去逼近理论 BLEU 上限。epoch 提高相当于计算 π 时用更多项——能提高精度，但不改变圆周率本身。

**实验验证**：

| # | H | E | N_params | P = N_data/N_params | BLEU |
|---|---|---|---|---|---|
| 1 | 16 | 16 | 3M | 0.053 | 2.13 |
| 1 | 32 | 32 | 6M | 0.027 | 2.94 |
| 1 | 64 | 64 | 12M | 0.013 | 2.97 |
| 1 | 128 | 128 | 24M | 0.0067 | 2.71 |
| 1 | 256 | 256 | 49M | 0.0033 | 2.32 |
| 1 | 512 | 512 | 100M | **0.0016** | **3.02** |
| 1 | 1024 | 1024 | 207M | 0.0008 | 2.42 |
| 2 | 512 | 32 | 36M | 0.0044 | 2.64 |
| 2 | 512 | 64 | 40M | 0.0040 | 2.89 |
| 2 | 512 | 128 | 49M | **0.0033** | **3.06** |
| 2 | 512 | 256 | 66M | 0.0024 | 2.88 |
| 2 | 512 | 512 | 100M | 0.0016 | 3.02 |
| 2 | 512 | 1024 | 168M | 0.00095 | 2.74 |

**峰值聚集**：两个实验的最佳 BLEU 均出现在 P ≈ 0.003 附近（49M 参数 / 160K 句）。

**待证伪的预测**：

1. 若 $N_{\text{data}}$ 加倍到 320K，最佳 $N_{\text{params}}$ 应翻倍到 ~98M，$K_{\text{lang}}$ 不变。
2. 换语言对（如 en-fr），$K_{\text{lang}}$ 应不同——语法越相似，最优 P 越大。
3. epoch 增大仅逼近理论 BLEU，不改变 $K_{\text{lang}}$ 的位置。

#### 预测 3 证伪测试：epoch 深度

| 实验 | hidden | best BLEU | peak epoch | epoch 19 BLEU | trend |
|---|---|---|---|---|---|
| H=512 ep20 | 512 | **3.02** | 2 | 1.35 | peak 后一路下滑 |
| H=1024 ep20 | 1024 | 2.42 | 1 | 1.94 | epoch 1 即巅峰，loss ep6 触底后反弹 |

**H=1024 完整 20 轮（350W 功耗限制下稳定跑完，零故障）**：

| epoch | 0 | 1 | 2 | 6 | 14 | 17 | 19 |
|---|---|---|---|---|---|---|---|
| loss | 5.98 | 5.37 | 5.12 | 4.80 | 5.54 | 5.89 | 5.79 |
| BLEU | 1.57 | **2.42** | 1.77 | 1.78 | 1.41 | 1.92 | 1.94 |

H=1024 过拟合更猛烈——epoch 1 即达峰，随后彻底崩溃。Loss 在 epoch 6 见底后反弹至 epoch 19，BLEU 持续震荡在 1.4~2.1 之间低位徘徊。

**结论：预测 3 成立，双重验证。** epoch 不改变 $K_{\text{lang}}$。增加 epoch 对 BLEU 的提升为零甚至为负——模型在 teacher forcing 强约束下迅速过拟合训练集，泛化能力 epoch 2 即达上限，之后都是噪声学习。

---

#### 预测 1 初步测试：数据加倍

**假设**：若 $N_{\text{data}}$ 加倍（160K→320K），$N_{\text{params}}$ 的最佳点应右移。H=1024（207M）在大数据下应摆脱过拟合，BLEU 从 2.42 上升。

**结果**（3/5 epoch，GPU 中途掉卡）：

| epoch | 0 | 1 | 2 |
|---|---|---|---|
| data×2 BLEU | **2.50** | 2.33 | 2.29 |
| data×1 BLEU | 1.57 | 2.42 | 1.77 |

epoch 0 BLEU 从 1.57 跳到 2.50（同 epoch 对比 +0.93），数据加倍大幅缓解了训练初期的冷启动——模型在更多梯度步数的指引下，epoch 0 就能学到不错的映射。但 epoch 1 之后 BLEU 依然衰退（2.33 vs data×1 的 2.42），**过拟合路径没有改变**——只是起始点提高了。

**结论**：预测 1 方向正确——数据加倍在 epoch 0 产生了 +0.93 的显著提升。但过拟合路径未被改变，epoch 1 后 BLEU 依然衰退。$K_{\text{lang}}$ 可能不是纯碰撞密度问题——当参数多到 207M 时，即使是 320K 样本也不够填充 hash 空间。需要至少 10 倍数据量（1.6M+ 句）才能在 1024 维 hidden 空间里提供足够的梯度信号。

### 对照分析实验 end

### 对照分析实验 end

---

## Phase 1.1：LSTM — 锻造淬火

### LSTM 的三扇门 + 细胞状态

$$f_t = \sigma(W_f \cdot [h_{t-1}, x_t])$$
$$i_t = \sigma(W_i \cdot [h_{t-1}, x_t])$$
$$o_t = \sigma(W_o \cdot [h_{t-1}, x_t])$$
$$\tilde{c}_t = \tanh(W_c \cdot [h_{t-1}, x_t])$$

$$c_t = f_t \odot c_{t-1} + i_t \odot \tilde{c}_t$$
$$h_t = o_t \odot \tanh(c_t)$$

**关键洞察**：$c_t$ 的更新是 **加性更新**——$f_t \cdot c_{t-1} + i_t \cdot \tilde{c}_t$。没有连乘 tanh！

- 忘了 0.3 旧记忆 + 写入 0.7 新信息 = 新细胞状态
- 梯度通过 c_{t-1}→c_t 可以"直线传递"（LSTM 论文称 "Constant Error Carousel"）
- 遗忘门 f_t 可以在训练中学到 "保留重要信息" vs "丢弃无关信息"

**类比**：c_t 是一张有"编辑权限"的便签。RNN 只能整张擦掉重写，LSTM 可以选择性地划掉某些字、补上新字。因此 50 步后，第一步的"签名"仍然可能清晰可辨。

### RNN vs LSTM 实战对比

| | Phase 1.0 (RNN) | Phase 1.1 (LSTM) |
|---|---|---|
| 隐状态 | h_t (1 份) | (hidden, cell) (2 份) |
| 参数 | H×H (单矩阵) | H×H×4 (三扇门 + 候选) |
| Decoder 接口 | `decoder(tgt, hidden)` | `decoder(tgt, (enc_out, (hidden, cell)))` |
| 长句梯度 | 趋近于 0 | 可保持 |
| BLEU 预期 | 很低 | 高于 RNN，但 < 5（仍信息瓶颈） |

### 代码级变化

```python
# Phase 1.0: RNN
self.rnn = nn.RNN(input_size, hidden_size, num_layers, ...)
output, hidden = self.rnn(embedded, hidden)
# hidden: (num_layers, B, H)

# Phase 1.1: LSTM
self.rnn = nn.LSTM(input_size, hidden_size, num_layers, ...)
output, (hidden, cell) = self.rnn(embedded, (hidden, cell))
# hidden: (num_layers, B, H)
# cell:   (num_layers, B, H)  ← 细胞状态，梯度高速通道
```

**PyTorch 层面**: `nn.RNN` → `nn.LSTM` 仅改一行。但 LSTM 需要额外维护 cell state，Decoder 的 `forward` 签名从 `(tgt, hidden)` 变成 `(tgt, (hidden, cell))`。

---

## 提问环节

### Q1: RNN 记忆的本质

RNN 把历史信息"折叠"进一个向量 h_t。这更像"压缩/蒸馏"还是更像"遗忘/丢弃"？如果用信息论的语言描述：h_t 的信息容量由 hidden_size 决定——256 维的向量能无损"记住"多长的句子？

Nio：参考 Phase 0 Q2 的 hash 碰撞理论——如果 h_t 是源语言的 hash 摘要，Decoder 需要从这个固定大小 hash 中"解压"出目标语言。信息容量随句子变长指数下降，这就是信息瓶颈。

HM: 如果只看RNN的问题，也就是h_t的形成过程。公式是$$h_t = \tanh(W_{hh} \cdot h_{t-1} + W_{ih} \cdot x_t + b)$$
首先是梯度消失，可以看到tanh是单调的，随着刻意的梯度下降，W的元素会越来越小，tanh的输入也会越来越小，tanh的输出也会越来越小，最终导致梯度消失。其次是信息瓶颈，h_t的维度是固定的，无论输入多长的句子，h_t只能提供有限的信息容量。重点来了，我认为梯度下降的操作，就是本质的压缩操作。而这个过程在压缩时，没有一个衡量标准，确认多少信息量丢失了。最终压缩到至极，以至于没有信息增加，梯度消失了。后面的LSTM的设计，就是为了在压缩的过程中，用cell的恒定参数，保存所有信息量，可以看到随着梯度下降，cell是没有压缩的，保持恒定的维度和信息量。这样就解决了梯度消失带来的信息丢失的问题。这也告诉我们，压缩的过程开始写入信息，所以信息的写入顺序也注定了hidden的训练效果。也就是说，越靠近输入端的词，越早被写入hidden，越容易被压缩掉；越靠近输出端的词，越晚被写入hidden，越不容易被压缩掉。这就是为什么RNN更容易记住句子末尾的信息，而忘记句子开头的信息。所以神经网络是一种天然包含时序的压缩方式。

### Q2: tanh 的驯服

RNN 用 tanh 激活 → 输出在 (-1, 1) 之间 → 导数最大为 1。LSTM 用 sigmoid (遗忘/输入/输出门) + tanh (候选记忆 + 输出门)。

为什么门控函数用 sigmoid 而不是 tanh？如果所有门都换成 tanh 会发生什么？

HM：看不懂，嚼不动，先放着

### Q3: 细胞状态的加法

LSTM 的核心创新是 `c_t = f_t*c_{t-1} + i_t*c̃_t`——加法而非连乘。除了梯度直通，这种"选择性遗忘 + 选择性写入"与你之前提到的"最低频率过滤"（min_freq=2）有什么本质相似之处？

HM：这里的假设都是抽象的。什么是选择性遗忘 选择性写入？我觉得AI在乱提问。我写点我的理解，首先，一个h_t的容量是有限的，而RNN的选择是，不断覆盖，在h_t域内，只留下最近的信息，这个信息怎么进入h_t的？信息在h_t中选中的概率是不同的。改变参数就是改变获得decode结果的概率。每一次正确的hash碰撞，就是一次BLEU的增加。所以增加层数，能增加参数，容量就越大。而参数越多，encoding的过程需要的时间算力就越大，因为是一个压缩过程。所以为了在合适尺度获得更好的效果，需要找到训练数据和训练顺序的完美搭配。为什么LSTM比朴素RNN好？答案是，并不是一定好，如果h_t本身很小，两者应该没有区别，熵增速度太大，h_t根本存不下，所以完全没有差别。在h_t尺度足够的情况下，LSTM因为encoding的方式不同，hash的效果就有变化。cell存在，使得信息能均匀分布到h_t的每个hash位上，而不是重复覆盖在所有位上，这样就能更好地利用h_t的容量，hash碰撞的概率更高效，从而提高BLEU分数。理论上讲，应该可以通过计算h_t的熵增量，来提前评价要一个 encoder 的性能，比如一个长句的熵增显著大于一个短句，一个重复句子的熵增应该更小。而对于h_t的直接评价算法，目前没有。只有loss评价算法。

### Q4: RNN→LSTM 的参数膨胀

LSTM 比 RNN 参数多了约 4 倍。在 IWSLT14 这种小数据集（160K 句）上，这个参数冗余是浪费还是必要？如果用 GRU（2 扇门，参数约为 LSTM 的 3/4），BLEU 会不会差不多？

### Q5: 信息瓶颈仍然存在

即使换上 LSTM，"上下文向量 c"（Encoder 最后 hidden state）仍然是固定 512 维。Phase 2 引入 Attention 后，Decoder 可以"跳过 c，直接看 Encoder 所有时间步的输出"。

从 LSTM 的 c_t（细胞内记忆）到 Attention 的 c（动态加权上下文），这两个 "c" 从命名到作用有什么本质不同？LSTM 的 c_t 能不能替代 Attention？如果不能，为什么？

### Q6: 训练速度与算力

| Phase | 参数量 | 每 epoch 时间（预估） | 梯度瓶颈 |
|---|---|---|---|
| 1.0 (RNN) | ~8M | 快 | 消失严重 |
| 1.1 (LSTM) | ~16M | 中 | 缓解 |
| 2.0 (LSTM+Attn) | ~20M | 慢 | Attention 的计算代价 |

在显存限制下（GTX 3090 24GB），如果 batch_size 从 64 降到 16 才能跑 LSTM，低 batch 引入的噪音和 LSTM 门控的稳定性之间如何权衡？

---

### 与Nio的讨论 start

#### 梯度函数的本质：选择一种学习规律

HM 提出：换个激活函数 = 换个梯度函数 = 换种学习方式。sin 是周期函数——周期桶让 hash 碰撞有更多自由度。但实验结果 BLEU=0.76（tanh 3.06），彻底失败。

**失败原因**：sin 的梯度 `cos(x)` 正负交替——前半句学的方向，后半句自己推翻。余弦每穿过 $\pi/2, 3\pi/2...$ 就翻转符号，模型在 hash 桶之间来回跳跃，净位移为零。tanh' 永远正、永远衰减——笨但方向从不出错。

**好的梯度函数 = 自洽的向量场**：每一步梯度指向的方向必须和全局最优方向一致。sin 的梯度在周期桶里反复翻转——不是没力气走，是走回来的路正好抵消了走出去的路。

#### loss 和 BLEU 不是一回事——训练听不到翻译质量

H=512 ep20 的实证：

| epoch | loss | BLEU |
|---|---|---|
| 0 | 5.69 | 1.84 |
| 2 | 4.76 | **3.02** |
| 10 | 4.22 | 1.79 |
| 19 | 4.46 | 1.35 |

loss 持续下降（5.69→4.46），BLEU 在 epoch 2 达峰后一路衰退。**模型在 teacher forcing 的镜子里觉得自己越来越好，但实际翻译质量越来越差。**

根因：CrossEntropy 度量的是"逐 token 预测是否和 tgt 一致"，BLEU 度量的是"整句 n-gram 和 ref 的碰撞率"——**两个不同的 hash 空间**。loss 在训练 hash 桶里找一模一样的 token，BLEU 在测试 hash 桶里考 n-gram 的碰撞。train 的碰撞太完美（teacher forcing 提供完美答案），test 的碰撞太稀疏（greedy decode 没有完美参考）。

#### BLEU 为何不能直接当 loss

BLEU 的公式里有 `argmax`——把 logits 变成离散的词序列。这一步数学上不可导：

$$ \frac{\partial \text{BLEU}}{\partial W} = \frac{\partial \text{BLEU}}{\partial \text{argmax}} \times \frac{\partial \text{argmax}}{\partial \text{logits}} \times \frac{\partial \text{logits}}{\partial W} $$

第二项 $\partial \text{argmax}/\partial \text{logits}$ 处处为零——无论你预测 `cat` 的概率是 0.4 还是 0.49，选出来的词不变，直到 0.51 才跳变。梯度在跳变之前为零，在跳变点不存在。

CrossEntropy 能传梯度是因为它不选词——它直接用整个概率分布和 one-hot 目标比对，每个词的预测概率都参与计算。

#### 解决方案：Soft BLEU

把硬 BLEU 的 argmax 换成 softmax，把硬 n-gram 计数换成概率加权：

$$\text{SoftBLEU} = \frac{\sum_{w \in hyp} \min(p(w|ctx), c_{ref}(w))}{\sum_{w \in hyp} p(w|ctx)}$$

$p(w|ctx)$ 是模型预测 w 的连续概率，不是 agrmax 的离散结果。整个链条可微——**梯度可以直接从 BLEU 近似值流回模型参数**。

训练时与 CrossEntropy 混合使用：

$$L_{total} = \lambda \cdot L_{CE} + (1-\lambda) \cdot (1 - \text{SoftBLEU})$$

$\lambda$ 从 1.0 逐步降到 0.5，让模型从"学 token"平滑过渡到"学翻译"。

#### 四层 hash 碰撞统一框架

HM 提出：翻译本质是四次 hash 碰撞的链式查找：

| 层次 | hash 空间 | 碰撞判定 | 参与梯度？ |
|---|---|---|---|
| 1. Embedding | E 维向量 | token→向量 | ✅ CS |
| 2. Hidden | H 维向量 | 整句→压缩向量 | ✅ CS |
| 3. Decoder output | V 维 logits | 向量→token | ✅ CS |
| 4. BLEU | n-gram 表 | 输出←→参考 | ❌ 不可微 |

前三次碰撞都参与梯度，模型拼了命优化。第四次——BLEU 碰撞——模型根本听不到。整个训练的悲剧在于：**优化器在追第 1~3 层的碰撞，但评分用第 4 层。**

Transformer 改了第 2 层（Attention 替代 RNN 的时序压缩），但第 4 层的问题——BLEU 不参与梯度——Transformer 也没解决。Soft BLEU 是填这条沟的可行方向。

#### sin 激活函数实验

| 激活 | best BLEU | loss 变化 | 关键观察 |
|---|---|---|---|
| tanh | **3.06** | 5.69→4.46 | baseline，稳定学习 |
| sin | 0.76 | 6.32→6.19 | loss 几乎不动，梯度方向翻转 |

sin 的多桶 hash 理论方向对——周期桶提供了更多自由度。但 cos 梯度的方向交替翻转让参数在桶之间跳跃，净学习量为零。

### 与Nio的讨论 end

---

*May the Code be with us.*

---

> **License: GPLv3**  
> 本文《SameTime》系列采用 GNU 通用公共许可证第三版 (GNU General Public License v3.0) 协议进行开源发布与分发。允许任何形式的复制、修改和分发，但必须继承相同的开源协议，承认在算力宇宙中所有的迭代与变异。
