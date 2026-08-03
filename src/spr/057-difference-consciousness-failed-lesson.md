---
title: "[SPR-057] 一次 100% 却失败的实验：为什么差分不能替我们找到意识"
date: 2026-07-15
lastmod: 2026-07-15
weight: 57
author: Houming818 & Codex Review
description: "一个显式 DIFF-TRANSPORT-APPLY 模型在有限类比任务上达到 100%，但 World TreeHeap 几乎可被删除，较小的 Transformer 同样满分。本文公开这次失败，并解释为何内部差分适合做诊断，却不足以解释意识或涌现。"
tags: [SPR, TreeHeap, ARA, Analogy, World Model, Emergence, Negative Result, Original Research]
---

# 一次 100% 却失败的实验：为什么差分不能替我们找到意识

这是一篇失败记录。

更准确地说，这是一次**指标成功、研究目标失败**的实验。

模型在四类有限世界类比任务上达到了：

~~~text
token accuracy     = 100%
sequence exact     = 100%
~~~

如果只看最终分数，这似乎是一场漂亮胜利。

但经过因果干预后，我们发现：模型几乎没有使用我们专门设计的 World TreeHeap。一个参数更少的普通 Transformer 也达到了 100%。

因此，这个实验没有证明 World TreeHeap，没有证明 TreeHeap 的类比优势，更没有触及意识。

它反而留下了一条重要教训：

> 差分可以帮助我们观察模型发生了什么，但不能仅凭一个漂亮的差分结构，就宣布我们理解了模型的意识、语义或推理过程。

---

## 1. 这条路线是怎样开始的

我们先观察到一个合理问题。

考虑两句话：

~~~text
小明喜欢吃红薯。
小明喜欢吃土豆。
~~~

如果 encoder 将整句话写成 TreeHeap，那么两个状态之间应该存在某种变化：

$$ \Delta H=H_{土豆}-H_{红薯}. $$

但 Houming818 很快指出，这不应该只是：

~~~text
embedding(土豆)-embedding(红薯)
~~~

因为同一个实体替换，在不同世界背景中的意义不同：

~~~text
小明喜欢吃红薯 → 小明喜欢吃土豆
红薯要两元一斤   → 土豆要两元一斤
~~~

前者改变的是“被食用对象”，后者改变的是“被定价实体”。

于是我们进一步提出：

> 差分可能不是一个普通向量，而是 World TreeHeap 背景中的一个结构变换。

这个想法本身并不荒谬。问题出在我们随后怎样把它实现成了模型。

---

## 2. 我们手工设计了一个看起来完整的推理系统

实验模型被拆成：

~~~text
A ─┐
B ─┼─> DIFF ─> Relation TreeHeap R_AB
W ─┘

R_AB ─┐
C ────┼─> TRANSPORT ─> R_C
W ────┘

C + R_C ─> APPLY ─> predicted H_D ─> Decoder ─> D
~~~

数学形式是：

$$ R_{AB}=DIFF(W,H_A,H_B), $$

$$ R_C=TRANSPORT(W,R_{AB},H_A,H_C), $$

$$ \hat H_D=APPLY(H_C,R_C). $$

我们还预先给出了：

- 固定逻辑槽位；
- 人物、食物、数字和谓词集合；
- 四种关系族；
- `A:B=C:D` 监督格式；
- World TreeHeap 的 15 个参数节点；
- `stop/left/right` 概率路由；
- 状态对齐和文本生成 loss。

从工程角度看，这套模型很完整。

从涌现角度看，它却有一个根本问题：

> 我们把希望模型自己发现的推理步骤，提前写进了模块名字、数据格式和 loss。

---

## 3. Toy 世界包含什么

所有陈述使用八个固定逻辑叶槽。实验生成四类关系。

### 3.1 跨场景实体替换

~~~text
A  P1 EAT FOOD0
B  P1 EAT FOOD6
C  FOOD0 COST N5 UNIT
D  FOOD6 COST N5 UNIT
~~~

### 3.2 数值平移

~~~text
A  FOOD7 COST N5 UNIT
B  FOOD7 COST N6 UNIT
C  P7 BUY FOOD1 N1
D  P7 BUY FOOD1 N2
~~~

这里不能直接把 `N6` 复制到 D，因为 C 中需要的是 `N1→N2`。

### 3.3 人物跨角色迁移

~~~text
A  P10 LIKE P2
B  P8  LIKE P2
C  P3  LIKE P10
D  P3  LIKE P8
~~~

### 3.4 主客体交换

~~~text
A  P3 LIKE P7
B  P7 LIKE P3
C  P4 LIKE P11
D  P11 LIKE P4
~~~

验证集按组合哈希整块留出。模型看过所有原子符号，但没有看过测试中的具体组合。

因此，这不是一个简单的随机六分类实验。它确实要求模型表达一些超出固定 token 替换的关系。

---

## 4. 一个漂亮得危险的结果

训练设置：

| 项目 | 数值 |
|---|---:|
| 训练 step | 6,000 |
| batch | 256 |
| 验证四元组 | 4,096 |
| TreeHeap 参数 | 238,314 |
| Flat Transformer 参数 | 73,574 |
| GPU | RTX 3090 |

最终结果：

| 模型 | Token accuracy | Sequence exact |
|---|---:|---:|
| TreeHeap analogy | 1.0000 | 1.0000 |
| Flat Transformer | 1.0000 | 1.0000 |
| Lexical replacement | 0.9124 | 0.5466 |

TreeHeap 四类关系全部达到 sequence exact `1.0`。

这说明：

> TreeHeap 形态的网络可以表示并学习有限世界类比函数。

但是，“能够表示”与“自然涌现”之间还有很长距离。

---

## 5. 因果干预推翻了漂亮故事

如果 World TreeHeap 真的是关系迁移的背景，那么删除它应显著破坏结果。

实际数据：

| 干预 | Token accuracy |
|---|---:|
| 正常 World TreeHeap | 1.0000 |
| 把 W 全部置零 | 0.9984 |
| 翻转 W 的 heap 地址 | 0.9867 |
| 使用错误的 B 关系 | 0.8284 |

最终路由熵约为：

~~~text
0.000024
~~~

概率路由几乎坍缩到一个固定节点。

也就是说，模型实际学习的是：

~~~text
A/B/C encoder
    ↓
普通非线性映射
    ↓
D
~~~

而不是：

~~~text
A/B
    ↓
查询World TreeHeap
    ↓
读取背景关系
    ↓
迁移到C
~~~

梯度发现了一条更短的道路，并合理地绕开了我们精心设计的 W。

这不是模型“不听话”。

恰恰相反，模型忠实地优化了我们给出的 loss。

---

## 6. 为什么这个设计违背了涌现规律

### 6.1 我们提前写好了推理步骤

还没有训练，我们已经规定：

~~~text
先DIFF
再TRANSPORT
最后APPLY
~~~

模型只需拟合这条监督管线，不需要自己发现类比结构。

### 6.2 数据直接给出了类比格式

训练输入就是：

~~~text
A、B、C → D
~~~

这能验证函数拟合和组合外推，却不能证明模型从普通世界经验中自然形成类比能力。

### 6.3 人工槽位替 encoder 完成了部分工作

我们规定了人物、食物、数字、主语位置和宾语位置。模型没有从自然语言中发现这些结构。

### 6.4 强行指定 W 的职责没有用

任务可以通过 A/B/C 的直接映射解决，所以梯度没有理由把知识写进一个额外 W。

### 6.5 较小的 Flat Transformer 同样满分

这说明 toy 主要考查通用函数逼近，而不是 TreeHeap 独有能力。

---

## 7. 为什么差分不足以分析意识

Houming818 对这次实验的总结是：

> 果然，想要利用差分来分析意识，不太靠谱。

这里需要把边界说清楚。

### 7.1 私有坐标中的减法不是客观语义

如果 encoder 和 decoder 使用自己的私有协议，那么：

$$ H_B-H_A $$

依赖当前坐标系。对 hidden space 做一个保持功能不变的非线性重参数化，裸差分的方向就可能改变。

### 7.2 state 变化不等于模型理解了变化

一个节点改变，可能是：

- token embedding 改了；
- 地址改了；
- LayerNorm 的连锁响应；
- 递归 FOLD 的必然传播；
- 真正的语义关系变化。

只看差分大小无法区分这些来源。

### 7.3 祖先路径变亮可能是数学必然

局部叶节点发生变化后，其祖先节点必然重新计算。看到一条从叶到 root 的红色路径，不代表模型发现了推理链。

### 7.4 观察者可能把自己的分类投射进模型

如果我们预先规定：

~~~text
这是食物差分
这是价格差分
这是主谓宾差分
~~~

再训练 probe 找到这些标签，最后可能只是证明 probe 学会了我们的分类。

### 7.5 “意识”还没有可执行定义

当前 ARA 可以测量：

~~~text
loss
概率
地址依赖
subheap因果作用
生成结果
跨组合迁移
~~~

但它还没有一个可以被程序直接判定的“意识”指标。

在没有操作性定义时，用 cosine、diff 或可视化颜色宣称观察到了意识，是不可证伪的。

---

## 8. 差分是不是完全没用了

不是。

差分仍然是有价值的**诊断工具**：

- 比较一次干预前后的节点变化；
- 观察变化经过哪些地址和深度；
- 检查不同算子是否留下不同响应；
- 定位坍缩、旁路和无效模块；
- 为因果消融选择观察位置。

我们此前的 Differential Atlas 就发现：

~~~text
WRITE、MIRROR、子堆交换
会形成部分不同的多尺度响应曲线
~~~

这可以帮助调试 TreeHeap。

但正确表述应是：

> 差分告诉我们模型状态怎样变化；它不自动告诉我们变化意味着什么，更不能自动上升为意识解释。

---

## 9. 主线回到哪里

ARA 中目前最可靠、也最接近自然学习的节点是：

~~~text
S3-TREEHEAP-ROOT-COMPRESS-C01
        +
S3-TREEHEAP-PYRAMID-C01
~~~

前者在 38,251,247 个真实文本 block 上，仅通过 next-token loss 学会了：

~~~text
64 token → recursive FOLD → root → next token
~~~

破坏左右地址后，valid NLL 增加 `2.6252`；消融不同 head，也产生明显损失。

没有语法标签、Bag 目标、DIFF 目标或类比四元组。这才是当前最接近涌现的证据。

Pyramid 又证明 root 与地址化 detail 可以形成多分辨率容器。

因此主线恢复为：

~~~text
真实语料
  ↓
通用TreeHeap WRITE
  ↓
共享多头kernel forest递归FOLD
  ↓
多分辨率H
  ↓
普通语言预测loss
~~~

模型参数 TreeHeap forest 本身承担世界背景，不再外挂一个被命名为“世界模型”的 W。

---

## 10. Encoder Mask 的对称 Decoder

Encoder 侧仍可以使用 TreeHeap-native 复杂 Mask：

~~~text
遮住局部subheap/detail
→ 逼迫恢复任务所需信息向parent/root聚合
~~~

但 Mask 只是信息压力，不是语义答案。

Decoder 侧的对称操作是概率 UNFOLD：

~~~text
root
  ↓ probabilistic UNFOLD
左右子节点概率桶
  ↓ delayed collapse
下一层subheap
  ↓ recursive UNFOLD
token概率桶
~~~

FOLD 是多对一，因此 UNFOLD 不能是假装精确的逆函数：

$$ P(h_l,h_r\mid h_p,C) = UNFOLD(h_p,C). $$

它必须输出多种可能性，等待源语言、目标前缀和更大上下文进入后再坍缩。

这条路线只规定通用的数据流和训练压力，不规定某个 head 必须学习“食物差分”或“类比运输”。

---

## 11. 这次失败保留了什么

我们保留三个窄结论：

1. TreeHeap 形态的网络能够表达有限类比函数；
2. lexical-copy 无法解决全部数值和角色变换；
3. 因果干预成功发现 World TreeHeap 被绕过。

同时拒绝四个更强结论：

1. 没有证明 World TreeHeap 参与推理；
2. 没有证明类比能力自然涌现；
3. 没有证明 TreeHeap 优于 Transformer；
4. 没有证明差分能够解释意识。

一个 100% 的实验，如果核心模块可以被删除，就仍然是失败。

这正是 ARA 的价值：不是阻止我们犯错，而是让漂亮的错误无法冒充研究结论。

---

## 12. 证据与原创边界

模型、ARA、checkpoint、训练 trace、可读四元组和干预结果均保存在开放仓库 [SameTime](https://github.com/houming818/sametime)：

~~~text
ara/s3-generation/logic/world_treeheap_analogy_transport.md
ara/s3-generation/src/s3_world_treeheap_analogy.py
ara/s3-generation/evidence/s3_world_treeheap_analogy_smoke/
~~~

关于“同一词语变化必须放在全局背景中理解”和“差分不足以分析意识”的研究修正由 Houming818 提出；Codex Review 负责错误模型的形式化、实现、因果审计与本文复盘。

本文是 SameTime 项目的原创研究记录，但不宣称发明向量差分、类比任务、因果消融、World Model、概率树路由、masked modeling 或 coarse-to-fine decoding 等已有公共方法。
