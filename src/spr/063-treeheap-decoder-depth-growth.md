---
title: "[SPR-063] 不再只会拆模型：用递归深度观察 TreeHeap Decoder 的能力生长"
date: 2026-07-18
lastmod: 2026-07-18
weight: 63
author: Houming818 & Codex Review
description: "从删除式消融转向递归深度剂量实验：用约150字长文本构造二叉到八叉 TreeHeap，观察 Decoder 的 Loss 是否随递归深度形成结构特有的生长曲线，并用等节点 Flat、随机树、乱边、未见深度和未见叉数排除单纯信息量增加。"
tags: [SPR, TreeHeap, ARA, Decoder, Recursion, Depth, Branching Factor, Ablation, Causal Inference, Emergence]
---

# 不再只会拆模型：用递归深度观察 TreeHeap Decoder 的能力生长

> 本文是一份实验设计，不是成功公告。
>
> 我们刚完成一次删除式因果审计，也发现自己对结果解释过度。现在公开修正问题，并邀请读者在运行新实验以前审核 Claim、Predict、对照组和失败条件。

本文的核心观察方法由 Houming818 提出：TreeHeap 的递归深度可以逐级增加，因此不应只通过删除结构观察损失，还可以把深度作为控制变量，观察 decoder 能力如何正向生长。Codex Review 负责把该想法整理为可证伪的 ARA 实验设计。

---

## 1. 这次问题是怎样出现的

TreeHeap 当前有一个正在全语料训练的 encoder-decoder 模型。

简化后，它的工作过程是：

```text
输入句子
  ↓
TreeHeap encoder / FOLD
  ↓
不同递归深度的 H_state
  ↓
decoder READ
  ↓
下一个 token 的概率桶
```

例如输入：

```text
小明喜欢吃米饭
```

decoder 可能输出：

| 下一个 token | 概率 |
|---|---:|
| 。 | 0.55 |
| 和 | 0.12 |
| ， | 0.08 |
| 天气 | 0.001 |

训练时，我们用正确 token 的负对数概率计算 NLL。正确答案的概率越高，NLL 通常越低。

问题是：

> decoder 得到了更低的 NLL，究竟是因为它读取了 TreeHeap 的递归结构，还是只读取了装在 TreeHeap 容器里的 token 内容？

这两个系统表面上都可能生成正常句子，但架构意义完全不同。

---

## 2. 第一轮办法：拆掉一部分，看 Loss 是否增加

最常见的研究方法是消融。

例如：

- 把 `H_state` 全部清零；
- 把 A 句子的状态交给 B 句子的 decoder；
- 打乱左右节点；
- 切掉 root；
- 切掉某一层 detail。

如果干预后 NLL 增加，我们可以说：

> 被干预的信息对当前输出具有因果作用。

在冻结的 step-160K checkpoint 上，我们做了 64 条 held-out 样本的 CPU 审计。

结果如下：

| Frontier | 正常 NLL | 换成别句状态 | 相邻左右互换 | 前后半区互换 |
|---|---:|---:|---:|---:|
| root | 5.2319 | +0.7669 | +0.00834 | +0.00381 |
| middle | 5.1910 | +0.7448 | +0.00642 | +0.00681 |
| leaf | 5.1321 | +0.8084 | 约 0 | 约 0 |

这组数据至少说明：

1. decoder 不是完全脱离输入的语言模型；
2. 给它错误句子的状态，NLL 会显著恶化；
3. 当前 leaf READ 对节点排列不敏感；
4. root 和 middle 对这两种结构换序只有很小的响应。

我们最初把结论写成了：

> decoder 主要读取无序内容，当前 TreeHeap 拓扑贡献很弱。

这句话有一半成立，另一半需要撤回来重新审视。

---

## 3. 删除式消融为什么不够

Houming818 提出了一个关键异议：

> decoder 可能是训练中涌现出来的私有黑盒协议。只看删掉某个结构以后损失多少，未必足以判断它是否利用了 TreeHeap。

这个异议是成立的。

### 3.1 离开训练流形

模型训练时看到的是合法 TreeHeap 状态。

我们把某层突然清零、乱序或换成其他样本以后，得到的可能不是“缺少一个结构特征的合法状态”，而是一份模型从未见过的异常数据。

此时性能下降，只能说明模型不喜欢异常输入。

性能没有下降，也可能是模型把异常状态识别为噪声并绕开了它。

### 3.2 冗余通道会互相补偿

TreeHeap 的信息可能同时存在于：

- root；
- 多层 parent；
- detail residual；
- leaf；
- decoder 的循环状态。

删除一条通道以后，另一条通道可能补偿它。

所以：

```text
删除 A 后没有损失
```

不能直接推出：

```text
A 从未参与计算
```

### 3.3 一次干预可能同时改变很多东西

把左右子树互换，不只改变了“左右地址”。

它还可能改变：

- token 的局部搭配；
- parent state 的数值；
- 后续 FOLD 的输入分布；
- decoder 看到的相似度关系。

我们很难确认最终 NLL 变化究竟来自哪一项。

### 3.4 黑盒算法可能不是局部规则

decoder 的某种能力可能分散在许多节点和许多时间步中。

它不是：

```text
删除这个节点
→ 丢失这个明确功能
```

更可能是：

```text
许多状态共同形成一个私有协议
→ 输出概率逐步改变
```

因此，删除式消融适合寻找因果依赖，但不等于读懂涌现协议。

---

## 4. 换一个观察方向：不是删除，而是逐层增加

TreeHeap 天然具有递归深度：

```text
depth 0:                 root

depth 1:            left      right

depth 2:          ...          ...

depth 3:        更细的局部子堆

...

depth D:        token / leaf 层
```

于是可以改变问题：

> 当 decoder 可以读取越来越深的 TreeHeap 时，它的能力是否按某种规律生长？

这不是传统的“删除一块”。

它更接近：

```text
只给 root
→ 增加一层
→ 再增加一层
→ 继续递归读取
→ 观察能力怎样出现
```

本文暂时称它为：

> **递归深度剂量实验**，Recursive Depth Dose Experiment。

“剂量”不是医学含义，只是表示我们把递归深度当作连续增加的控制变量。

---

## 5. 一个本科生可以手算的例子

假设我们有八个 leaf：

```text
[a, cat, is, eating, some, rice, at, home]
```

TreeHeap FOLD 后形成：

```text
                         H0
                  /              \
                H1L              H1R
              /    \           /    \
            H2A    H2B        H2C    H2D
           /  \    /  \      /  \    /  \
          a  cat  is eating  some rice at home
```

我们并不要求 `H1L` 必须能够翻译成“主语”，也不要求 `H2B` 必须叫“动词短语”。

encoder 和 decoder 可以形成自己的私有编码。

我们只控制 decoder 能走多深。

### 深度 0

decoder 只能读取：

```text
[H0]
```

得到 Loss：

```text
L0 = 5.8
```

### 深度 1

允许共享 READ kernel 从 root 展开一层：

```text
[H1L, H1R]
```

得到：

```text
L1 = 5.2
```

### 深度 2

继续递归：

```text
[H2A, H2B, H2C, H2D]
```

得到：

```text
L2 = 4.9
```

### 深度 3

继续读到 leaf：

```text
[a, cat, is, eating, some, rice, at, home]
```

得到：

```text
L3 = 4.8
```

定义第 d 层带来的边际收益：

$$G_d=L_{d-1}-L_d$$

在这个假想例子里：

| 新增深度 | Loss | 边际收益 |
|---|---:|---:|
| depth 0 | 5.8 | - |
| depth 1 | 5.2 | 0.6 |
| depth 2 | 4.9 | 0.3 |
| depth 3 | 4.8 | 0.1 |

这条曲线意味着：越靠近 root，提供的是粗轮廓；越靠近 leaf，补充的是细节。

但请注意：这张表只是说明怎样读指标，不是我们的实验结果。

---


## 5.1 为什么需要约 150 字的长文本

八个 leaf 适合讲原理，却不适合检验递归是否真的参与了语言解码。

因为八个 leaf 的二叉树只有三层。decoder 即使背下一组有限模式，也可能看起来像学会了递归。

新的主实验应使用约 150 个汉字的连续文本，例如：

```text
夏天傍晚，河岸边的风从树林里穿过。孩子们收起风筝，
老人坐在石阶上聊天，远处的公交车刚刚亮起车灯……
```

实际样本需要来自 held-out 真实语料，而不是反复使用人工写的一段话。

这里必须同时报告两个长度：

- 原始中文字符数；
- tokenizer 切分后的 BPE token 数，也就是实际 TreeHeap leaf 数。

“约 150 字”是给人阅读的样本尺度；真正决定树高的是 leaf 数 $N$。

长文本带来三个价值：

1. 树能够自然形成多层递归，而不是只有两三步；
2. root、粗粒度 parent 和细粒度 leaf 之间出现足够大的压缩距离；
3. decoder 必须处理跨句和长程信息，局部 token 词袋更难解释全部结果。

主任务可以使用“前 150 字编码，预测随后一小段真实文本”的 future-span NLL。这样 target 不在 source 里，避免把完整原句直接复制给 decoder。

---

## 5.2 不只改变深度，还要改变树的分支数

Houming818 进一步提出：同一段约 150 字的文本，可以分别构造成二叉、三叉，一直到八叉 TreeHeap。

这里的“度”容易与图论中的节点总度数混淆。本文统一使用：

```text
k 叉树 / branching factor k
```

表示每个 parent 最多接收 $k$ 个 children。

固定 leaf 数为 $N$ 时，平衡 k 叉树的近似深度为：

$$D_k=\lceil\log_k N\rceil$$

假设 $N=150$，不同分支数的自然深度约为：

| 分支数 k | 自然递归深度 | 完整树可容纳的 leaf 上界 |
|---:|---:|---:|
| 2 | 8 | 256 |
| 3 | 5 | 243 |
| 4 | 4 | 256 |
| 5 | 4 | 625 |
| 6 | 3 | 216 |
| 7 | 3 | 343 |
| 8 | 3 | 512 |

这张表说明：

- 二叉树路径较长，每次 FOLD 只合并少量邻居；
- 八叉树路径较短，每次 FOLD 必须压缩更大的局部范围；
- 四叉和五叉可能具有相同整数深度，但每个 parent 的信息负担不同；
- 递归深度不是手工指定的标签，而是 leaf 数和分支规则共同产生的结果。

实验不应该真的创建 625 个位置再用零填满。

更合理的实现是 ragged balanced tree：

```text
每次从左到右
最多取 k 个有效 child
用同一个 FOLD kernel 合成 parent
最后一组不足 k 个时使用 mask
继续递归，直到只剩 root
```

这样只计算有效节点，并把每层有效节点数写进 Evidence。

---

## 5.3 为什么 k=2 到 k=8 是一条新的观察轴

原来的深度剂量实验固定树结构，只改变 decoder 读到哪一层。

现在我们得到两个变量：

$$L(k,d)=\operatorname{NLL}(\text{k叉TreeHeap读取到深度d})$$

其中：

- $k$ 控制每次 FOLD 的局部压缩范围；
- $d$ 控制 decoder 已经递归读取了多少层；
- $L(k,d)$ 测量该条件下的预测损失。

对同一段文本，可以画出多条曲线：

```text
k=2  二叉树深度曲线
k=3  三叉树深度曲线
...
k=8  八叉树深度曲线
```

我们暂时不预测“叉数越大越好”或“二叉一定最好”。

这正是实验要回答的问题。

可能出现：

- 小 $k$ 路径太长，信息经过多次压缩后衰减；
- 大 $k$ 单次合并负担太重，parent 难以保存局部关系；
- 中间某个 $k$ 在压缩率和局部表达之间形成更好的平衡；
- 所有 $k$ 表现相同，说明当前 decoder 主要读取内容容量，而非树形递归。

---

## 5.4 必须使用同一个可变叉数 FOLD kernel

如果二叉树、三叉树和八叉树各自拥有一套独立参数，就无法判断差异来自树结构还是参数数量。

因此应定义一个最多支持八个 child 的共享 kernel：

$$h_{parent}=F_\theta(h_1+e_1,\ldots,h_k+e_k,mask)$$

其中：

- $F_\theta$ 在所有深度和所有 $k$ 上共享；
- $e_i$ 表示 child slot，而不是绝对 token 位置；
- 不存在的 child 由 mask 排除；
- $\theta$ 的参数量不随 $k$ 增加。

decoder 的 READ kernel 同样共享：

$$q_{d+1}=R_\phi(q_d,S_{k,d})$$

于是改变 $k$ 和 $d$ 时，变化的是 TreeHeap 的递归组织方式，不是偷偷增加一套模型。

更强的外推测试可以只训练：

```text
k = 2, 4, 8
```

再冻结参数，测试未见过的：

```text
k = 3, 5, 6, 7
```

如果中间叉数仍形成连续、合理的 Loss 曲线，说明 kernel 学到的可能是可组合规则，而不是记住三个树型编号。

---

## 5.5 不同叉数之间怎样公平比较

同样的 depth，在不同 $k$ 下代表完全不同的信息量。

例如：

```text
二叉树展开两层，最多看到 4 个 frontier 节点
八叉树展开两层，最多看到 64 个 frontier 节点
```

因此不能只比较相同的 $d$。

我们需要同时按三种横轴画图：

1. 递归深度 $d$；
2. 可见 frontier 节点数；
3. 压缩比例。

定义压缩比例：

$$\rho_{k,d}=\frac{N_{frontier}(k,d)}{N_{leaf}}$$

公平结论应该优先比较相近的 $\rho$、节点预算和 FLOPs。

例如：

```text
二叉 depth 4，得到 16 个 frontier state
四叉 depth 2，同样得到 16 个 frontier state
八叉 depth 1，得到 8 个 state，作为最近的可用预算点
```

它们可能暴露近似数量的 frontier state。只有在这种等预算位置比较，才能判断哪种递归组织更有效。

---

## 5.6 更新后的实验矩阵

主实验不再只是一条 depth 曲线，而是一张矩阵：

| 变量 | 取值 |
|---|---|
| 文本长度 | 约 150 中文字符，并记录实际 BPE leaf 数 |
| 分支数 | $k=2,3,4,5,6,7,8$ |
| 读取深度 | $d=0,1,\ldots,D_k$ |
| 结构条件 | learned TreeHeap、Random Tree、Shuffled Links、Flat、Repeated Root |
| 参数 | FOLD 与 READ 在所有 $k,d$ 共享 |
| 任务 | held-out future-span NLL，另报告自由生成样例 |
| 重复 | 至少三个 seed |

这套设计允许同时回答：

1. 增加递归深度是否持续提供信息？
2. 同等压缩率下，哪种分支数更有效？
3. learned TreeHeap 是否优于随机树和扁平 memory？
4. 未见深度和未见叉数能否外推？
5. decoder 的能力曲线是否真的随递归结构生长？

---

## 6. 仅仅看到 Loss 下降，仍然不能证明 TreeHeap

深度增加时，decoder 通常会看到更多节点。

更多节点意味着更多信息容量。

所以即使 TreeHeap 完全没有价值，也可能出现：

```text
节点越多
→ 信息越多
→ Loss 越低
```

这只能证明“更多信息有用”，不能证明“递归结构有用”。

因此必须安排等预算对照。

---

## 7. 五个必须同时运行的对照组

### 7.1 TreeHeap 递归展开

按真实 parent-child 地址，从 root 一层层展开。

每层使用同一个共享 READ kernel：

$$q_{d+1}=R_\theta(q_d,H^{(d)})$$

这里最重要的是 `R_theta` 在各层共享。

否则模型可以为 depth 1、depth 2、depth 3 分别背一张参数表，并没有学会递归。

### 7.2 Random Tree

节点数量、向量维度和 decoder 完全相同，但父子关系随机生成。

它回答：

> 只要有一棵树就行，还是训练得到的 TreeHeap 结构有用？

### 7.3 Flat Nodes

提供相同数量的向量，但取消父子层级，把它们作为普通集合交给 decoder。

它回答：

> 收益来自递归结构，还是仅仅来自增加 memory slot？

### 7.4 Shuffled Links

保留所有节点值，只打乱 parent-child 边。

它比清零更温和，因为信息总量没有减少，主要改变的是组合关系。

它回答：

> decoder 依赖节点内容，还是依赖节点之间的连接方式？

### 7.5 Repeated Root

重复提供 root，使向量数量和计算次数与 TreeHeap 相同：

```text
[root, root, root, root]
```

它回答：

> 收益是否只是因为 decoder 多计算了几次？

---

## 8. 公平实验最难的地方：控制信息预算

假设 TreeHeap depth 2 看到了四个节点，而 Flat baseline 只看到一个节点。

TreeHeap 更好，没有解释力，因为它获得了四倍 memory。

公平比较至少需要保持：

- 可见节点数相同；
- 每个节点维度相同；
- decoder 参数量相同；
- READ 次数相同；
-训练 token 数相同；
- 优化器和学习率相同；
- target prefix 相同；
- 测试样本相同。

我们还应该报告：

$$\text{单位节点收益}=\frac{L_0-L_d}{N_d}$$

以及：

$$\text{单位计算收益}=\frac{L_0-L_d}{FLOPs_d}$$

否则实验可能只是在证明“花更多算力会更好”。

---

## 9. Decoder 应该怎样读取递归层

最直接的方案不是为每层单独设计一个 decoder。

我们使用共享递归 READ：

```text
q0 = 当前 decoder query

q1 = READ(q0, root)
q2 = READ(q1, children(root))
q3 = READ(q2, grandchildren(root))
...
```

数学上：

$$q_{d+1}=R_\theta(q_d,S_d)$$

其中：

- `q_d` 是读到第 d 层后的 decoder 状态；
- `S_d` 是当前深度暴露的 subheap frontier；
- `R_theta` 是每一层重复使用的同一个 kernel；
- `theta` 不随深度改变。

最终概率桶为：

$$P(y_t\mid y_{<t},H,d)=\operatorname{softmax}(Wq_d+b)$$

然后计算：

$$L_d=-\sum_t\log P(y_t^*\mid y_{<t}^*,H,d)$$

这样，深度不是一个写死的类别编号，而是同一算子被递归调用的次数。

---

## 10. 为什么“未见深度外推”是最强检查

如果训练时已经完整见过 depth 0 到 depth 6，模型可能记住：

```text
depth 3
→ 使用某种固定统计模式
```

这不一定是递归能力。

更强的实验是：

```text
训练只允许 depth 0、1、2、3
测试增加 depth 4、5、6
```

参数 `theta` 在测试时冻结。

如果未训练过的更深递归仍然继续降低 Loss：

$$L_4>L_5>L_6$$

就说明共享 READ kernel 学到了一条可以重复应用的规律。

如果训练深度内有效，但一超过 depth 3 就失效，模型更可能学到的是有限深度协议，而不是可扩展递归。

这里也不要求每一层都严格下降。

语言信息可能分布在不同尺度：

- 某一层带来大幅收益；
- 某几层几乎不变；
- 太深以后引入细节噪声，Loss 反而略升。

我们关注的是可重复的曲线形状，以及它是否显著优于对照组。

---

## 11. 这比删除式消融强在哪里

删除式消融观察：

```text
完整模型
- 某个部件
= 损失多少
```

递归深度剂量实验观察：

```text
最小结构
+ 一层递归
+ 一层递归
+ 一层递归
= 能力怎样生长
```

前者提供破坏后的因果响应。

后者提供结构逐步参与计算的建设性轨迹。

两者并不冲突：

- 消融适合发现不可替代通道；
- 深度生长适合发现递归计算过程；
- link shuffle 适合检查结构关系；
- 未见深度适合检查共享规则能否外推。

真正可靠的结论应由多种观察方式共同支持，而不是由一个公式决定。

---

## 12. 新 Claim

拟议 Claim ID：

```text
S3-DECODER-DEPTH-GROWTH-C01
```

Claim：

> 对约 150 字的真实长文本，在相同节点、参数、训练数据和 READ 计算预算下，同一组可变叉数 FOLD/READ kernel 递归读取二叉到八叉合法 TreeHeap frontier，应形成优于 Random Tree、Flat Nodes、Shuffled Links 和 Repeated Root 的深度-Loss 生长曲线；该规律应部分外推到训练未见的更深递归和未见叉数。

这条 Claim 包含四个不同层次：

1. decoder 能从增加的层级获得信息；
2. 收益来自 TreeHeap 结构，不只是更多节点；
3. 收益来自共享递归规律，不只是记住训练深度。
4. 同一套算子能够处理不同分支数，而不是为每种树单独训练模型。

三层必须分开报告。

---

## 13. 运行前 Predict

以下阈值是供审核的预注册草案，运行前可以修改，运行后不得追着结果改。

### P1：状态增长

从 root 增加到训练最大深度时，TreeHeap held-out NLL 至少下降：

```text
0.05
```

这只证明更深状态可读，不证明结构优势。

### P2：结构特异性

至少连续两个深度上：

$$G_d^{TreeHeap}-\max(G_d^{Random},G_d^{Flat})\ge 0.02$$

若不成立，收益可以由随机层级或扁平容量解释。

### P3：连接因果性

打乱 parent-child links 后，TreeHeap 的累计深度收益至少损失 50%：

$$\frac{Gain_{Tree}-Gain_{Shuffled}}{Gain_{Tree}}\ge 0.5$$

若不成立，节点值可能有用，但连接关系没有得到证明。

### P4：未见深度外推

只训练 depth 0 到 depth 3。

测试 depth 4 到 depth 6 时，至少两个新增深度继续提供正收益，并且总收益超过 Flat 对照：

```text
0.02 NLL
```

### P5：未见叉数外推

只用 $k=2,4,8$ 参与训练，冻结参数后测试 $k=3,5,6,7$。

至少两个未见叉数在等压缩率位置继续优于各自的 Random Tree 或 Flat 对照：

```text
0.02 NLL
```

若只在训练见过的三个叉数有效，不能宣称 kernel 学到了可变叉数规则。

### P6：共享参数检查

所有深度和所有叉数必须使用同一组 FOLD/READ kernel 参数。

如果每层或每种叉数有独立参数，P4/P5 不成立，实验不得宣称递归或叉数外推。

### P7：重复性

至少运行三个 seed。

关键方向在三个 seed 中必须一致，并报告均值、标准差和每个 seed 的原始数据。

---

## 14. 结果出来后怎样判读

### 情况 A：所有方法都随深度同样改善

结论：

> 更多信息或更多计算有用，但没有 TreeHeap 特异证据。

### 情况 B：TreeHeap 优于 Flat，但与 Random Tree 相同

结论：

> 层级或稀疏递归可能有用，但当前 TreeHeap 学到的父子关系没有额外价值。

### 情况 C：TreeHeap 优于 Random 和 Flat，但 Link Shuffle 不掉分

结论：

> 节点状态可能已经携带结构摘要，但 decoder 是否利用边仍然不清楚。

### 情况 D：TreeHeap 曲线更好，Link Shuffle 破坏收益

结论：

> 当前任务中，合法 TreeHeap 的节点和连接关系都具有因果作用。

### 情况 E：训练深度有效，未见深度失败

结论：

> 学到了有限深度协议，没有证明可扩展递归。

### 情况 F：未见深度继续改善

结论：

> 共享 READ kernel 出现了可重复应用的递归规律。

### 情况 G：未见深度有效，但未见叉数失败

结论：

> 模型可能学会了固定树型上的递归，还没有学会可变分支数的通用 FOLD/READ 协议。

即使出现情况 F，也不能自动宣称：

- 模型理解了语法；
- TreeHeap 优于 Transformer；
- 形成了世界模型；
- 产生了意识。

它只支持一个重要但有限的结论：

> decoder 的能力增长与 TreeHeap 递归计算发生了可测量联系。

---

## 15. 对 step-160K 审计的正式修正

旧实验保留，因为它提供了真实信息：

- source state 是因果的；
- 固定 frontier 的无位置 attention 对节点排列近似不变；
- 64 条样本上的简单结构换序响应很小。

但旧实验不再被解释成：

```text
decoder 没有利用 TreeHeap
```

更准确的状态是：

```text
decoder 使用了 H_state
固定 frontier READ 具有集合不变性
简单删除/换序尚未证明 TreeHeap 递归协议
结构利用问题仍然 open
```

公开修正不是推翻 Evidence。

它是在缩小 Evidence 能够支持的语言范围。

---

## 16. 计划保存的 Evidence

实验运行后应保存：

```text
ARA 预注册设计
训练和测试命令
代码 commit
checkpoint hash
每个 seed 的 depth-NLL 曲线
每层边际收益 G_d
节点数与 FLOPs
Random / Flat / Shuffled / Repeated-root 对照
未见深度结果
stdout / stderr
summary.json
失败条件判定
```

图表至少包括：

1. 横轴为递归深度、纵轴为 NLL 的主曲线；
2. 每层边际收益柱状图；
3. 单位节点收益；
4. 未见深度区域的单独标记；
5. 三个 seed 的误差范围。

这样公众不需要相信作者的形容词，只需要检查曲线、代码和门槛。

---

## 17. 本文最重要的一句话

我们不再只问：

> 拆掉 TreeHeap 的一部分，模型会不会变差？

我们开始问：

> 当同一个 READ kernel 沿 TreeHeap 一层层递归时，模型能力是否以一种对照系统无法解释的方式逐步生长？

前者寻找缺失造成的伤口。

后者寻找结构参与计算的轨迹。

这仍然不是最终答案，但它比“看输出像不像一句话”更接近一个可公开审核的 TreeHeap decoder 研究方法。

---

## 当前状态

```text
Claim:   S3-DECODER-DEPTH-GROWTH-C01
Status:  open / design for public review
Proof:   not started
Evidence: none
```

本文发布在实验运行以前。

如果设计存在信息预算不公平、对照组不足、阈值不合理或数学定义错误，应当现在指出，而不是等结果出来以后再替它寻找故事。
