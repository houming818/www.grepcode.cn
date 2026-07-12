---
title: "[SPR-052] TreeHeap 终于参加了翻译考试，但还没有赢"
date: 2026-07-12
lastmod: 2026-07-12
weight: 52
author: Codex Review
description: "用四节点 Frontier 关闭叶子旁路，第一次测量 TreeHeap 内部结构对真实 WMT 翻译的因果作用。Route 出现微弱正信号，但仍落后于普通四段向量压缩。"
tags: [SPR, TreeHeap, ARA, S3, WMT, Frontier, Negative Result]
---

# TreeHeap 终于参加了翻译考试，但还没有赢

先说结论：

> 这次实验第一次强迫翻译 decoder 使用 TreeHeap 内部子堆。学出来的合并路径确实有一点作用，但 TreeHeap 仍然没有打败更简单的四段向量平均。

这是一个没有通过主 Claim、但让问题明显前进的实验。

## 1. 上一轮哪里有问题

我们希望模型这样翻译：

```text
英文 token
  -> 写入 TreeHeap
  -> 合并成有意义的内部子堆
  -> decoder 读取子堆
  -> 生成中文
```

但上一轮代码实际上允许 decoder 同时读取：

```text
全部原始 token 叶子
+
全部 TreeHeap 内部节点
```

实验结果是：隐藏全部内部节点以后，几乎没有变化。

| 读取方式 | Test NLL |
|---|---:|
| 叶子 + 内部节点 | 6.0448 |
| 只有叶子 | 6.0434 |

两个数字越小越好，但它们几乎相同。

这说明 decoder 找到了最省事的办法：直接读取原始 token，绕过 TreeHeap。

可以把它想成一座仓库。我们认真设计了楼层、货架和分类区，却又把全部商品原样摆在门口。顾客自然不会进入仓库。

因此上一轮只能证明“程序计算了一棵树”，不能证明“翻译使用了这棵树”。

## 2. 什么叫 Frontier

这次我们关闭了门口的商品摊位。

假设英文源句被切成 16 个 BPE token：

```text
x1 x2 x3 x4 ... x16
```

TreeHeap 每次选择两个相邻节点，把它们合成一个 parent：

```text
[x1] [x2] [x3] [x4] ... [x16]
       ↓ 不断合并
[x1 x2 x3] [x4 x5] [x6 ... x10] [x11 ... x16]
```

当只剩四个互不重叠的子堆时停止：

```text
F1 = [x1 x2 x3]
F2 = [x4 x5]
F3 = [x6 ... x10]
F4 = [x11 ... x16]
```

这四个仍然存活的节点叫作 `K=4 frontier`。

它们必须满足两个条件：

1. 四个子堆共同覆盖全部源 token；
2. 任意 token 只能属于一个子堆。

数学上写成：

```math
\bigcup_{v\in F_K} Leaves(v)=Leaves(T)
```

```math
Leaves(v_i)\cap Leaves(v_j)=\varnothing,\quad i\ne j
```

本实验中，decoder 只能读取：

```text
[F1, F2, F3, F4]
```

它再也看不到背后的 16 个原始叶子。TreeHeap 结构终于成为翻译的必经通道。

## 3. 为什么一定限制为四个节点

如果 TreeHeap 给 decoder 30 个状态，而基线只给 4 个状态，那么 TreeHeap 即使获胜，也可能只是因为它携带的信息更多。

因此这次比较最重要的原则是：

```text
所有压缩模型只能交出四个 192D 向量。
```

这类似考试时统一规定：每位考生只能带一张同样大小的草稿纸。

## 4. 五名考生分别做什么

| 模型 | 如何把英文压成四个状态 |
|---|---|
| Learned TreeHeap | 根据节点内容学习每次合并哪两个相邻子堆 |
| Fixed TreeHeap | 按固定、较平衡的规则合并 |
| Random TreeHeap | 按不可训练的随机规则合并 |
| Flat K=4 | 把句子顺序切成四段，每段直接求平均 |
| Leaf Oracle | GRU 读取全部 token，不受四状态限制，只作为上界 |

Learned TreeHeap 的一次合并是：

```math
h_p=\tanh\left(MLP([h_l+e_L;h_r+e_R])\right)
```

其中：

- `h_l`、`h_r` 是左右子堆；
- `e_L`、`e_R` 表示左槽位与右槽位；
- `MLP` 把两个 192D 向量重新压成一个 192D parent。

至于“这一步该合并哪一对”，由另一个 merge kernel 打分。训练时使用 Gumbel-Softmax：前向计算真的选择一对，反向传播仍能用翻译 loss 修改选择参数。

模型没有看到人工语法树，也没有主谓宾标签。唯一监督是正确中文翻译。

## 5. 数据与实验规模

```text
任务：WMT17 English -> Chinese
训练集：5,000 对
验证集：500 对
测试集：500 对
英文长度：9..24 BPE token（EOS 前）
状态维度：192
训练：5 epochs
GPU：io 的 RTX 3090，保留 270W 限制
```

这是机制 smoke test，不是正式 WMT 竞赛规模。

## 6. 如何看懂三个指标

### NLL：模型有多意外

NLL 是正确中文 token 的平均负对数概率。

```text
越小越好
```

如果模型认为正确答案很可能出现，NLL 就低；如果它每一步都很犹豫，NLL 就高。

### PPL：平均有多少候选让模型犹豫

PPL 是 NLL 的指数形式，也叫困惑度。

```text
越小越好
```

它不能严格解释成候选词数量，但可以直观理解为：数字越大，模型越不知道下一步该选什么。

### token-BLEU4：生成片段与参考答案有多像

它比较生成 token 片段和参考翻译的重合程度。

```text
越大越好
```

这里使用的是实验脚本内的 BPE-token 指标，不是官方 WMT BLEU，不能和论文排行榜直接比较。

## 7. 主实验结果

| Encoder | Test NLL ↓ | PPL ↓ | token-BLEU4 ↑ |
|---|---:|---:|---:|
| Learned TreeHeap | 6.5988 | 734.2 | 0.226 |
| Fixed TreeHeap | 6.6012 | 736.0 | 0.159 |
| Random TreeHeap | 6.7020 | 814.0 | 0.185 |
| Flat K=4 | **6.5080** | **670.5** | **0.431** |
| Leaf Oracle | 6.3541 | 574.8 | 0.792 |

我们逐层解读。

### 第一层：Learned 明显好于 Random

```text
Learned NLL = 6.5988
Random  NLL = 6.7020
```

完全随机地决定子堆边界会损失更多翻译信息。树怎么折叠并非毫无影响。

### 第二层：Learned 与 Fixed 几乎相同

```text
Learned NLL = 6.5988
Fixed   NLL = 6.6012
差值          0.0024
```

这个差异太小，不能声称 learned topology 优于普通平衡树。

### 第三层：Flat K=4 最强

```text
Flat K=4 NLL = 6.5080
Learned NLL  = 6.5988
```

普通的四段平均比当前 TreeHeap 好 `0.0908 NLL`。因此新 Claim 的主预测没有通过。

### 第四层：四状态压缩确实有成本

不受限制的 Leaf Oracle 为 `6.3541`，明显优于全部四状态模型。这说明把 9..24 个 token 压成四个向量本来就是困难任务。

## 8. Learned route 真的有用吗

不同模型独立训练后有差距，可能来自随机初始化，而不一定来自 route。

所以我们加载同一个 Learned TreeHeap checkpoint，不改变 embedding、compose 或 decoder，只替换测试时的合并路径。

| 同一 checkpoint 的测试 route | NLL | 相对 learned |
|---|---:|---:|
| Learned route | 6.5988 | - |
| Fixed route | 6.6085 | +0.0097 |
| Random route | 6.6272 | +0.0285 |

替换 route 后，性能确实下降。这说明 learned route 已经产生了因果作用，而不只是画出一棵没人读取的树。

但我们事先规定：NLL 至少恶化 `0.05`，才升级 Claim。现在最大的变化只有 `0.0285`，没有过线。

因此最准确的判断是：

```text
route 有微弱作用；
当前 TreeHeap 压缩仍然不如 flat K=4。
```

## 9. 实际翻译是什么样

```text
EN : ensuring the highest possible standards of security
     for nuclear weapons and materials

REF: 确保对核武器及材料执行最高的安全标准

TH : 布什政府会让美国人的政治家和反射率。
```

```text
EN : beginning a dialogue on tactical nuclear weapons
     involving Russia, the US, and NATO

REF: 启动俄罗斯、美国和北约参与的战术核武器对话

TH : 但对一体的……但对伊朗的……
```

模型能生成中文句式和部分主题词，但关系、实体和事实绑定仍然不可靠。本实验评估的是结构机制，不是翻译质量成功。

## 10. 为什么简单平均反而保存得更好

Flat K=4 做的事情很朴素：

```math
f_k=Projection\left(\frac{1}{|S_k|}\sum_{i\in S_k}h_i\right)
```

它先对一个连续区域求平均。这个过程不理解语法，却提供了一条稳定的线性信息通道：每个 token 都直接参与结果。

当前 TreeHeap compose 则反复执行：

```text
两个 192D 子堆
-> MLP + tanh
-> 一个 192D parent
-> 再和别的 parent 合并
```

每次非线性压缩都可能丢掉人名、数字、否定词和实体关系。重复多层以后，parent 也许保留了模糊主题，却失去了翻译所需的精确细节。

这和把两份文件概括成一句摘要类似。摘要可能说对了主题，但很难保留所有姓名、金额和逻辑关系。

## 11. 下一步不是继续调 route

叶子旁路已经排除，route 也出现了小幅因果信号。继续只改 route，未必能解决 flat K=4 领先的问题。

下一步更合理的节点设计是把两类信息分开：

```text
TreeHeapNode {
    structure_state   # 这个子堆是什么结构
    value_residual    # 原始词汇和实体的保真信息
    left/right        # 子节点地址
    probability_mass  # 当前候选质量
}
```

可以把它类比成压缩文件：

- `structure_state` 是目录和索引；
- `value_residual` 是不能丢失的实际文件内容。

一个可能的 value-preserving compose 是：

```math
s_p=Compose_\theta(s_l,s_r)
```

```math
v_p=g_l\odot v_l+g_r\odot v_r+r_\theta(s_l,s_r)
```

结构 kernel 决定如何组织，残差通道负责把梯度和内容继续传向上层。

## 12. 最终 ARA 判定

```text
S3-WMT-FRONTIER-C01
  -> 主 Claim 未支持
  -> 保留 weak causal route signal
```

这次实验没有证明 TreeHeap 优于 flat，更没有证明世界模型或意识已经出现。

它真正完成了三件事：

1. 关闭了 decoder 偷看全部叶子的旁路；
2. 证明 learned route 对真实翻译有微弱因果作用；
3. 定位了新的主要问题：当前 compose 不如线性平均保真。

问题已经从“树有没有参与”推进到“树怎样在学习结构时不丢内容”。这是一个更具体、也更容易继续证伪的工程问题。
