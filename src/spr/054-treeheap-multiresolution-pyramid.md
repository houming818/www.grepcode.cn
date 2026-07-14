---
title: "[SPR-054] TreeHeap 多分辨率金字塔：root 看全局，子堆保存细节"
date: 2026-07-14
lastmod: 2026-07-14
weight: 54
author: Houming818 & Codex Review
description: "把语言折叠类比为图像缩放：冻结已经训练成功的 TreeHeap root compressor，用带地址的低维 detail code 逐层补回局部信息，并用率失真曲线验证它究竟是不是一种有效压缩。"
tags: [SPR, TreeHeap, ARA, S3, Multiresolution, Compression, Rate Distortion, Original Research]
---

# TreeHeap 多分辨率金字塔：root 看全局，子堆保存细节

先说这篇文章提出的新假设：

> TreeHeap 不应该强迫一个 root 无损背下整句话。更合理的设计是：root 保存全局轮廓，各层 subheap 保存逐步补回细节所需的低维编码。

这与缩小一张图片很像。

一张 `1024 x 1024` 的照片缩成 `64 x 64` 后，不可能保留每一根头发，但我们仍然可能看出：

- 画面里有没有人；
- 人站在哪里；
- 背景是房间还是街道；
- 整体颜色和轮廓是什么。

丢失的主要是细小纹理。

对于语言，TreeHeap 的叶子可以看成高分辨率数据，内部节点是中等分辨率，root 是最低分辨率的全局摘要：

```text
token leaves       原始高分辨率
local subheaps     局部短语与关系
upper subheaps     更大范围的组合
root               全局低分辨率表示
```

但这仍然只是类比。它是否真的成立，必须变成一个可以失败的实验。

---

## 1. 为什么现在提出这个问题

上一轮实验已经用完整中文语料训练了一个 TreeHeap root compressor。

输入是64个 token：

```text
x1, x2, ..., x64
```

TreeHeap 反复用共享的三槽 kernel 折叠相邻节点：

```text
[root, left, right]
```

最后只留下一个192维 root，由 decoder 预测下一个 token。

这次全量训练处理了：

```text
文档数             7,564,966
训练 block 数      38,251,247
news block        28,052,019
wiki block         4,375,165
web block          5,824,063
训练时间            7.94 小时
```

最终可用模型是四头无残差 TreeHeap：

| 指标 | 结果 |
|---|---:|
| 验证 NLL，越低越好 | 6.2365 |
| Top-1 | 11.96% |
| Top-5 | 23.29% |
| root variance | 0.05843 |

更重要的是，破坏左右地址配对后，NLL 增加了 `2.6252`。

这说明 root 不是普通词袋。它确实依赖 TreeHeap 的递归地址和左右配对，保存了某些有助于预测的全局信息。

但它没有回答另一个问题：

> root 丢掉了哪些细节？能否用少量、分层的补充信息把这些细节找回来？

---

## 2. 不要让 root 背诵整句话

假设每个 token 是192维，64个 token 一共需要：

$$
64 \times 192 = 12288
$$

个浮点数。

如果把它们压成一个192维 root，容量只剩原来的：

$$
\frac{192}{12288}=1.56\%
$$

这显然是强压缩。

强压缩不等于错误。问题在于任务需要什么。

如果任务只是判断“大致在说吃饭还是旅行”，root 也许已经够用；如果任务是逐词 echo、翻译人名或还原数字，root 就可能丢失关键细节。

因此我们不再要求：

```text
一个 root = 完整句子
```

而改成：

```text
一个 root        = 全局摘要
多层 detail code = 折叠时丢失的局部细节
```

---

## 3. 新的数据结构长什么样

对于左右两个子节点：

$$
L,\;R \in \mathbb{R}^{192}
$$

已经训练好的 TreeHeap fold kernel 生成父节点：

$$
P=D_\theta(L,R)
$$

这里的 $D_\theta$ 是上一轮完整训练得到的模型。新实验会冻结它，不允许它继续变化。

然后增加一个细节编码器：

$$
d=Q_\phi(L,R,P),\qquad d\in\mathbb{R}^{k}
$$

其中 $k$ 比192小很多，例如8、16、32或64。

解码器读取父节点和细节：

$$
(\hat L,\hat R)=U_\psi(P,d)
$$

如果 $\hat L$ 和 $\hat R$ 接近原来的 $L$、$R$，说明：

```text
父节点 P          保存了公共、粗粒度信息
细节向量 d         保存了区分左右孩子所需的信息
```

完整节点可以写成：

```text
PyramidNode {
    coarse_state P
    detail_code  d
    left_address
    right_address
}
```

解码从 root 开始：

```text
root + 顶层 detail
  -> 两个较粗子节点

每个子节点 + 下一层 detail
  -> 四个更细节点

不断递归
  -> 尽可能恢复64个叶子
```

这就是 TreeHeap 多分辨率金字塔。

---

## 4. 这和普通残差有什么不同

普通残差通常写成：

$$
H_{t+1}=H_t+\Delta H_t
$$

它主要用于让旧状态和梯度穿过深层网络。

本文的 detail code 不直接加回同一个状态。它回答的是另一个问题：

> 把两个高分辨率孩子压成一个低分辨率父节点以后，重建孩子还缺少什么信息？

所以这里更接近图像的拉普拉斯金字塔或小波中的“低频摘要 + 高频细节”：

```text
coarse state   负责大轮廓
detail code    负责缺失差异
```

上一轮四头残差模型在 `step 62,400` 发生 NaN，已经否定了当时那个“无约束全局残差尺度”的实现。

新方案不会复用那个失败公式。它冻结成功的无残差 root encoder，只训练独立的 detail encoder 和 decoder。

---

## 5. 它真的压缩了吗

一棵64叶子的完全二叉树有63个内部节点。

如果只保存一个192维 root，并为每个内部节点保存 $k$ 维 detail，那么总容量是：

$$
R(k)=192+63k
$$

| detail宽度 $k$ | 总浮点数 | 原始容量占比 |
|---:|---:|---:|
| 0 | 192 | 1.56% |
| 8 | 696 | 5.66% |
| 16 | 1,200 | 9.77% |
| 32 | 2,208 | 17.97% |
| 64 | 4,224 | 34.38% |
| 原始叶子 | 12,288 | 100% |

例如 `k=32` 时，只使用原始激活量的约18%。

如果它已经能恢复大部分 token 和顺序，就出现了有价值的压缩；如果必须把 `k` 增加到接近192才能恢复，那么它虽然能编码，却没有明显压缩优势。

这里说的只是“浮点数数量”，还不是严格的比特压缩。只有完成量化、熵编码和实际文件大小测量后，才能讨论真正的 bit rate。

---

## 6. 新 Claim

新声明编号：

```text
S3-TREEHEAP-PYRAMID-C01
```

正式内容是：

> 一个冻结的 TreeHeap root compressor 可以扩展为多分辨率 codec：root 保存粗粒度、与任务相关的状态；每个内部地址保存有界的 detail code。随着 detail 容量增加，真实语料的重建质量应单调提高，同时冻结 root 的下一词预测能力保持不变。

当前状态：

```text
designed / experiment pending
```

它现在只是一个可检验的原创工程假设，不是实验结论。

---

## 7. Predict：成立时我们应该看到什么

### P1：root 的旧能力必须完全保留

冻结模型原来的验证 NLL 是：

```text
6.236525
```

新模块不能偷偷改写 root：

$$
|NLL_{new}-6.236525|<10^{-5}
$$

如果变化，说明代码存在旁路或错误。

### P2：细节越多，恢复应该越好

我们预测：

$$
E_{root}>E_8>E_{16}>E_{32}>E_{64}
$$

其中 $E$ 是叶子状态的重建误差。

对应的 token Top-1、Top-5和顺序恢复率应该反向单调上升。

### P3：形成清楚的率失真曲线

横轴是存储容量，纵轴是重建误差：

```text
容量小 --------------------> 容量大
误差大 --------------------> 误差小
```

detail容量与重建质量的 Spearman 相关性应至少达到 `0.9`。

### P4：有限容量必须带来明显收益

`k=64` 必须让 root-only 的重建 MSE 至少下降50%。

如果增加了大量细节却只改善一点点，说明当前 fold 已经过早破坏了信息。

### P5：TreeHeap 地址必须有用

打乱左右地址以后，至少满足一个条件：

```text
重建 MSE 增加 >= 10%
或
token accuracy 下降 >= 5 个百分点
```

### P6：不能只打败自己

在相同存储容量下，它还要比较：

- 固定平均池化金字塔；
- 固定 Haar 式平均/差分；
- flat autoencoder；
- 随机左右配对树。

只有 TreeHeap 在至少一个有效容量上击败这些对照，才能提出“TreeHeap具有更好率失真归纳偏置”的后续声明。

---

## 8. 实验怎样执行

第一轮不直接再跑八小时。

```text
真实语料 block       1,000,000
上下文长度            64 token
冻结 root encoder      四头无残差 checkpoint
detail k              0 / 8 / 16 / 32 / 64
随机种子               3
```

训练过程：

1. 读取冻结 TreeHeap；
2. 保存每层的 left、right、parent 状态；
3. 只训练 $Q_\phi$ 和 $U_\psi$；
4. 在未见过的 block 上递归重建；
5. 输出每个容量的率失真曲线；
6. 做地址破坏和逐层 detail 消融。

指标分开报告，不能只给一个“大锅 loss”：

| 指标 | 检查什么 |
|---|---|
| root next-token NLL | 全局预测能力是否被破坏 |
| leaf embedding MSE | 连续状态恢复 |
| token Top-1/Top-5 | 词面恢复 |
| sequence token accuracy | 整句恢复 |
| edit similarity | 顺序接近程度 |
| bag overlap | 内容是否回来 |
| position accuracy | 地址与次序是否回来 |
| floats/token | 付出了多少容量 |

---

## 9. Toy：为什么逐层细节有意义

考虑一句短句：

```text
the cat is eating rice
```

最低分辨率 root 可能只能表达：

```text
某个主体正在进行进食活动
```

加入顶层 detail 后，可能恢复：

```text
主体部分 | 动作与对象部分
```

继续加入更低层 detail：

```text
the cat | is eating rice
```

最后才恢复具体词面：

```text
the | cat | is | eating | rice
```

这不是说模型一定会形成这些人类语法标签。实验只检查一个更基础的事实：

> 不同层级是否真的以越来越大的容量，逐渐补回越来越细的信息。

如果没有这种渐进关系，“金字塔”就只是一个漂亮名字。

---

## 10. 什么结果会否定它

以下任一情况都会让 Claim 被拒绝或缩小：

1. 增加 detail 后，重建误差不单调下降；
2. 必须接近原始容量才能恢复；
3. 随机树和真实地址表现相同；
4. 平均池化或 flat autoencoder 在同容量下全面更好；
5. root NLL发生变化，说明实验偷偷改写了旧模型；
6. 所有层的 detail 完全可以互换，没有尺度分工。

失败不是“调参不够”。这些失败会直接告诉我们：

```text
当前 TreeHeap fold 不是合适的降采样核
或
语言信息不适合按当前地址形成多尺度编码
```

---

## 11. 哪些部分是我们的原创

为了避免把已有数学重新命名为自己的发明，这里明确划界。

已有公共理论包括：

- 多分辨率分析；
- 高斯与拉普拉斯图像金字塔；
- 小波与平均/差分分解；
- autoencoder；
- 信息论中的率失真理论。

我们不声称这些理论由 SameTime 发明。

本文的原创研究贡献是：

1. 把已经测得地址因果性的 TreeHeap root compressor 定义为冻结降采样核；
2. 设计“一个 root + 每个内部地址一个低维 detail code”的语言 TreeHeap codec；
3. 给出固定容量公式 $R(k)=192+63k$；
4. 设计 root 不回归、渐进恢复、地址破坏、同容量基线和层级消融；
5. 登记可证伪 Claim `S3-TREEHEAP-PYRAMID-C01` 及其数值门槛。

这是 SameTime 项目在现有数学基础上的原创架构假设与实验协议。截至本文发布时，它尚未通过实验，也不构成“世界首创”或专利新颖性检索结论。

---

## 12. ARA 与可复核材料

正式 ARA：

- [Multiresolution TreeHeap Pyramid](https://github.com/houming818/sametime/blob/main/ara/s3-generation/logic/multiresolution_treeheap_pyramid.md)
- [S3 Claims Registry](https://github.com/houming818/sametime/blob/main/ara/s3-generation/logic/claims.md)
- [上一轮全量实验分析](https://github.com/houming818/sametime/blob/main/ara/s3-generation/evidence/s3_residual_treeheap_forest/result_analysis.md)

任何后续文章都必须同时报告通过和失败的 Predict，不允许只展示最好的一条曲线。

---

## 版权、原创与许可证

Copyright (C) 2026 Houming818 and SameTime contributors.

本文由 Houming818 提出核心类比与研究方向，Codex Review 参与数学整理、ARA声明和实验协议编写。正文与伪代码为本项目原创表达，没有复制第三方论文正文、代码或插图；已有理论已在上一节明确列为公共学术背景。

> **SPDX-License-Identifier: GPL-3.0-only**  
> **License: GNU General Public License v3.0 only**

本文允许复制、修改和分发，但衍生版本必须继续遵守 GNU GPL v3，并保留版权、许可证、修改说明及来源声明。完整许可证文本见本站 [/LICENSE](/LICENSE)。

本文按“原样”提供，不附带任何明示或暗示担保。数学思想和事实本身不受版权垄断；本许可证适用于本文的原创文字、结构、表格、伪代码及其他可受版权保护的表达。

