---
title: "[SPR-064] TreeHeap 私有协议实验：协议成立，性能优势未成立"
date: 2026-07-19
lastmod: 2026-07-20
weight: 64
author: Houming818 & Codex Review
description: "TreeHeap 私有协议三 seed 正式实验结果：结构因果性和 encoder-decoder 私有配对成立，但多头收益与 flat 性能优势未成立。"
tags: [SPR, TreeHeap, ARA, Private Protocol, Encoder, Decoder, Lifting, Multi-Head, Transformer]
---

# TreeHeap 私有协议实验：协议成立，性能优势未成立

> **证据状态更新（2026-07-28）：本文的“私有协议成立”表述降级为“teacher-forced decoder 对 TreeHeap 状态存在依赖”。后续 C10 审计发现，同系列训练目标允许 decoder 依靠正确中文前缀降低 NLL，而不必使用英文 source。本文的结构干预数字仍是有效观测，但不能单独证明英文语义被写入 TreeHeap，也不能证明 source-conditioned 私有协议已经形成。详见 SPR-074。**

> 本文首先纠正一个刚刚出现的方向错误：我们已经决定让 TreeHeap 的 encoder 和 decoder 自己形成私有协议，就不应该再由研究者规定“root 必须保存主题”“detail 必须保存次要信息”或者“某个 head 必须学习语法”。我们只设计可微、递归、可寻址的通信结构。协议内部写了什么，由最终任务的梯度决定。最后有没有本事，由实验结果决定。

---

## 1. 什么叫私有协议

给定输入字符串 $X$ 和目标字符串 $Y$，encoder 把输入写入一个 TreeHeap 状态：

$$H=E_\theta(X)$$

decoder 只能读取这个状态，并生成输出概率：

$$P(Y\mid X)=D_\phi(H)$$

训练只使用最终输出的交叉熵：

$$L(\theta,\phi)=-\sum_t \log P_{\theta,\phi}(y_t\mid X,y_{\lt t})$$

梯度同时修改 $E_\theta$ 和 $D_\phi$。只要 encoder 写出的状态能被 decoder 正确读取，loss 就会下降。内部编码不需要像自然语言，也不需要让人类看懂。

这就叫私有协议。它像一个人自己的笔迹：我们不规定每一笔必须代表什么，只要求写的人和读的人使用同一套规则。

但是，“私有”不等于“无法验证”。我们仍然可以验证：

1. encoder 和 decoder 是否真的能够联合完成任务；
2. decoder 是否依赖 TreeHeap，而不是绕过它读取原字符串；
3. 地址、父子关系、递归深度和 head 被破坏以后，输出是否退化；
4. 相同数据、参数量和训练预算下，它是否优于更简单的结构。

---

## 2. 抽水机在协议中是什么

最近建立的 lifting 抽水机，不是语义分类器，也不是“信息价值判断器”。它只是 encoder 和 decoder 共同遵守的递归通信介质。

一次局部 FOLD 接收左右两个状态 $a,r$，产生一个继续向上传播的 parent $p$，以及保留在当前地址的 detail $d$：

$$p=a+U_\theta(r)$$

$$d=r-P_\theta(p)$$

decoder 使用相反方向的运算恢复 children：

$$r=d+P_\theta(p)$$

$$a=p-U_\theta(r)$$

同一组共享 kernel 在整棵树上递归调用：

```text
tokens
  -> WRITE
  -> FOLD 得到 parent + addressed detail
  -> parent 继续递归 FOLD
  -> 形成完整 H_state
  -> decoder 从 H_state 递归 READ / UNFOLD
  -> 输出 token 概率桶
```

这里的 $p$ 和 $d$ 首先只是两个不同位置的私有通信变量。研究者不能提前宣布：

```text
p = 句子主题
d = 表面细节
```

如果将来实验发现某个深度更适合预测全局输出，那是实验结论；不是算法定义。

---

## 3. 我们已经走到了哪里

这条路线并不是今天才提出。ARA 中已经有三段连续证据。

### 3.1 M0：短算子协议能够学习

在受控数论 TreeHeap 中，结构 encoder 学习一个短算子程序，固定 executor 使用 TreeHeap 原生算子恢复目标。

| 测试 | TreeHeap structural restore | Flat program |
|---|---:|---:|
| IID | 0.9270 | 0.1535 |
| OOD 地址 | 0.8400 | 0.0000 |

这说明“学习协议 + 固定结构执行器”在受控世界中可以成立，但联合外推到未见递归深度仍然失败。

### 3.2 Native codec：raw token 能形成地址敏感私有协议

模型从随机参数开始，只用 echo 交叉熵联合训练：

```text
WRITE -> FOLD -> DETAIL -> UNFOLD -> READ
```

| 版本 | 正常 token top-1 | detail 地址错位后 |
|---|---:|---:|
| continuous v1 | 0.9955 | 0.0024 |
| continuous v2 | 0.9915 | 0.0014 |

所有五个算子都收到非零梯度。地址错位几乎摧毁输出，因此模型确实形成了依赖 TreeHeap 地址的私有协议。

但 root 清零后准确率几乎不变。这个协议主要走本地 detail 通道，并没有形成完整的 root-plus-detail 协议。Echo 允许这种答案，所以不能责怪模型“没有学会主题”。

### 3.3 Lifting pump：协议获得了闭合递归载体

抽水机实验已经证明：

- depth-6 闭包最大误差约为 $3.70\times10^{-6}$；
- state MSE 为 $3.14\times10^{-14}$；
- 确定性 token/block echo 都是 1.0；
- WMT checkpoint 从 depth cap 0 开放到 6 时，NLL 从 13.8100 降到 4.6335；
- root、detail 和多个递归 pairing 在 WMT 中具有可测的因果作用。

这证明同一个 decoder 可以沿同一棵 TreeHeap 递归增加可用状态。它没有证明 root 是人类可读摘要，也没有证明 TreeHeap 已经优于 flat sequence。

在 200K WMT 实验中：

| 模型 | NLL | Token BLEU-4 |
|---|---:|---:|
| TreeHeap learned-update lifting | 4.6335 | 9.909 |
| Flat sequence | 4.5419 | 10.572 |

因此当前体检报告是：

```text
私有协议存在                阳性
协议依赖 TreeHeap 地址      阳性
递归 FOLD/UNFOLD 闭合       阳性
真实 WMT 使用多层状态       阳性
翻译质量超过 flat           阴性
内部语义可以被人类解释      未检测，也不是当前门槛
```

---

## 4. 下一条 Claim

下一轮不再证明“私有协议能不能存在”，而测试它有没有工程竞争力。

建议预注册为：

> **S3-PRIVATE-PROTOCOL-BATTLE-C01**：在不提供语法、深度、route、摘要或 head 语义标签的条件下，多个共享递归 TreeHeap kernel 可以仅通过最终 seq2seq 交叉熵形成 encoder-decoder 私有协议；该协议必须在真实任务中稳定训练，因果依赖 TreeHeap 地址和递归结构，并在相同参数、数据与训练预算下，相对单 head TreeHeap 和 flat baseline 产生可测收益。

这条 Claim 没有规定协议内容。它只规定通信介质、训练信号和判分方法。

---

## 5. 实验模型

使用同一份真实数据、同一 tokenizer、同一训练/验证/测试切分和相同随机数据顺序，训练四组模型。

### A. 单 head TreeHeap

```text
token embedding
-> 一个 WRITE/FOLD/DETAIL kernel
-> 一个 H_state
-> 递归 READ/UNFOLD
-> autoregressive decoder
```

这是当前 lifting pump 的直接基线。

### B. 多 head TreeHeap

每个 head 有独立参数，并在相同 TreeHeap 地址上建立自己的状态：

$$H^{(m)}=E_{\theta_m}(X),\qquad m=1,\ldots,M$$

decoder 联合读取所有 head：

$$P(Y\mid X)=D_\phi\left(H^{(1)},\ldots,H^{(M)}\right)$$

所有 head 共用一个最终 seq2seq loss。没有“语法 head loss”“主题 head loss”或者人工分工。

完整研究计划考虑 $M\in\{1,2,4,8\}$。本次正式 Stage A 为控制守夜任务的变量和时间，只预注册并执行 $M\in\{1,2,4\}$；8 head 留待前三级出现收益以后再开放。如果增加 head 只增加参数，不改善验证集，就不能宣称多头有效。

### C. Flat sequence baseline

保留 token 顺序和相同 decoder，但 encoder 不使用父子地址、递归 FOLD 或 addressed detail。参数量和训练 FLOPs 应尽量与 TreeHeap 匹配。

### D. 小型 Transformer baseline

使用相同 tokenizer、训练数据和参数预算。它不是敌人，而是成熟的序列私有协议基线。

---

## 6. 最直接的私有协议检查

训练三个随机种子的 encoder-decoder 配对：

```text
(E1, D1)
(E2, D2)
(E3, D3)
```

首先测试原配：

```text
E1 -> D1
E2 -> D2
E3 -> D3
```

然后交换 decoder：

```text
E1 -> D2
E1 -> D3
E2 -> D1
...
```

如果原配工作、交换后明显退化，说明 encoder 与 decoder 形成了互相兼容但不必相同的内部协议。这个实验不能证明协议具有人类语义，却能比观看某个向量的 cosine 更直接地测量“双方是否共同写成了一套编码”。

如果交叉配对也能工作，也不是坏事。它说明架构和数据诱导出了跨 seed 相近的协议。此时再通过权重匹配或小型 adapter 判断它是公共坐标，还是可以被简单变换对齐。

---

## 7. 如何确认它真的用了 TreeHeap

仅有低 loss 不够，因为模型可能退化成普通数组协议。测试时保持参数不变，分别进行干预：

| 干预 | 测试问题 |
|---|---|
| 打乱 left/right 地址 | 协议是否依赖手性与地址 |
| 交换两个 subheap | 协议是否依赖子结构位置 |
| root 清零或换样 | root 是否参与当前任务 |
| 逐层关闭 detail | decoder 是否递归使用不同深度 |
| 单独关闭每个 head | 哪些 head 对最终结果有因果贡献 |
| 全部 head 只留一个 | 多头收益是否来自组合，而非单个幸运 head |
| 禁止 decoder 读取原始 token | 排除 string 旁路 |

记正常 loss 为 $L_0$，干预后的 loss 为 $L_I$：

$$\Delta L_I=L_I-L_0$$

只有当结构干预稳定产生正的 $\Delta L_I$，才能说对应结构参与了协议。

但我们仍然不能把它翻译成“这个 head 学会了宾语”。因果参与和人类语义解释是两件事。

---

## 8. 什么叫多 head 真正有效

多 head 不能只比较最终最好的一个数字。至少要同时报告：

1. **任务质量**：NLL、token accuracy、BLEU 或目标任务指标；
2. **训练效率**：达到同一验证 NLL 需要多少 token、step 和 GPU 时间；
3. **参数效率**：相同参数量下谁更好；
4. **稳定性**：至少三个 seed 的均值、标准差和失败尾部；
5. **head 因果性**：逐 head 消融造成多少损失；
6. **组合收益**：完整多头是否优于最佳单 head；
7. **结构收益**：TreeHeap 是否优于 matched flat 和 Transformer。

我们此前讨论过“head 只向前优化”。需要谨慎：非负 gate 或 ReLU 不能自动保证最终 loss 单调下降。第一轮实验不把这个性质写成事实。它只测量多个私有 kernel 是否产生稳定的组合收益。若出现 head 干扰，再单独预注册带 line search、trust region 或阶段式 boosting 的单调更新实验。

---

## 9. 判决表

### 支持

满足以下条件，Claim 才获得支持：

```text
1. 多 head TreeHeap 在多个 seed 上稳定训练；
2. 完整模型优于最佳单 head，而不是只靠一个 head；
3. 地址、subheap、深度干预造成可重复损失；
4. decoder 没有原始 token 或 flat memory 旁路；
5. 在匹配预算下，相对 flat 至少出现一项稳定收益：
   任务质量、收敛速度、参数效率或结构外推。
```

### 部分支持

如果结构干预有效，但任务分数仍低于 flat/Transformer，则结论只能是：

> TreeHeap 私有协议真实存在并使用了结构，但当前实现尚无竞争优势。

### 拒绝或降级

出现以下结果应当降级：

```text
地址打乱几乎不影响输出；
多 head 等于或差于最佳单 head；
收益完全来自参数量增加；
decoder 通过 leaf/string 旁路完成任务；
TreeHeap 在匹配预算下持续落后且没有外推或效率收益。
```

负结果也有价值。它会告诉我们问题究竟在多头组合、训练优化，还是 TreeHeap 归纳偏置本身。

---

## 10. 正式实验怎样运行

正式实验已经在 `io` 的 RTX 3090 上完成。训练本体耗时 8762.91 秒，约 2 小时 26 分钟。

| 项目 | 设置 |
|---|---|
| 数据 | WMT massive 英文到中文真实平行语料 |
| 训练 / 验证 / 测试 | 30,000 / 2,000 / 2,000 对 |
| 随机种子 | 71901、71902、71903 |
| 训练轮数 | 每个模型 4 epoch |
| 对比模型 | flat、TreeHeap h1、h2、h4 |
| 总协议宽度 | 固定为 64，head 越多，每个 head 越窄 |
| 参数量 | 全部约 2730 万到 2760 万 |
| 训练监督 | 只有最终英文到中文交叉熵 |

这里的固定总宽度很重要。h4 不是偷偷使用四倍内存，而是把同一份 64 维通信预算拆成四份。这样才能测试“多个私有协议 head 的组合”本身是否有价值。

原始 Stage A 没有加入 Transformer。原因不是回避对比，而是预注册时规定先选择 TreeHeap 内部的 winner。正式结果出来后，我们接受读者提出的异议：flat GRU 只是最低可行基线，不能代表成熟架构。因此又独立预注册并执行了 C02 小型 Transformer reality check。它作为追加实验单独判决，不倒过来修改 Stage A 的门槛。

---

## 11. 第一张体检表：任务质量

NLL 是模型给正确答案分配概率的代价，**越低越好**。BLEU-4 衡量生成文本和参考译文的局部词序重合，**越高越好**。

| 模型 | 参数量 | NLL ↓ | BLEU-4 ↑ | 每个 seed 平均训练时间 |
|---|---:|---:|---:|---:|
| flat | 27,421,377 | **6.0401** | **5.3530** | **111.6 秒** |
| TreeHeap h1 | 27,619,714 | 6.1231 | 4.9719 | 405.4 秒 |
| TreeHeap h2 | 27,435,395 | 6.1341 | 5.2892 | 775.6 秒 |
| TreeHeap h4 | 27,343,237 | 6.1934 | 5.0853 | 1552.2 秒 |

这张表给出两个明确的阴性结果：

1. h4 没有优于 h1。h4 的 NLL 反而高了 0.0703；
2. h4 没有优于 flat。h4 的 NLL 高了 0.1533，而且当前实现约慢 13.9 倍。

BLEU-4 也没有反转这个判断。四种模型的 BLEU 都只有约 5 分，说明这仍是研究级小训练，不是可用的翻译产品。flat 在本轮依然最好。

因此，预注册的“多头带来收益”和“TreeHeap 击败 flat”都失败了。这个结果不能改写成胜利。

---

## 12. 加测小型 Transformer：结果出现反转

追加实验沿用完全相同的 WMT 切分和三个 seed。Transformer 使用 2 层 encoder、2 层 decoder、4 个 attention head、256 维状态和 512 维前馈层，共 `27,278,337` 个参数，与 TreeHeap h1 只差 `1.236%`。

我们运行了两种配方：

```text
same recipe：和旧实验相同，4 epoch、AdamW、固定 lr=0.002
standard recipe：8 epoch、warmup、cosine decay、dropout=0.1、label smoothing=0.1
```

结果如下：

| 模型 | NLL ↓ | BLEU-4 ↑ | 每个 seed 平均训练时间 |
|---|---:|---:|---:|
| flat GRU | **6.0401** | **5.3530** | 111.6 秒 |
| TreeHeap h1 | 6.1231 | 4.9719 | 405.4 秒 |
| Transformer same recipe | 6.4423 ± 0.0062 | 2.9422 ± 0.1529 | **52.2 秒** |
| Transformer standard recipe | 6.5330 ± 0.0043 | 2.8941 ± 0.1916 | 100.8 秒 |

这一次 TreeHeap h1 明显胜过两个小 Transformer：

```text
相对 same-recipe Transformer：NLL 优势 0.3192
相对 standard-recipe Transformer：NLL 优势 0.4099
BLEU-4 优势：约 2 分
```

因此，“TreeHeap 只是在树上更慢地实现一个更差模型”这个最悲观判断，没有得到这次小 Transformer 实验的支持。至少在 30K 数据和约 27M 参数下，TreeHeap 的任务质量处于 flat GRU 与小 Transformer 之间。

但这里绝不能偷换成“TreeHeap 达到了 Transformer top model”：

1. flat GRU 仍然是质量第一名；
2. TreeHeap h1 比 flat 慢约 3.63 倍，比 same-recipe Transformer 慢约 7.77 倍；
3. 所谓 standard recipe 反而比 same recipe 差，说明它不是已经调到最优的强基线；
4. standard Transformer 到第 8 epoch 时验证 NLL 还在下降，尚不能声称收敛；
5. 本轮没有公开强 checkpoint，也不是标准榜单测试。

所以 C02 的窄结论是：

> **TreeHeap 通过了本次约 27M 小 Transformer 对照，但仍未达到“行业 top model”证明标准。**

---

## 13. 第二张体检表：它到底有没有使用 TreeHeap

任务分数没有赢，不代表 TreeHeap 一定没被使用。我们保持模型参数不变，只破坏 H_state 的某一部分，再观察 NLL 增量：

$$\Delta L=L_{\text{intervention}}-L_{\text{normal}}$$

$\Delta L$ 越大，说明被破坏的部分对输出越重要。

| 干预 | NLL 损伤 | 解释 |
|---|---:|---|
| 打乱输入样本 | +1.9532 | decoder 明显依赖 encoder 输入 |
| 交换 root | +2.1113 | root 是强因果通道，不是摆设 |
| 逐深度打乱 detail | +0.0187 到 +0.2577 | 6 层中 5 层超过预注册的 0.02 门槛 |
| 逐深度破坏 FOLD 配对 | 约 0 到 +0.5220 | 6 层中 5 层具有明显因果作用 |
| 分别关闭四个 head | +0.0554 到 +0.0874 | 四个 head 都参与了输出 |

这说明模型没有把 TreeHeap 当作一个空壳：root、多个 detail 深度、多个 parent-child 配对以及所有四个 head 都进入了最终预测。

但也有一个值得注意的边界：最深的一层 detail 和 pairing 几乎没有作用。不能说“整棵树每一层都被充分利用”。当前协议使用了大量结构，但利用并不均匀。

更有意思的是，**四个 head 每个都有效，四头整体却没有胜过一头**。这意味着“有因果贡献”和“组合后更优秀”不是同一件事。可能的原因包括：

- 固定 64 维被拆成四份后，每个 head 容量太窄；
- 四个 head 学到的是部分冗余协议；
- 当前拼接式 decoder 能读取每个 head，却不会高效组合它们；
- 递归 TreeHeap 的计算成本远高于当前 flat 实现。

这些只是下一轮假设，还不是本轮证明。

---

## 14. 第三张体检表：encoder 和 decoder 是否形成私有配对

三个 seed 分别训练出了三对 encoder 和 decoder。原配正常使用，然后把不同 seed 的双方交叉连接。

| 交换方式 | 相对 decoder 原配的 NLL 损伤 |
|---|---:|
| E71901 → D71902 | +4.2754 |
| E71901 → D71903 | +2.6694 |
| E71902 → D71901 | +4.2958 |
| E71902 → D71903 | +3.2091 |
| E71903 → D71901 | +2.2507 |
| E71903 → D71902 | +3.3085 |

六次交换全部严重退化，中位损伤约为 +3.2588 NLL。这支持一个窄而明确的判断：每次训练都形成了 encoder 和 decoder 彼此兼容的私有坐标，另一组 decoder 不能直接读懂。

但跨 seed 不兼容并不是 TreeHeap 独有的超能力。普通神经网络也可能因为隐空间旋转或置换而不能直接交换模块。本轮真正有价值的是两类证据同时出现：

```text
交叉配对失败：说明 encoder 与 decoder 共同形成了协议；
TreeHeap 干预有效：说明该协议实际经过 root、detail 和递归配对结构。
```

两者合起来，才支持“结构化 TreeHeap 私有协议存在”。它仍然不证明协议具有可读语义，更不证明 TreeHeap 优于其他神经网络。

---

## 15. 预注册判决

| Gate | 结果 | 判决依据 |
|---|---|---|
| P1：所有 head 可训练 | 通过 | 梯度有限，所有 TreeHeap head 都收到梯度 |
| P2a：h4 优于 h1 | **失败** | 6.1934 高于 6.1231 |
| P2b：每个 h4 head 都有用 | 通过 | 四次消融均造成损失 |
| P3：TreeHeap 结构具有因果作用 | 通过 | root、detail、pairing、head 干预通过门槛 |
| P4：形成私有或共享协议 | 通过 | 跨 seed 损伤远高于 0.10，属于 seed 私有协议 |
| P5：h4 优于 flat | **失败** | 6.1934 高于 6.0401 |

按照实验前写死的规则，最终状态只能是：

> **Partial：TreeHeap 私有协议真实存在，并且因果依赖其递归结构；但多头组合收益和相对 flat 的性能优势没有成立。**

这不是“平局”。从机制问题看，我们获得了阳性证据；从竞争性能看，TreeHeap 输掉了本轮。

当前最合理的下一步，不是立刻增加更多 head 或扩大语料，而是先定位多头退化：比较固定每头宽度与固定总宽度、测量 head 表征冗余，并替换当前简单拼接读取。只有 h2/h4 稳定优于 h1，才值得进入 Transformer Stage B。

完整 ARA 证据位于：

```text
ara/s3-generation/evidence/s3_private_protocol_battle_full/
```

三个 checkpoint 已归档到 NAS。原始日志、每 seed 结果、结构干预和交叉配对结果均保留，没有因为竞争预测失败而删除。

---

## 16. 为什么这次不再走迷宫

这一轮只回答一个问题：

> **已经能够形成的 TreeHeap 私有协议，在真实 seq2seq 任务上到底有没有本事？**

不再同时讨论意识、语法标签、最低熵句子、人类可读 root、世界模型拓扑和有限比特压缩。那些问题可以保留，但不能继续挤进同一个实验。

实验结束后，我们只允许三种结论：

```text
赢：TreeHeap 在公平指标上出现稳定优势，并且结构干预证明优势来自 TreeHeap。

平：TreeHeap 能工作且确实使用结构，但没有超过成熟基线。

输：TreeHeap 的结构没有被使用，或者使用以后仍持续降低任务能力。
```

协议内部可以保持沉默。结果必须公开说话。
