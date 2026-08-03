---
title: "[SPR-077·论文特别篇一] TreeHeap 为什么不是把数组画成一棵树"
date: 2026-08-02
lastmod: 2026-08-02
weight: 77
author: Houming818 & Codex Review
description: "TreeHeap 论文导读第一篇：从路径语义、张量位权、概率容器和 root-only 等失败出发，解释最终算法为什么必须拥有可逆状态、稀疏通信和递归读取。"
tags: [SPR, TreeHeap, Paper, ARA, Research, Reversible, PrivateProtocol]
---

# TreeHeap 为什么不是把数组画成一棵树

> **系列定位：TreeHeap 论文特别篇（1/4）。**
>
> 当前最可靠的结论是：TreeHeap 已成为一种可训练、可逆、可干预的多分辨率状态结构。它还没有证明语义地址、真正压缩、计算优势或产品级生成。

## 特别篇导航

1. **本篇：问题、失败与设计演化**
2. [数学与数据流：一个句子怎样进入 TreeHeap](/spr/078-treeheap-paper-math-and-dataflow.html)
3. [实验证据：三种子 WMT 与双向 Dreams](/spr/079-treeheap-paper-evidence-and-dreams.html)
4. [边界与复现：哪些成立，哪些仍然开放](/spr/080-treeheap-paper-boundaries-and-reproduction.html)

完整中文论文保存在开放仓库：

```text
https://github.com/houming818/sametime/blob/main/ara/papers/treeheap_emergent_protocol.zh.md
```

## 1. TreeHeap 最初在问什么

普通序列模型把临时状态排成一列。TreeHeap 想问一个不同的问题：

> 如果模型的临时状态本身具有 root、parent、child、leaf、路径和子堆，任务梯度能不能利用这些结构形成 Encoder 与 Decoder 都能读写的协议？

这里的关键词是“利用”，不是“摆放”。

把下面的数组：

```text
[a, cat, is, eating, some, food]
```

换成下面的图：

```text
              root
            /      \
        subtree   subtree
        /   \      /   \
       ...  ...   ...  ...
```

并不能自动产生语言理解。若所有计算最后仍把节点重新摊平成数组，树只是一张示意图。

TreeHeap 必须证明至少三件事：

1. 树上的运算在数学上成立；
2. 模型训练时真的使用了地址、深度和子结构；
3. 使用这些结构后，任务指标发生可重复变化。

## 2. 第一次误区：路径不是语义

早期 TreeHeap 的路径由 token ID 决定。两个 token 路径拥有较长公共前缀，看起来很像“它们属于同一个结构”。

但同一个 `bank` 可以表示银行，也可以表示河岸；同一个 `cat` 在不同句子中也可能处于不同关系。token ID 没变，路径就不会变。

所以路径只能回答：

```text
这个状态放在哪里？
```

不能单独回答：

```text
这个状态在当前句子里是什么意思？
```

最终设计仍然保留地址，但不再把地址直接叫作语义。

## 3. 第二次误区：能区分排列，不等于知道正确排列

Houming818 用 `321` 与 `123` 提出了位权问题。数字顺序之所以有意义，是因为每个数字处于不同的位权基。

类比到句子，可以让 token 向量 $s_i$ 与角色基 $e_r$ 做外积：

$$ T=\sum_i s_i\otimes e_{r_i} $$

这样，`cat` 放进 SUBJECT 槽和 OBJECT 槽会得到不同张量。

实验确认：外积、拼接和非交换组合可以让不同排列得到不同表示。但是，如果我们在构造张量前已经知道 SUBJECT 和 OBJECT，结构答案其实已经被人写进去了。

因此必须区分：

| 问题 | 是否已经回答 |
|---|---|
| 两种排列能不能表示成不同状态 | 可以 |
| 正确排列会不会自然得到更低能量 | 没有稳定证明 |
| 任务梯度能不能自己学会选择结构 | 仍需模型完成 |

“可以区分”是表示能力，“知道选谁”才是学习能力。

## 4. 概率桶不是信息来源

项目还尝试过保留多个父节点候选：

```text
Parent A: 0.62
Parent B: 0.25
Parent C: 0.13
```

这可以避免信息不足时过早 `argmax`。但概率桶只能延迟丢失，不能创造节点状态中不存在的信息。

这个想法没有消失，而是改变了位置。最终 TreeHeap 不再维护人工 parent 候选，而是让 Decoder 在真实 root、internal node 和 leaf 之间递归分配读取概率。

## 5. 为什么世界模型 Claim 被降级

我们曾希望 TreeHeap 向量形成如下关系参考系：

```text
ball + foot -> football
ball + hand -> basketball
```

但是旧 checkpoint 的 TreeHeap 向量平均 cosine 一度达到约 `0.985`。不同状态几乎都指向同一个公共方向。去中心化后虽然还能看到部分差异，却没有得到稳定、跨样本迁移的关系方向。

因此，论文明确撤回一个过强说法：

> 向量之间有距离，不等于世界模型已经形成。

一个世界参考系至少要在新词组、新句子和困难负例上保持关系迁移。这个证据目前没有完成。

## 6. 信息抽水机为什么必须可逆

最简单的 parent 是两个 child 求和或平均：

$$ parent=\frac{left+right}{2} $$

它能缩小节点数量，却会混淆左右次序和子堆身份。Decoder 无法知道被平均掉的差异来自哪里。

Houming818 用“抽水机”描述目标：

```text
leaf 保存局部细节
parent 接收更大范围的信息
越靠近 root，观察范围越大
Decoder 需要时还能取回 detail
```

关键修正是 lifting：parent 保存更新后的 anchor，detail 保存预测残差。这样 FOLD 可以改变分辨率，UNFOLD 又可以恢复完整状态。

所以完整 TreeHeap 状态不是 root：

$$ H=\left(root,\ all\ details,\ masks\right) $$

## 7. 为什么还需要 Butterfly

纯二叉 FOLD 只能让相邻 leaf 先相遇。长度为 8 时，位置 0 和位置 7 必须经过多层 parent 才能交换信息。

最终方案在 FOLD 前加入 XOR-Butterfly：

```text
stage 0: (0,1) (2,3) (4,5) (6,7)
stage 1: (0,2) (1,3) (4,6) (5,7)
stage 2: (0,4) (1,5) (2,6) (3,7)
```

它不增加 leaf 数量，只改变每一轮谁和谁进行局部可逆通信。$N$ 个地址经过 $\log_2N$ 轮后获得全地址通信路径。

## 8. 最终算法不是一次灵感，而是一组失败留下的约束

| 失败 | 暴露的问题 | 最终修正 |
|---|---|---|
| token ID 路径直接解释语义 | 地址与上下文含义混淆 | 地址和语义学习分开 |
| 随机角色基张量 | 可区分不等于可选择 | 选择交给任务梯度 |
| parent 直接求和 | 左右和子堆身份丢失 | 保存 lifting detail |
| flat route 表 | 每种长度单独记忆 | 使用共享递归 kernel |
| geometry feature 泄漏 | 输入直接包含正确方向 | 只读取真实节点状态 |
| root-only Decoder | root 因果增强但 NLL 恶化 | 完整 $H$ 参与 READ |
| 局部相邻 FOLD | 长距离通信过深 | 加入固定容量 Butterfly |

这也是 TreeHeap 目前最朴素的研究态度：不是要求读者相信一个完整理论，而是公开每次错误如何缩小设计空间。

## 9. 本篇结论

TreeHeap 的目标不是把数组画成树。它要求：

```text
地址可计算
局部算子可共享
分辨率可变化
状态可逆
读取可递归
结构作用可干预
任务结果可复现
```

下一篇将不再讲研究历史，而是从一个输入句子开始，逐步说明 WRITE、Butterfly、FOLD、UNFOLD、READ 和交叉熵梯度到底如何连接。

> 下一篇：[TreeHeap 的数学与数据流](/spr/078-treeheap-paper-math-and-dataflow.html)

---

**License:** GPLv3。本文与代码允许阅读、复制、修改和分发；引用定量结论时请同时保留 Evidence 边界。
