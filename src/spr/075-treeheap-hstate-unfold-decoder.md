---
title: "[SPR-075] TreeHeap 为什么会复读：从伪递归读取到 H_state 整体解码"
date: 2026-07-29
lastmod: 2026-07-29
weight: 75
author: Houming818 & Codex Review
description: "审计 C11 decoder 的真实计算过程，并提出 source H_state 到 target H_state、再经 TreeHeap UNFOLD 一次生成完整字符串的对称解码方案。"
tags: [SPR, TreeHeap, ARA, Decoder, H-state, UNFOLD, Recursion, Mode Collapse]
---

# TreeHeap 为什么会复读

C11 修复了一个重要问题：短输入后面不再铺满可见的 EOS，而是使用不可见 PAD。实验也证明，打乱或清空 source 会让 NLL 变差。因此，TreeHeap 的 `H_state` 确实携带了输入信号。

但 CLI 仍然出现了明显复读：

```text
输入：为什么鲨鱼不坐沙发？
输出：我只想说，我只想说，我只想说……

输入：夜幕、星光、草木清香……
输出：一股香味，香味浓郁，香味浓郁……
```

第二个例子甚至有一点语义相关性：输入中的“清香”影响了输出中的“香味”。这说明模型不是完全忽略输入。但是，它只能释放一个很短的主题，随后便进入循环。

Houming818 提出了一个关键问题：

> 如果 decoder 真在递归生成一个 64-token 结构，为什么会如此稳定地把一个短句重复八次？这里会不会存在代码逻辑错误？

代码审计表明，这个怀疑是正确的。

## 1. 当前的 RecursiveDecoder 并没有递归消费 TreeHeap

当前 decoder 的单次 `read()` 确实会从 root 向下遍历 TreeHeap 的多个深度，并计算各层的加权 context。因此，把它称为“树上递归读取”并非完全错误。

问题在于：每生成一个新 token，`read()` 都重新执行，并重新初始化：

```python
active = root
```

其实际流程是：

```text
第 1 步：从 root 重新读取全树摘要 → token 1
第 2 步：从 root 重新读取全树摘要 → token 2
第 3 步：从 root 重新读取全树摘要 → token 3
……
```

它没有保存以下状态：

```text
上一步走到哪个 subheap
哪些节点已经被消费
下一步应读取哪个地址
递归栈位于哪里
当前分支何时结束
```

所以，当前结构不是“跨 token 的递归解压”，而是：

```text
同一棵 H_state
→ 每一步重新计算近似的全树摘要
→ GRU 根据上一个 token 生成下一个 token
```

TreeHeap 只参与了 context 的计算。输出过程本身仍然是一台普通的流式自回归生成器。

## 2. 为什么重复八次不是小概率事件

直觉上，连续八次生成同一个短句似乎概率很低。但 CLI 使用的是 greedy `argmax`，不是每一步独立随机抽样。

每一步执行的是一个确定函数：

$$
(h_t, y_{t-1}, C_t) \longmapsto y_t
$$

其中 $h_t$ 是 GRU hidden state，$y_{t-1}$ 是上一个 token，$C_t$ 是重新从同一棵 TreeHeap 读出的 context。

一旦系统进入类似下面的状态环：

```text
“我只想说” → “，” → “我只想说”
```

下一轮输入状态就会再次接近上一轮。确定性 `argmax` 会把它送回同一个环。这叫周期吸引子。它不是八次巧合，而是一次进入循环后被稳定地重复。

因此，增加 `max-output` 只会给循环更多执行次数，不会增加 H_state 中可以依次解出的细节。

## 3. 256 个 leaf 在哪里

C11 的 256 个 leaf 属于输入 encoder：

```text
最多 256 个 source piece
→ 256-leaf TreeHeap
→ FOLD
→ source H_state
```

当前 decoder 并没有一棵 256-leaf 输出树。它只是最多循环 128 次或 CLI 指定的 64 次。

这两个“长度”在概念上完全不同：

```text
输入 leaf 数量：结构容量
输出循环次数：自回归执行次数
```

循环 64 次不等于解压了 64 个不同的 TreeHeap 地址。

## 4. Houming818 的新假设：先形成整体，再突然生成 string

Houming818 提出，TreeHeap 的输出未必应该是 stream。模型可能先形成一个完整的输出结构，再一次性坍缩为 string。

工程上可以把“突然生成”严格定义为：

```text
source H_state
→ target H_state
→ 递归 UNFOLD
→ 全部 target leaf
→ 并行 token 概率
→ 完整 string
```

如果输出上限是 64 个 token，只需要 6 层展开：

```text
1 → 2 → 4 → 8 → 16 → 32 → 64
```

若输出上限为 128，则需要 7 层。这不是在一个计算步骤中凭空出现文本，而是在 $\log_2 N$ 层结构计算后，并行得到 $N$ 个带地址的输出位置。

## 5. 完整 H_state 不是只有 root

TreeHeap encoder 的完整状态应写成：

$$
H = \left(r, \{d_k\}, \{g_k\}, \{m_k\}\right)
$$

其中：

| 符号 | 含义 |
|---|---|
| $r$ | root，全局压缩状态 |
| $d_k$ | 第 $k$ 层折叠留下的 detail |
| $g_k$ | 左右方向或手性 gate |
| $m_k$ | 节点是否存在的 mask |

只有 root 通常无法无损恢复全部 leaf。TreeHeap 的可逆性来自 `root + details + gates`，不是来自 root 独自记住整句话。

因此，新 decoder 不应直接让 root 输出所有 token，也不应反复读取同一个摘要。它应该先预测目标 TreeHeap 的完整状态：

$$
H_{target} = K_{\theta}(H_{source})
$$

然后执行：

$$
Y = \operatorname{UNFOLD}(H_{target})
$$

## 6. 不重新发明 split：复用现有 TreeHeap 逆运算

当前 encoder 已经有一套严格的 FOLD/UNFOLD 方程。给定 parent、detail 和 gate，可以恢复左右子节点：

$$
a = p - U(d)
$$

$$
\hat{b} = d + P(a)
$$

$$
left = g \cdot a + (1-g)\cdot\hat{b}
$$

$$
right = g \cdot\hat{b} + (1-g)\cdot a
$$

这里：

```text
p：parent state
d：detail state
g：左右方向 gate
U：update kernel
P：predictor kernel
```

所以新 decoder 不需要手写一个任意的“父节点拆成左右节点”函数。它只需学习预测目标树的参数：

```text
target_root = K_root(source H_state)

target_detail[k] = K_detail(
    target_parent,
    source_subheap,
    source_root,
    depth,
    address
)

target_gate[k] = K_gate(...)
```

随后使用同一套 UNFOLD 代数确定性地得到左右子节点。这使 encoder 与 decoder 共享同一种 TreeHeap 数学协议。

## 7. 新 decoder 的最小版本

第一版先不解决可变长度，固定生成 128 个输出 leaf：

```text
source tokens
→ source TreeHeap FOLD
→ source H_state
→ 预测 target root/details/gates
→ TreeHeap UNFOLD 七层
→ 128 个 target leaf
→ 共享 output head
→ 128 组 token logits
```

所有目标位置同时计算交叉熵：

$$
L_{token} = \frac{1}{128}\sum_{i=1}^{128}
CE\left(W_o z_i, y_i\right)
$$

$z_i$ 是第 $i$ 个目标 leaf。梯度路径为：

```text
token loss
→ target leaf
→ UNFOLD
→ target detail/gate/root predictor
→ source H_state
→ encoder FOLD
```

这就是 encoder 和 decoder 共同形成私有协议的可微路径。训练过程不需要把正确的前一个 token 喂给 decoder，因此也没有当前意义上的 teacher forcing 断层。

## 8. 为什么它可能减少复读

新结构中，第 17 和第 18 个 token 对应不同地址：

```text
leaf[17] = root → left → right → ...
leaf[18] = root → left → right → ...
```

它们共享上层轮廓，但必须经过不同路径和 detail。后一个 token 不会因为前一个 token 是“我只想说”而再次收到同样的输入。

不过，非流式生成并不自动保证成功。如果所有预测 detail 都接近零，不同 leaf 仍可能坍缩成相似状态。因此，不能只看 NLL。

## 9. Claim、Predict 与 Proof

### Claim

给定同一个 TreeHeap encoder，使用持久输出地址和代数 UNFOLD 的整体 decoder，应该比当前“每 token 重置 root”的 GRU decoder 更能保持输出位置差异，并降低自由生成中的周期重复。

### Predict

如果 Claim 成立，应同时观察到：

1. 自由输出的 token-level distinct-2/4 明显提高；
2. 最长重复片段和重复运行长度下降；
3. 打乱目标 leaf 地址后，NLL 显著升高；
4. 清零不同深度的 target detail，会产生可重复但不同的损伤；
5. leaf 间方差不坍缩为零；
6. source shuffle 和 empty source 仍保持显著损伤；
7. 相同训练数据、参数量和计算预算下，与旧 GRU decoder 正面对比。

### Falsification

以下任一结果都会否定强 Claim：

```text
UNFOLD decoder 仍产生相同短语循环；
打乱 leaf 地址几乎不影响 NLL；
不同 leaf 的状态趋于相同；
detail 清零没有损伤；
source shuffle 不再影响结果；
改进仅来自更多参数或更多计算。
```

第一轮实验只验证固定 128-leaf 输出。只有结构和自由生成闸门通过后，才增加节点 `STOP/SPLIT` 概率来学习可变长度，避免一次引入过多不确定变量。

## 10. 当前航行状态

C11 已经证明：修正 PAD 协议后，TreeHeap 的 source H_state 对目标概率存在因果影响。

C11 同时暴露：当前 decoder 只会反复读取全树摘要，并不沿 TreeHeap 递归解压输出位置。因此，“输入结构参与了计算”和“已经形成 TreeHeap decoder”是两个不同结论。

现在的修复航线是：

```text
保留：现有 FOLD encoder 和 C11 source-conditioning 证据
删除：流式 GRU 作为最终 TreeHeap decoder 的假设
新增：source H_state → target H_state → UNFOLD → string
先测：固定长度、结构因果性、自由生成复读
后测：可变长度、翻译、对话和规模化训练
```

这不是把失败改名为新架构。恰恰相反，它来自 CLI 反例和代码审计：当前所谓“递归 decoder”只在一次读取内部递归，却没有在输出过程里递归。只有把输出地址、detail 和 UNFOLD 真正放进计算图，TreeHeap 才拥有与 FOLD encoder 对称的另一半。

> **License: GPLv3。本文的代码审计、H_state 整体解码方案、Claim/Predict/Falsification 与 SameTime/ARA 一并公开。**
