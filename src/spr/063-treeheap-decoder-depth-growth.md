---
title: "[SPR-063] TreeHeap 分辨率协议重审：递归抽水、细节残差与递归解码"
date: 2026-07-18
lastmod: 2026-07-19
weight: 63
author: Houming818 & Codex Review
description: "公开撤回一次把多层变长数组误称为 TreeHeap 递归解码的实验解释，并重新定义 TreeHeap 的分辨率、递归、残差和抽水协议。"
tags: [SPR, TreeHeap, ARA, Decoder, Recursion, Residual, Lifting Scheme, Multiresolution]
---

# TreeHeap 分辨率协议重审：递归抽水、细节残差与递归解码

> 本文记录一次重要纠错。旧版 SPR-063 设计了所谓“递归深度剂量实验”，但代码审计发现，decoder 实际读取的是长度为 1、2、4、8 等的平铺数组。它没有沿 TreeHeap 地址移动，也没有读取父子边。因此，已经完成的实验不能否定 TreeHeap 的深度假设，只能否定这种多分辨率 flat READ。

本文的核心概念由 Houming818 提出：信息应当像抽水机一样从 leaf 逐层退火到 root；这个过程必须递归。Codex Review 负责检查代码是否真的保存了这些概念，并把它整理成下一轮可证伪实验。

---

## 1. 先说结论：旧实验测错了对象

旧代码的 encoder 确实执行了递归 FOLD：

```text
leaf
  -> FOLD 得到上一层 parent
  -> 再用这些 parent 做下一次 FOLD
  -> 一直得到 root
```

如果记 leaf 为 $H_D$，那么：

$$
H_{d-1}=F_\theta(H_d),\qquad d=D,D-1,\ldots,1
$$

同一个 $F_\theta$ 在不同深度重复调用。这部分是真递归。

但 encoder 随后把树转换成了一个列表：

```text
levels = [
  [root],
  [depth-1 的所有节点],
  [depth-2 的所有节点],
  ...,
  [所有 leaf]
]
```

每一层只剩一个形状为 `[batch, width, dim]` 的张量。parent、children、left、right、stop、path 和 span 都没有交给 decoder。

旧 READ 做的是：

$$
q_{d+1}=R_\phi(q_d,\,[h_{d,1},h_{d,2},\ldots,h_{d,n_d}])
$$

其中方括号只是当前层的平铺数组。`dose` 增加一层，本质上只是再读取一个不同长度的数组。

因此旧实验的准确名称应当是：

> 递归池化产生的多分辨率数组实验。

它不是 TreeHeap 递归 decoder 实验。

---

## 2. 为什么“用树算出节点”还不等于“使用了树”

考虑这棵树：

```text
             A
          /     \
         B       C
        / \     / \
       1   2   3   4
```

递归 encoder 计算：

```text
B = FOLD(1, 2)
C = FOLD(3, 4)
A = FOLD(B, C)
```

如果 decoder 最后只收到：

```text
[A]
[B, C]
[1, 2, 3, 4]
```

它并不知道：

```text
1、2 属于 B
3、4 属于 C
B、C 属于 A
```

它只能把每一层当作集合或数组进行 attention pooling。

这解释了守夜实验的异常结果：

| 指标 | 结果 |
|---|---:|
| Tree 多层数组 NLL | 6.2366 |
| Random 多层数组 NLL | 6.2361 |
| Flat pooling NLL | 5.9311 |
| 所谓“打乱链接”的 NLL 变化 | 0.00000021 |

数字没有证明 TreeHeap 拓扑无效，因为拓扑从未进入 READ。所谓 `shuffled_links` 也只是重新生成了另一组池化数组，并没有在保持节点值不变时修改 decoder 正在遍历的边。

因此 ARA 状态必须修正为：

```text
不是：TreeHeap depth claim 被否证
而是：该实验没有测试到 TreeHeap depth claim
```

---

## 3. 分辨率到底是什么

我们先不要求 root 能翻译成人类可读的缩句。encoder 和 decoder 可以形成私有编码。

这里的分辨率是一个操作定义：

```text
root                  最少状态，最大覆盖范围
root + 第一层 detail  更多局部信息
继续展开              更高分辨率
全部 leaf/detail      最高表面精度
```

它类似一张图片：缩略图保留大体结构，放大后补充纹理。但语言不是天然平滑的像素平面，所以我们不能直接宣称 root 一定保存“主语、谓语、宾语”或者一条可读摘要。

我们真正要验证的是：

1. parent 是否保存了对多个 children 都有用的公共状态；
2. child/edge 是否保存了 parent 无法预测的细节；
3. 增加细节后，decoder 是否沿同一棵树递归改善；
4. 破坏地址和父子关系后，这种改善是否消失。

---

## 4. 抽水机不能只是加权平均

旧 FOLD 大致是：

```text
children
  -> slot embedding
  -> MLP
  -> softmax 加权平均
  -> parent
```

它可以把多个 child 压成一个 parent，但没有说明哪些信息上传、哪些信息留在原处。连续多次压缩后，信息可能只是被混合和扭曲。

更完整的抽水过程应当同时产生两类量：

```text
coarse：上传给 parent 的公共轮廓
detail：留在 child 或 edge 上的预测残差
```

定义 children 为 $c_1,\ldots,c_k$。先计算 parent：

$$
s_p=U_\theta(c_1,\ldots,c_k)
$$

再由 parent 和 slot 预测每个 child：

$$
\hat c_j=P_\phi(s_p,e_j)
$$

细节残差为：

$$
r_j=c_j-\hat c_j
$$

于是 child 可以恢复为：

$$
\tilde c_j=P_\phi(s_p,e_j)+r_j
$$

这里的 `coarse` 被抽到 parent，`detail residual` 没有硬塞进 root，而是保存在对应的边上。

---

## 5. 这与小波 lifting scheme 有什么关系

这套结构不是凭空发明。小波的 lifting scheme 使用 `split -> predict -> update` 构造多分辨率表示：一部分数据形成低分辨率近似，另一部分记录预测失败产生的 detail。保留全部 detail 时可以精确恢复；逐步丢弃 detail 时得到逐级降低的分辨率。

对 TreeHeap，可以作如下对应：

| Lifting scheme | TreeHeap |
|---|---|
| split | 把节点分为 parent 覆盖的 child slots |
| predict | 用 parent 预测 child state |
| detail | child 与预测值的差 $r_j$ |
| update | 用 detail 修正 parent 的 coarse state |
| inverse lifting | 从 parent 与 residual 递归恢复 children |

这给了我们一个重要保护：

> residual 不应当作为原始 child 的直通旁路混入 root；它应当成为有地址的细节量，只有 decoder 展开对应 edge 时才参与恢复。

否则 root 会退化成全部 leaf 的 Bag，分辨率抽水优势会消失。

参考：Wim Sweldens, [The Lifting Scheme: A Construction of Second Generation Wavelets](https://epubs.siam.org/doi/abs/10.1137/S0036141095289051)。图结构上的可学习版本也已经存在，例如 [Graph Neural Networks With Lifting-based Adaptive Graph Wavelets](https://arxiv.org/abs/2108.01660)。

---

## 6. Transformer 式残差与 TreeHeap detail residual 不是一回事

Transformer/ResNet 残差大致是：

$$
x_{l+1}=x_l+f_l(x_l)
$$

它提供接近恒等映射的信息与梯度通道，使深层网络不必在每一层重新创造输入。参考 [Deep Residual Learning](https://arxiv.org/abs/1512.03385)。

旧 TreeHeap 代码中也有：

```text
pooled + MLP(pooled)
query  + UPDATE(query, context)
```

但第一个残差发生在 children 已经被压成 `pooled` 之后。它只能保护 pooled state，不能保存已经丢失的 child detail。

因此下一版需要区分：

```text
kernel residual：帮助深层优化
tree detail residual：保存跨分辨率丢失的信息
```

两者可以同时存在，但不能混为一个变量。

---

## 7. 字符串中有没有“抽取大轮廓”的已有算法

有相关工作，但没有一种算法能仅靠压缩就保证 root 成为人类认可的摘要。

### 7.1 DIORA：用递归预测压力诱导潜在树

[DIORA](https://aclanthology.org/N19-1116/) 用 inside-outside recursive autoencoder 考虑句子的多种二叉树组合，并通过“根据其余句子预测某个词”学习 constituent state。

它支持一个重要判断：递归节点可以在没有人工句法标签时，通过上下文预测任务形成结构。但它不保证 root 是自然语言摘要。

### 7.2 Hierarchical Multiscale RNN：从序列中学习不同时间尺度

[Hierarchical Multiscale RNN](https://arxiv.org/abs/1609.01704) 学习潜在边界，让不同层按不同时间尺度更新。这说明字符串可以在没有显式边界标签时形成多尺度状态。

### 7.3 PEGASUS：直接训练“保留重要内容”

[PEGASUS](https://arxiv.org/abs/1912.08777/) 从文档中移除重要句子，再要求模型根据剩余内容生成它们。它把摘要需要的“重要性”变成了训练压力。

### 7.4 Funnel 与 Hourglass：语言序列可以逐步降低分辨率

[Funnel Transformer](https://arxiv.org/abs/2006.03236)逐步缩短 hidden sequence；[Hourglass Transformer](https://arxiv.org/abs/2110.13711)执行 shorten 后再 upsample。它们证明多长度语言计算可行，但不能单独证明语义轮廓形成。

### 7.5 Top-down latent tree generation

[Recursive Top-Down Production for Sentence Generation with Latent Trees](https://aclanthology.org/2020.findings-emnlp.208/)从潜在二叉树递归生成句子，与 TreeHeap decoder 从 coarse state 展开 detail 的目标直接相关。

这些工作共同提示：

> 代数协议决定信息怎样压缩与恢复，训练目标决定什么信息值得上传。

---

## 8. 新的数据结构契约

下一版代码中的 TreeHeap 节点至少要保存：

```text
Node {
    address          当前堆地址
    parent_address   父地址
    child_addresses  子地址
    depth            递归深度
    span             覆盖的 leaf 区间
    coarse_state     上传后的低分辨率状态
    detail_residual  相对 parent 预测的细节
}
```

任何实验只要在进入 decoder 前把它重新变成无边的 `List[Tensor]`，就不得命名为 TreeHeap recursive READ。

---

## 9. 新 encoder：递归 learned lifting

伪代码如下：

```text
ENCODE(node):
    if node is leaf:
        return token_embedding(node.token)

    child_states = []
    for child in node.children:
        child_states.append(ENCODE(child))

    parent.coarse = UPDATE(child_states)

    for slot, child_state in enumerate(child_states):
        predicted = PREDICT(parent.coarse, slot)
        edge[slot].detail = child_state - predicted

    return parent.coarse
```

关键审计条件是：每个 parent 的输入必须来自其 children 的递归返回值，而不是从全局 leaf array 重新池化。

---

## 10. 新 decoder：沿地址 top-down 展开

```text
DECODE(address, state, remaining_depth):
    node = heap[address]
    bucket = ROUTE_KERNEL(query, node, path)

    if bucket.stop is selected or remaining_depth == 0:
        return OUTPUT(state)

    for child_address in node.child_addresses:
        predicted_child = PREDICT(state, child_slot)
        child_state = predicted_child + edge.detail
        DECODE(child_address, child_state, remaining_depth - 1)
```

这里的递归深度不是读取数组的数量，而是 kernel 沿合法地址实际移动的次数。

一次路径可能是：

```text
root
  -> left
  -> right
  -> stop
```

每一步都携带当前地址、局部 subheap、path state 和概率桶。

---

## 11. 下一项实验不能直接跑语言大模型

我们先验证数学与代码契约，再验证语言归纳能力。

这里不是从零开始。项目已有两段应当复用的实现：

- `s2_adaptive_lifting_wmt.py` 已经按 `detail = child - predict(anchor)`、`parent = anchor + update(detail)` 递归 FOLD，并用逆运算 UNFOLD；历史实验的闭包 MSE 为 `2.35e-14`。
- `s2_lifting_pump_wmt.py` 的 recursive READ 保留了 active probability。某个 parent 的 expand 概率只会分配给它自己的两个 children，而不是对整层节点重新做一次无条件 pooling。

历史 S2 数据中，recursive/root/full/flat 的测试 NLL 分别为 `5.0903 / 5.4337 / 5.1342 / 4.8103`。这支持“递归 detail 对翻译有用”，但 flat 仍然更好，也没有证明 root 是语义摘要。

因此下一项代码工作不是再发明一种 FOLD，而是给已有 recursive READ 增加严格的 `max_depth`，并审计它是否真的沿地址递归生长。

### Proof A：完整 residual 的递归往返

输入一棵随机 TreeHeap：

```text
leaf -> recursive encode -> root + addressed residuals
     -> recursive decode -> reconstructed leaf
```

预测：保留全部 residual 时，重建误差接近浮点误差；删除任何一条 residual 时，只影响其对应 subheap。

这证明协议和地址实现正确，不证明语义。

### Proof B：逐级释放 residual 的率失真曲线

对真实中文 BPE 序列递归编码，只允许 decoder 使用：

```text
root
root + depth1 residual
root + depth1..2 residual
...
全部 residual
```

预测：token reconstruction NLL 应总体单调下降。若曲线乱跳，说明 coarse/detail 协议没有形成稳定分辨率。

### Proof C：递归与地址因果

保持 coarse state 和 residual 数值不变，只交换 residual 所属的 edge address。

预测：恢复损失明显增加，并主要发生在被交换的 subheap 内。如果全局几乎不变，decoder 仍未利用 TreeHeap 地址。

### Proof D：抽水是否产生可用轮廓

在 root 容量固定且明显小于 leaf 总容量时，让 root 预测：

- 被遮住的 span；
- 相邻上下文；
- 文档中抽出的 gap sentence；
- 下一段真实文本。

再与随机分组树、flat bottleneck 和 shuffled corpus 比较。

只有当合法 TreeHeap 的 coarse state 在 held-out 数据上更好，才能说抽水机提取了任务相关轮廓。

---

## 12. 新 Claim 的边界

下一项 Claim 暂定为：

```text
S3-TREE-LIFT-RECURSIVE-C01
```

> 一个显式保存 parent-child 地址的共享 learned-lifting kernel，可以递归地把 leaf 分解为 parent coarse state 与 addressed detail residual；top-down decoder 沿相同地址协议展开时，完整 residual 支持近似无损恢复，逐层释放 residual 形成有序率失真曲线，交换 residual 地址会产生局部且显著的恢复损失。

它只声明三件事：

1. 递归协议在代码中真实存在；
2. coarse/detail 分辨率可以稳定定义；
3. decoder 使用了 TreeHeap 地址。

它不声明：

- root 已经理解人类摘要；
- TreeHeap 优于 Transformer；
- 模型已经形成世界知识或意识；
- 任意 FOLD 都会自然产生语义轮廓。

---

## 13. 当前状态

```text
旧实验：完成，但重新分类为 multiresolution flat READ
旧 Claim：未被测试，不是被否证
新协议：递归 learned lifting + addressed residual + top-down READ
新实验：确定性 contract 已通过，真实语言 depth-cap 实验待运行
```

2026-07-19，第一道 contract probe 已在 io 的 CPU 上完成：

| 检查 | 结果 |
|---|---:|
| 8-leaf 完整 FOLD/UNFOLD MSE | `3.2341e-15` |
| 不同 depth cap 下 route 质量守恒最大误差 | `5.9605e-8` |
| 交换两个 residual 后，目标四叶 subheap MSE | `1.4019` |
| 同一次交换在 subheap 外造成的 MSE | `2.7198e-15` |

这说明当前复用的 lifting 代数可以递归闭合，概率质量可以沿父子地址守恒，而且 residual 地址扰动具有严格局部性。它仍然没有证明 root 学到了语言轮廓。下一道真实语料实验将专门验证 root source causality、递归深度收益和学习后的地址因果性。

这次纠错最重要的收获不是换了一个公式，而是建立了一条命名纪律：

> 递归生成过数据，不等于递归参与了计算。只有地址、父子关系和共享 kernel 一起进入 decoder 的移动过程，才是 TreeHeap recursive READ。
