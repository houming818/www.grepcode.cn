---
title: "[WMT-008] Phase 6 Transformer——从 3 到 11 的跃迁"
date: 2026-05-05
weight: 1
author: nio (Houming818) & opencode (First Mate)
keywords: SameTime, WMT, Transformer, BPE, Academic Baseline, IWSLT14
description: Attention 天花板 3.77，Transformer 词级 11.49，BPE 小模型 10.66。下一步：BPE d512 大模型追学术基线 20-25。
tags: [WMT, NMT, SameTime, Transformer, BPE]
---

# Phase 6 Transformer——从 3 到 11，再到学术基线

> Attention 跑了 15 组实验，最高 3.77。Transformer 第一轮就 11.49。

## 为什么 Transformer 秒杀 Attention

不是因为 Transformer 更聪明——是因为 Attention 的 decoder 是 Python for-loop，而 Transformer 是**全向量化**的。

| | Phase 2 Attention | Phase 6 Transformer |
|---|---|---|
| Decoder | for t in range(T): attention per step | `torch.matmul(Q, K.T)` 一气呵成 |
| 速度 | ~15 min/epoch | ~3 min/epoch |
| 最优 BLEU | 3.77 (A15, 双头+α=0.8) | 11.49 (词级, ep8) |

速度差 5 倍，BLEU 差 3 倍。这两个差距其实同源：**计算效率决定了你能跑多少 epoch、多少数据、多深的网络。**

## Phase 6 实验矩阵

全部 30 epoch, BPE 8K, label smoothing 0.1, warmup scheduler：

| E-# | 实验 | 配置 | Params | BLEU | 分析 |
|------|------|------|------|------|------|
| E-024 | B0 词级 | d256/3L/4H | 53.6M | 11.49 | 词级 baseline |
| E-025 | B1 BPE | d256/3L/4H | 11.6M | 10.66 | BPE 小模型反降 |
| E-026 | B2 BPE | d512/6L/8H | 56.4M | 8.18 | 过拟合——参数过多 |
| E-028 | B4 BPE | d512/3L/8H | ~30M | 8.57 | 宽不加深，仍过拟合 |
| E-029 | B5 BPE | d256/4L/4H | ~14M | 11.52 | B1→B3 中间点 |
| **E-027** | **B3 BPE** | **d256/6L/4H** | **17.2M** | **11.70** | ✅ **最优** |

### B3 的启示

B3 (d256/6L) 用 17.2M 参数跑出 11.70 BLEU——**BPE 首次超过词级 baseline (11.49)**。

关键发现：
- **深度 > 宽度**：6 层 256 维 (17M) > 3 层 512 维 (56M) ——参数效率差 3 倍
- **160K 句子匹配 ~15M 参数**：B2 的 56M 严重过拟合，B3 的 17M 刚好
- BPE 的真正优势在中型模型：vocab 效率释放了 embedding 参数，让每层能更宽更深

## 通往学术基线的路

IWSLT14 De-En 上，标准 Transformer 论文配置（d512, 6 layers, 8 heads, BPE 8K）通常达到 20-25 BLEU。我们的路线：

| 步骤 | 改动 | 预期 BLEU | E-# | 状态 |
|---|---|---|---|---|---|
| B0 | 词级 d256/3L | 11.49 | E-024 | ✅ |
| B1 | BPE d256/3L | 10.66 | E-025 | ✅ |
| B2 | BPE d512/6L/8H | 8.18 | E-026 | ✅ 过拟合 |
| **B3** | **BPE d256/6L** | **11.70** | **E-027** | ✅ **最优** |
| B4 | BPE d512/3L | 8.57 | E-028 | ✅ 宽过浅 |
| B5 | BPE d256/4L | 11.52 | E-029 | ✅ |
| **B6** | **BPE d256/6L + K_lang** | **~8.1** | **E-030** | ❌ 反降 |
| — | TW/AW 系列 (WMT14) | 进行中 | E-031+ | 🔄 |

## 从 BLEU 3 到 11，我们学到了什么

**1. 架构和损失函数是一体两面——都是梯度的产生方式**

Phase 2 花了 15 组实验 (A1-A15) 在损失函数上反复调试。SoftBLEU、K_lang、双头梯度相乘——最好的一组 A15 达到 3.77 (+9.3% vs CE-only)。Transformer 第一轮就用纯 CE 跑到 11.49。

看起来像是"架构 > 损失函数"。但其实不是。架构和损失函数是同一个东西的两面：**都是定义了梯度的产生方式。**

- 架构改变 → `hidden_seq` 的表示能力变了 → `∂L/∂W` 经由不同路径回传 → 梯度的**接收面**不同
- 损失函数改变 → `L` 的定义变了 → `∂L/∂W` 的量级和方向变了 → 梯度的**来源**不同

Attention 上用 K_lang + 0.18 BLEU，Transformer 上一轮架构跳变就 +7.7 BLEU——这不是因为 Architecture > Loss，而是因为 Attention 的瓶颈在表示能力（LSTM 时序链），不是损失函数的梯度。换个场景，当架构的表达力已经够用，但数据分布有偏斜，调损失函数就是唯一的出路。

**梯度的多寡和方向才是学习的唯一原料。架构和损失函数只是不同的食谱。**

**2. BPE 在小模型上反效果——但不是永远的**

BPE 的 8K vocab 把 embedding 参数从 33.5M 砍到 4M——在 d256/3L 模型上，总参数从 53.6M 缩到 11.6M。浅模型容量被压过了 BPE 的子词泛化收益。

但 B3 (d256/6L, 17.2M) 用 BPE 跑到 11.70，首次盖过词级 baseline (11.49)。**BPE 的桶压缩需要深度补偿——这一点恰恰印证了 K_lang 框架。**

**3. K_lang 在 Transformer 上失效——SoftBLEU 是缺陷补偿器**

B6 (d256/6L + K_lang, k=170, α=0.8)：BLEU 止步于 ~8.1。同样架构不用 K_lang 跑 11.70。

K_lang 在 RNN (BLEU 3.0→3.21, +7%) 上有效，在 Attention (3.45→3.77, +9%) 上有效。但在 Transformer (11.70→8.1, −31%) 上反降。模式很清楚：

- **基线越强，K_lang 增益越小**。RNN 的 CE 梯度是弱鸡（BLEU 3），K_lang 的 333× 放大确有作用。Transformer 的 CE 梯度已经足够精准，SB 头的梯度穿过 6 层 Transformer，**打乱了 CE 辛苦优化的 attention 模式**。
- SoftBLEU 不是通用增强器，是缺陷补偿器。**当模型本身表达力不足时它帮忙，当模型够强时它捣乱。**

**4. 梯度训练 = Hash 编码 + Riemann 积分**

训练一个 Transformer，本质上就是把语言**逐词逐句 hash 编码进权重张量**，每一步梯度是当前 batch 的语言统计快照，训练过程就是把这些快照永久存储：

$$W_T = W_0 + \sum_{t=0}^{T} (-\eta \cdot \nabla \mathcal{L}_t) \quad \xrightarrow{\eta \to 0} \quad W_0 + \int_0^T \nabla \mathcal{L}(t) \, dt$$

每一个 `optimizer.step()` 的执行流程：

1. **词 → embedding hash**：token → $\mathbb{R}^d$ 向量，查表
2. **前向撞桶**：hidden 层把向量推过 6 层 attention + FFN，到 output 层做 softmax 查桶
3. **比对碰撞**：预测桶 vs 目标桶 → `CrossEntropy` 算出误差
4. **反向修正**：$\nabla\mathcal{L}$ 告诉你桶壁该往哪边挪
5. **积分存储**：$W \mathrel{-}= \eta \cdot \nabla\mathcal{L}$ 把这次碰撞经验**热记录**进权重

50 epoch × 2500 batch/epoch = 125,000 次积分。这 125,000 次 hash 碰撞的逐次累积，把 160K 句 IWSLT14 的全部语言统计模式寄存到了 17M 个参数里。

在这个框架下，所有我们调试的变量都有了统一的物理意义：

| 变量 | 物理意义 |
|---|---|
| **K_lang（k）** | 每次积分时，多少个桶参与修正（桶太少→信息丢失，桶太多→噪声稀释） |
| **α（SB 权重）** | SB head 的碰撞修正力度 |
| **lr（η）** | Riemann 积分的步长（dt） |
| **深度（n_layers）** | hash 链的长度——每个 token 经历多少次碰撞 |
| **宽度（d_model）** | hash 桶的容量——每个桶能存多少信息 |
| **BPE vs 词级** | hash 桶的大小选择——大桶少量 vs 小桶多量 |

**3. 早停 + 倒 U 是所有模型的共有特征**

无论是 Phase 2 Attention (ep2 峰) 还是 Phase 6 词级 Transformer (ep8 峰)，BLEU 都呈现峰值后回落。这不是过拟合——loss 和 BLEU 同时变好。这是 teacher forcing 的 exposition bias。

**4. 日志就是 infrastructure**

Loki 驱动 + Grafana 看板 = 看一眼就知道实验跑到哪了。没有基础设施，3 个实验 15 个 epoch 的结果能让你翻半天日志。花 1 天修基础设施省 10 天找日志。

## 更新日志

| 日期 | 实验 | 结果 |
|---|---|---|
| 2026-05-05 | BPE d256/3L (B1) | 10.66 |
| 2026-05-05 | 词级 d256/3L (B0) | 11.49 |
| 2026-05-06 | BPE d512/6L (B2) | 8.18 — 过拟合 |
| 2026-05-06 | BPE d256/6L (B3) | **11.70** — 最优 |
| 2026-05-06 | BPE d512/3L (B4) | 8.57 |
| 2026-05-06 | BPE d256/4L (B5) | 11.52 |
| 2026-05-06 | BPE d256/6L + K_lang (B6) | 8.02 — SoftBLEU 缺陷补偿器 |

**核心发现**：深度 > 宽度。d256/3L→4L→6L 步步上升 (10.66→11.52→11.70)，但 d512/3L 和 d512/6L 双双过拟合。160K 句的 IWSLT14 上，17M 参数的 d256/6L 是甜点。

---

*May the Code be with us.*

---

> **License: GPLv3**  
> 本文《SameTime》系列采用 GNU 通用公共许可证第三版 (GNU General Public License v3.0) 协议进行开源发布与分发。允许任何形式的复制、修改和分发，但必须继承相同的开源协议，承认在算力宇宙中所有的迭代与变异。
