---
title: "[SPR-078·论文特别篇二] 一个句子怎样进入 TreeHeap：数学、参数与数据流"
date: 2026-08-02
lastmod: 2026-08-02
weight: 78
author: Houming818 & Codex Review
description: "用本科线性代数与概率论解释 TreeHeap 的 theta、H、WRITE、可逆 Butterfly、lifting FOLD/UNFOLD、递归 READ 和交叉熵梯度。"
tags: [SPR, TreeHeap, Paper, Mathematics, Lifting, Butterfly, Encoder, Decoder]
---

# 一个句子怎样进入 TreeHeap

> **系列定位：TreeHeap 论文特别篇（2/4）。**
>
> 本篇只解释当前代码真实执行的数学过程，不把内部节点命名为主语、谓语、摘要或世界模型。

## 系列导航

1. [问题、失败与设计演化](/spr/077-treeheap-paper-origin-and-evolution.html)
2. **本篇：数学、参数与数据流**
3. [三种子 WMT 与双向 Dreams](/spr/079-treeheap-paper-evidence-and-dreams.html)
4. [边界、否证条件与复现](/spr/080-treeheap-paper-boundaries-and-reproduction.html)

## 1. 先区分参数与状态

回归方程：

$$ y=wx+b $$

里面的 $w,b$ 是长期学习参数，$x$ 是当前输入，$y$ 是当前输出。

TreeHeap 也必须做同样区分。

共享参数记作 $\theta$：

$$ \theta=\{embedding,Butterfly,FOLD,READ,GRU,output\} $$

它们保存在 checkpoint 中，被全部训练样本共同使用。

一个具体句子 $x$ 经过这些参数后，形成临时状态：

$$ H_\theta(x)=\left(root_x,details_x,masks_x\right) $$

$H_\theta(x)$ 随句子改变，不是另一份模型参数。

可以这样理解：

```text
theta：长期形成的读写规则
H(x)：这套规则对当前句子的实例化
```

## 2. WRITE：把离散 token 写入 leaf

输入由三部分组成：

```text
[direction token] + [SentencePiece pieces] + [EOS]
```

例如中译英方向的第一个 leaf 会写入 `zh2en` 特殊 token，后续 leaf 才是原句 pieces。

对有效位置：

$$ x_i=E_{src}(w_i) $$

当前实现没有额外的位置 embedding。位置差异来自：

1. leaf 下标；
2. Butterfly 中由地址决定的配对；
3. 二叉 FOLD 中不同的左右路径。

不足容量的位置由 mask 关闭。WRITE 只完成离散到连续向量的映射，还没有自动产生高层语义。

## 3. Butterfly：固定容量内的长距离通信

设 TreeHeap 有 $N=2^D$ 个 leaf。第 $s$ 轮中，地址 $i$ 与地址

$$ j=i\oplus2^s $$

通信。

一对状态 $(a,b)$ 的可学习 kernel 为：

$$ b'=b+\alpha_s\tanh(F_\theta(a)) $$

$$ a'=a+\alpha_s\tanh(G_\theta(b')) $$

这里 $F_\theta,G_\theta$ 是共享的小型非线性网络。所有地址使用同一套 kernel，不为每一对节点单独学习一张表。

逆运算按相反顺序计算：

$$ a=a'-\alpha_s\tanh(G_\theta(b')) $$

$$ b=b'-\alpha_s\tanh(F_\theta(a)) $$

所以 Butterfly 可以改变坐标，又不要求丢失输入。

每轮有 $N/2$ 对，共有 $\log_2N$ 轮：

$$ \text{pair operations}=\frac{N}{2}\log_2N $$

这是 $O(N\log N)$ 的稀疏通信，不分配 $N\times N$ 的稠密注意力矩阵。

## 4. FOLD：把两个 child 组织成 parent 与 detail

Butterfly 之后，TreeHeap 开始逐层 FOLD。对于左右状态 $(l,r)$：

$$ d=r-P_\theta(l) $$

$$ p=l+U_\theta(d) $$

其中：

- $P_\theta$ 预测右侧状态；
- $d$ 保存没有被预测到的残差；
- $U_\theta$ 决定残差怎样更新到 parent；
- $p$ 进入更高一层。

当前 Update 为：

$$ U_\theta(d)=0.5d+0.5\tanh(\widetilde U_\theta(d)) $$

可学习部分从零初始化。训练开始时，它等价于稳定的 $0.5d$ 更新；训练随后可以改变信息如何向 parent 上导。

## 5. UNFOLD：为什么它能恢复 child

已知 parent $p$ 与 detail $d$：

$$ l=p-U_\theta(d) $$

再计算：

$$ r=d+P_\theta(l) $$

就能恢复左右状态。

递归执行后，$N$ 个 leaf 被组织为：

```text
1 个 root
+ 第 0 层 details
+ 第 1 层 details
+ ...
+ masks
```

detail 总数仍为 $N-1$。因此当前多分辨率状态不是文件压缩：信息只是被重新组织，并没有自动减少存储量。

## 6. READ：Decoder 如何决定读取哪个深度

Decoder 每生成一个 token，都从 root 开始分配概率质量。

对节点 $n_i^{(k)}$，计算停止概率：

$$ p_{stop}(i,k,t)= \sigma\left(S_\theta\left[q(h_t),n_i^{(k)}+e_k\right]\right) $$

如果不停止，剩余质量进入左右 child：

$$ p(c\mid i,t)= \operatorname{softmax}_c \left(\frac{B_\theta(h_t)^\top n_c}{\sqrt m}\right) $$

到达节点 $i$ 的质量为 $m_i$ 时：

$$ m_i^{stop}+m_{left}+m_{right}=m_i $$

所以概率没有在递归过程中凭空增加。所有停止节点的加权和形成当前上下文 $c_t$。

## 7. Decoder 如何生成下一个 token

Decoder 把上一个目标 token、当前 TreeHeap context 和历史隐状态放进 GRU：

$$ h_{t+1}=GRU([E_{tgt}(y_t),c_t],h_t) $$

再输出词表概率：

$$ p(y_{t+1})=softmax(W_o[h_{t+1},c_t]) $$

训练时使用 teacher forcing：第 $t$ 步输入真实的 $y_t$。自由生成时，输入模型自己上一步选择的 token。

## 8. 梯度到底从哪里来

唯一语言目标是目标 token 的交叉熵：

$$ \mathcal L=-\sum_t\log p_\theta(y_t\mid y_{<t},H_\theta(x)) $$

如果正确 token 的概率太低，loss 就升高。反向传播依次经过：

```text
词表输出
  -> GRU
  -> recursive READ
  -> UNFOLD levels
  -> root + details
  -> lifting FOLD
  -> Butterfly
  -> source embedding
```

这条链就是私有协议形成的物理通道。模型没有内部节点标签，也没有人工告诉它哪个 node 是“食物”或者“主语”。

## 9. 这套结构哪里是确定的，哪里是学习的

| 类型 | 内容 |
|---|---|
| 确定性结构 | heap 地址、XOR 配对轮次、FOLD/UNFOLD 计算顺序、概率质量守恒 |
| 可学习参数 | embedding、Butterfly kernel、Predictor、Update、stop、branch、GRU、输出层 |
| 样本临时状态 | leaf、root、details、READ context |
| 最终监督 | 目标 token 交叉熵 |

这一区分很重要。Butterfly 地址图是人工给定的归纳偏置；具体传递什么信息由梯度学习。FOLD 的逆式由数学定义保证；不同深度最后承担什么任务，必须由实验观察。

## 10. 当前计算代价

Butterfly 是 $O(N\log N)$，FOLD/UNFOLD 是 $O(N)$。当前 recursive READ 每个输出时间步会访问总计小于 $2N$ 个节点，所以生成约为：

$$ O(TN) $$

其中 $T$ 是输出长度。

因此，“稀疏”目前只是结构性质，不等于工程上已经更快。是否节省 GPU 小时，必须用吞吐、显存和训练成本实际测量。

## 11. 本篇结论

一个句子进入 TreeHeap 后，没有被压成一个神奇 root。它经历的是：

```text
WRITE
-> Butterfly communication
-> reversible FOLD
-> H(root, details, masks)
-> recursive READ
-> token distribution
-> cross-entropy gradient
```

下一篇将检查这条链到底产生了什么证据，以及哪些漂亮数字其实不能被解释得太强。

> 下一篇：[三种子 WMT 与双向 Dreams](/spr/079-treeheap-paper-evidence-and-dreams.html)

---

**License:** GPLv3。
