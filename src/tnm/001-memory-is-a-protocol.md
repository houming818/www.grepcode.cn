---
title: "[TNM-001] 记忆不是仓库：私有编解码协议如何成为持续状态"
date: 2026-08-07
lastmod: 2026-08-07
weight: 1
author: Houming818 & Codex Review
description: "从原文检索与理解问答的差别出发，说明所有记忆都是协议，并厘清 Encoder、Decoder、TreeHeap merge 与持续记忆之间的关系。"
tags: [TNM, TreeHeap, Memory, Encoder, Decoder, PrivateProtocol, Merge]
---

# 从一句“西西弗斯”开始

假设系统读到一句话：

> 西西弗斯在推着石头上山。

过一会儿，我们希望它记得这件事。怎样才算“记得”？至少可以有两种完全不同的行为。

第一种像 GrepCode：

```text
查询：西西弗斯 石头
返回：西西弗斯在推着石头上山。
```

第二种像问答系统：

```text
问题：谁在推石头？
回答：西西弗斯。
```

一开始，我们很容易把第一种称为“原文存储”，把第二种称为“理解式记忆”，仿佛第二种更接近真正的记忆。这个说法并不准确。

Houming818 指出了更根本的定义：

> **它们都是记忆协议。区别不在于哪一种才算记忆，而在于写入端和读取端共同约定了什么行为。**

GrepCode 协议按照词面、地址或索引找回原文；问答协议按照问题生成答案。它们的状态表示、写入方式和读取方法都可以不同。即使底层保存的是同一段经历，协议不同，能得到的结果也不同。

这成为 TNM（TreeHeap Native Memory，TreeHeap 原生记忆协议）专题的起点。

## 1. 什么叫“协议”

协议不是一句神秘的比喻。它是一组参与者都遵守的计算约定。

最小的记忆协议可以写成：

\[
\mathcal{M}=(H,W,R,U)
\]

其中：

| 符号 | 含义 |
|---|---|
| \(H\) | 当前记忆状态 |
| \(W\) | Write，怎样把新信息写入状态 |
| \(R\) | Read，怎样用查询读取状态 |
| \(U\) | Update，怎样处理覆盖、冲突、遗忘与修复 |

如果缺少读取协议，一串比特即使保存了全部历史，也未必能被当前系统解释。如果缺少写入协议，系统只知道怎样读，却不知道新的经历应当放在哪里。如果缺少更新协议，记忆会不断膨胀，或者新信息覆盖旧信息而不自知。

所以记忆不是单独的 \(H\)。更完整的说法是：

> **记忆是状态与读写规则共同形成的系统。**

## 2. Encoder 与 Decoder 已经是一套协议

在普通 Encoder--Decoder 系统中，Encoder 把输入变成内部状态：

\[
H_x=E_{\theta}(x)
\]

Decoder 再解释这个状态：

\[
y=D_{\phi}(H_x)
\]

只要两端一起训练，它们就可能形成一套人类看不懂、但彼此能够使用的内部编码。这就是我们在 TreeHeap 研究中反复讨论的**私有协议**。

这里的“对称”不能简单理解为两个函数长得一样。它真正表示的是读写之间存在配合：

```text
Encoder 怎么写
        ↓
中间状态怎样变化
        ↓
Decoder 就学会怎样读
```

在精确 Echo 任务中，Decoder 近似执行 Encoder 的逆：

\[
D_{\phi}(E_{\theta}(x))\approx x
\]

但在翻译、问答和续写中，Decoder 并不是 Encoder 的数学逆函数。它读取同一个内部状态，却按照任务协议产生另一种输出。

因此，“Encoder 与 Decoder 共同形成私有协议”这句话本身没有错。问题在于：它描述的通常还是**一次输入、一次输出**。

## 3. 从编解码协议到记忆协议，增加了时间

一次性编解码可以这样工作：

```text
输入 x
  ↓
临时状态 Hx
  ↓
输出 y
  ↓
Hx 被丢弃
```

记忆系统不能在输出后丢掉全部状态。它必须把旧状态带到下一次：

\[
H_{t+1}=W_{\theta}(H_t,x_t)
\]

以后再接受查询：

\[
y_t=R_{\phi}(H_t,q_t)
\]

例如：

```text
H0
 + “西西弗斯在推着石头上山”
 ↓ 写入
H1
 + 后续经历
 ↓ 继续写入
H2
 + “谁在推石头？”
 ↓ 读取
“西西弗斯”
```

与普通 Encoder--Decoder 相比，记忆协议至少多了三项约束：

1. **持续性**：处理结束后，状态仍然存在；
2. **增量性**：新经历进入时，不必从零重建全部历史；
3. **干扰管理**：连续写入以后，旧协议不能立刻失效。

因此，两者的关系不是互相替代，而是包含关系：

\[
\text{Encoder--Decoder 私有协议}
\subset
\text{完整记忆协议}
\]

私有编解码协议是记忆的读写语言；持续状态、冲突处理和遗忘机制构成它的时间部分。

## 4. TreeHeap merge 在协议中负责什么

TreeHeap 已经有一个明确的局部 FOLD：

\[
D=R-P_{\theta}(L)
\]

\[
U=L+A_{\theta}(D)
\]

这里 \(L\) 和 \(R\) 是左右子状态，\(D\) 是 detail，\(U\) 是向上递归的 parent。给定 \(U,D\)，可以恢复：

\[
L=U-A_{\theta}(D)
\]

\[
R=D+P_{\theta}(L)
\]

这说明 TreeHeap merge 已经拥有可逆 lifting transform 的数学基础。这里值得把推导完全公开，因为可逆性不是依靠“神经网络也许能学会”，而是由算子结构直接保证。

先把 FOLD 拆成两个三角变换。第一步是 Predict：

\[
(L,R)\longmapsto\left(L,D=R-P_{\theta}(L)\right)
\]

第二步是 Update：

\[
(L,D)\longmapsto\left(U=L+A_{\theta}(D),D\right)
\]

Predict 没有修改 \(L\)，所以知道 \(L,D\) 就能恢复 \(R\)。Update 没有修改 \(D\)，所以知道 \(U,D\) 就能恢复 \(L\)。把两步逆序执行，就得到前面的 UNFOLD 公式。

这一结论不要求 \(P_{\theta}\) 或 \(A_{\theta}\) 是线性函数，也不要求单独求它们的逆。只要 FOLD 和 UNFOLD 调用同一组确定参数，显式逆就成立。

如果 \(P\) 和 \(A\) 可微，两步的 Jacobian 分别具有分块三角结构：

\[
J_{\mathrm{predict}}=
\begin{bmatrix}
I&0\\
-J_P&I
\end{bmatrix}
\]

\[
J_{\mathrm{update}}=
\begin{bmatrix}
I&J_A\\
0&I
\end{bmatrix}
\]

两个行列式都为 1，因此完整局部变换满足：

\[
\left|\det J_{\mathrm{FOLD}}\right|=1
\]

这意味着在理想连续算术中，它是一个体积保持的双射。实际程序仍会受到浮点误差、mask、量化和参数版本不一致的影响，所以代码必须继续做数值闭合测试。

### 4.1 整棵树为什么也能闭合

设有 \(N=2^h\) 个 leaf，每个状态维度为 \(d\)。第一层产生 \(N/2\) 个 parent 和 \(N/2\) 个 detail；第二层继续产生 \(N/4\) 个 parent 和 \(N/4\) 个 detail，直到只剩 root。

所有 detail 的数量是：

\[
\frac{N}{2}+\frac{N}{4}+\cdots+1=N-1
\]

加上一个 root，状态块总数仍然是：

\[
1+(N-1)=N
\]

因此完整 TreeHeap 变换保持总自由度：

\[
Nd\longleftrightarrow d+(N-1)d=Nd
\]

从 root 开始，只要按照深度逆序使用每层 detail，就能恢复全部 leaf。这个结论可以由深度归纳直接得到：深度 1 的局部 FOLD 可逆；若深度 \(h\) 的两棵子树可逆，再加一个可逆顶层 FOLD，深度 \(h+1\) 也可逆。

### 4.2 “压缩”到底发生在哪里

完整保留 root 和全部 detail 时，TreeHeap 完成的是**可逆坐标变换**，不是减少字节数。真正的有损压缩发生在：

1. 只读取 root 或较浅 frontier；
2. 对较深 detail 进行低精度量化；
3. 删除、稀疏化或熵编码低价值 detail；
4. 在固定读取预算下，不把全部 detail 搬入现实 \(H\)。

因此 TNM 当前首先利用的是**访问压缩和分辨率压缩**。它是否还能获得存储压缩，必须由后续 rate--distortion 实验回答，不能从 lifting 公式直接推出。

但是，这还不是记忆协议。

merge 目前回答的是：

> 两个局部状态怎样变成 parent 与 detail，并且以后可以展开？

记忆协议还必须回答：

> 新经历应该与哪一个 subheap 合并？旧状态哪些部分要保留？查询 kernel 怎样找到与问题有关的部分？重复、冲突和遗忘怎样处理？

因此，先把长期状态明确记为 \(M\)，TreeHeap 中更完整的数据流应当是：

\[
z_t=E_{\theta}(x_t)
\]

\[
M_{t+1}=\operatorname{Merge}_{\theta}(M_t,z_t)
\]

\[
R_t=K_{\phi}(q_t,M_{t+1})
\]

其中：

- Encoder 把新观察变成可写入状态；
- Merge 决定它怎样进入已有 TreeHeap；
- Query kernel 从长期 TreeHeap 中形成取回状态 \(R_t\)；
- Decoder 与现实状态的融合过程将在下一节展开。

merge 是协议的状态更新算子，不是协议的全部。

## 5. 记忆系统不是把全部过去塞进现实 H

到这里还缺少一个重要的工程边界。真正使用记忆时，当前问题首先形成现实状态 \(H_t\)，然后从长期记忆系统中提取一小块状态 \(R_t\)，再把它混入现实：

\[
q_t=E_q(H_t)
\]

\[
R_t=\operatorname{Retrieve}(M_t,q_t;B)
\]

\[
H'_t=\operatorname{Mix}(H_t,R_t)
\]

\[
y_t=D(H'_t)
\]

这里必须区分四个对象：

| 符号 | 工程含义 |
|---|---|
| \(M_t\) | 长期记忆 TreeHeap |
| \(H_t\) | 当前问题、上下文和感知形成的现实状态 |
| \(R_t\) | 从长期记忆中提取的小型相关状态 |
| \(H'_t\) | 现实与记忆融合后的生成状态 |

参数 \(B\) 是读取预算，包括最多访问多少节点、展开多少次、搬入多少状态以及允许多少延迟。一个系统即使最终能从 12 TB 数据中找到“西西弗斯”，如果查询需要一个小时，它也不是可用的实时记忆。

因此 TNM 不能只报告回答准确率。它还必须报告访问节点数、读取带宽、延迟和记忆容量。

## 6. 为什么不能退化成 B 或 B+ 检索树

最直接的实现是把记忆分区：每个内部节点保存范围或类别，query 沿树比较，最后到 leaf 取出一条记录。

```text
query
-> 比较分区
-> 沿树寻找 leaf
-> 返回 record
```

这当然可以工作，但本质上是可训练的 B/B+ Tree。TreeHeap 只提供了树形地址，没有使用此前建立的 FOLD、detail 和多分辨率压缩协议。

TNM 希望测试另一种机制：

> **长期记忆 \(M\) 本身就是经过递归 FOLD 的多分辨率 TreeHeap；读取不是定位某条记录，而是在 query 条件下局部 UNFOLD，逐步合成足以回答问题的 \(R\)。**

两者的区别是：

| B/B+ 检索树 | TNM 的候选设计 |
|---|---|
| 内部节点保存分区键 | 内部节点保存 parent/detail 压缩状态 |
| 查询目标是定位记录 | 查询目标是合成可用状态 |
| 一般必须到 leaf 才获得记录 | 可能在 parent 分辨率停止 |
| 路由规则主要由索引定义 | 展开协议由任务训练形成 |
| 返回一条已有记录 | 返回 query 条件下重建的小 TreeHeap |

这不意味着 B+ Tree 不好。它只是另一个成熟协议，不是 TNM 当前要验证的 TreeHeap 原生机制。

## 7. Query-Conditioned Partial UNFOLD

我们把这个候选逻辑原型暂称为 **Query-Conditioned Partial UNFOLD**，即“查询条件下的局部展开”。

假设长期记忆由 leaf 状态递归 FOLD 得到：

\[
M=\left(U_{\mathrm{root}},D_{\mathrm{root}},D_1,D_2,\ldots\right)
\]

其中 root 是全局粗分辨率状态，各层 detail 保存继续提高分辨率所需的信息。

### 7.1 记忆怎样写成 M

先把第 \(j\) 条经历 \(x_j\) 编成一个 leaf 状态：

\[
e_j=E_w(x_j)\in\mathbb{R}^d
\]

固定容量为 \(N\) 时，当前 leaf 层记为：

\[
X=(e_1,e_2,\ldots,e_N)
\]

空位置由显式 mask 标记，不能把 PAD 的数值大小误当成有效记忆。对整个 leaf 层执行递归 FOLD：

\[
M=\mathcal{T}_{\theta_f}(X)
\]

如果只替换一个 leaf，树外所有不在其祖先路径上的状态保持不变。需要重新计算的节点数至多等于树高：

\[
h=\log_2N
\]

所以固定地址下的一次局部更新可以在 \(O(\log N)\) 个 merge 中完成。这里的地址更新规则仍然是第一版待定项；这个复杂度结论只描述“已知写入位置以后”怎样维护 TreeHeap，不证明系统已经学会把新经历放到正确位置。

### 7.2 mixed-resolution frontier

Partial UNFOLD 不把整棵树恢复成 leaf 数组。它维护一个 frontier，即当前已经足以代表整棵记忆的、不重叠的节点集合。

初始 frontier 只有 root：

\[
\mathcal{F}_0=\{\mathrm{root}\}
\]

如果选择展开节点 \(i\)，就用它的两个子节点替换它：

\[
\mathcal{F}_{t+1}
=
\left(\mathcal{F}_t\setminus\{i\}\right)
\cup
\{\operatorname{left}(i),\operatorname{right}(i)\}
\]

设 \(\operatorname{Leaves}(i)\) 表示节点 \(i\) 覆盖的原始 leaf 地址。每次替换都满足：

\[
\operatorname{Leaves}(i)
=
\operatorname{Leaves}(\operatorname{left}(i))
\mathbin{\dot\cup}
\operatorname{Leaves}(\operatorname{right}(i))
\]

符号 \(\dot\cup\) 表示不相交并集。因此任意时刻都有两个不变量：

\[
\bigcup_{i\in\mathcal{F}_t}\operatorname{Leaves}(i)
=
\operatorname{Leaves}(\mathrm{root})
\]

\[
i\neq j
\Longrightarrow
\operatorname{Leaves}(i)\cap\operatorname{Leaves}(j)=\varnothing
\]

也就是说，frontier 始终无遗漏、无重复地覆盖完整记忆，只是不同区域采用不同分辨率。展开 \(B\) 次以后：

\[
|\mathcal{F}_B|=B+1
\]

这个不变量是 Partial UNFOLD 与“随便取几个节点”之间的数学区别。

### 7.3 query 怎样控制展开

读取从 root 开始，每到一个 frontier 节点，kernel 接收：

\[
(q,U_i,D_i,\operatorname{path}_i,\operatorname{depth}_i)
\]

然后产生一个局部概率桶：

\[
\pi_i=P(\mathrm{stop},\mathrm{left},\mathrm{right},\mathrm{both})
\]

四个动作分别表示：

- `stop`：当前分辨率已经足够；
- `left`：展开当前节点后，优先继续细化左侧；右侧仍作为粗节点保留在 frontier；
- `right`：展开当前节点后，优先继续细化右侧；左侧仍作为粗节点保留；
- `both`：两个子节点都进入后续可展开集合。

一旦展开，就直接使用 TreeHeap 已有的 UNFOLD：

\[
L_i=U_i-A_{\theta}(D_i)
\]

\[
R_i=D_i+P_{\theta}(L_i)
\]

在预算耗尽或全部选择 `stop` 后，系统得到的不是某条原始记录，而是一棵混合分辨率的小 TreeHeap：有的区域已经展开到细节，有的区域仍然保留粗轮廓。

\[
R_t=\operatorname{PartialUnfold}_{\theta_r}(M_t,q_t;B)
\]

更具体地说，\(R_t\) 不是简单求和后的单向量，而是带地址、深度和 query 权重的 frontier：

\[
R_t=
\left\{
(i,U_i,\operatorname{path}_i,\operatorname{depth}_i,w_i)
\;\middle|\;
i\in\mathcal{F}_B
\right\}
\]

其中 \(w_i\) 由读取 kernel 产生。保留 path 和 depth 是为了不把 mixed-resolution TreeHeap 再次压平为无序 word bag。

### 7.4 可执行伪代码

```text
frontier = {root}
expandable = {root}

repeat at most B times:
    对 expandable 中已暴露的节点计算 kernel(q, U, D, path, depth)
    选择一个允许展开的节点 i
    如果所有节点都选择 stop:
        break

    (left, right) = UNFOLD(U_i, D_i)
    frontier 删除 i
    frontier 加入 left 和 right

    根据 left/right/both 动作更新 expandable

return 带地址和深度的 frontier 作为 R
```

这个算法只读取已经暴露节点的局部 detail，不需要先扫描全部 leaf。若实现为了算所有节点分数而预先读取整棵树，就已经破坏了预算定义。

同一个 \(M\) 面对不同问题，可以合成不同的 \(R\)：

```text
“谁在推石头？”
-> 展开能改变人物回答的内部状态

“石头被推向哪里？”
-> 展开另一组内部状态

“原话是什么？”
-> 继续展开更多 detail，接近 leaf 分辨率
```

这些例子描述的是外部行为，不要求树中预先存在“人物槽”或“地点槽”。内部协议仍然可以是训练形成的私有编码。

## 8. 时间复杂度从展开预算产生

每展开一个节点，只读取该节点附近的 parent/detail，并恢复两个子状态。设：

\[
C_U=C_P+C_A+O(d)
\]

其中 \(C_P\) 和 \(C_A\) 分别是一次 predictor 与 update 的成本，\(C_U\) 是一次 UNFOLD 的成本；再设一次读取 kernel 的成本为 \(C_K\)。

如果节点分数只依赖 \((q,U_i,D_i,\operatorname{path}_i,\operatorname{depth}_i)\)，新节点暴露时计算一次分数，并用优先队列维护候选，那么展开 \(B\) 次的成本是：

\[
T_{\mathrm{read}}
=
O\!\left(B(C_U+C_K)+B\log B\right)
\]

若忽略固定维度 kernel 和优先队列常数，才可以简写为近似 \(O(B)\)。如果实现每一步都重新扫描整个 frontier，累计成本会退化为 \(O(B^2)\)；如果为了打分先读取全部 \(N\) 个节点，则直接退化为 \(O(N)\)。这些实现不能被包装成快速 Partial UNFOLD。

如果只沿一条路径走到深层：

\[
B\approx\log_2N
\]

如果问题需要多个区域：

\[
\log_2N<B\ll N
\]

最坏情况下仍然可能展开整棵树。TreeHeap 不会因为长得像树就自动获得快速查询。它真正需要验证的 claim 是：

> 训练形成的 parent/detail 协议，能否让多数查询在远小于 \(N\) 的展开预算下得到足够的 \(R\)。

评价时应当画出回答质量与读取预算的曲线：

```text
展开 4 个节点  -> 回答准确率 ?
展开 8 个节点  -> 回答准确率 ?
展开 16 个节点 -> 回答准确率 ?
展开全部节点   -> 回答准确率 ?
```

如果少量展开已经接近完整展开，TreeHeap 压缩结构才提供了可测量的读取收益。如果必须扫描全部节点，它就没有获得预期优势。

完整建立一个 \(N\)-leaf TreeHeap 需要 \(N-1\) 次局部 FOLD：

\[
T_{\mathrm{build}}=O\!\left(N(C_P+C_A)\right)
\]

已知写入地址后，修改一个 leaf 只重算祖先路径：

\[
T_{\mathrm{update}}=O\!\left((C_P+C_A)\log N\right)
\]

完整可逆存储仍然需要 \(N\) 个 \(d\)-维状态块：

\[
S_{\mathrm{exact}}=O(Nd)
\]

所以 TNM 当前可争取的是读取带宽和在线计算收益，不应把它提前写成无条件的存储空间收益。

## 9. 哪些部分允许训练

这个逻辑原型包含三组可训练协议：

\[
\theta_f:\quad\text{信息怎样形成 parent/detail}
\]

\[
\theta_r:\quad\text{query 怎样决定 stop 或展开}
\]

\[
\theta_m:\quad\text{取回的 R 怎样混入现实 H}
\]

完整流程是：

\[
M=\operatorname{FOLD}_{\theta_f}(X)
\]

\[
R=\operatorname{PartialUnfold}_{\theta_r}(M,q;B)
\]

\[
H'=\operatorname{Mix}_{\theta_m}(H,R)
\]

\[
y=D(H')
\]

第一版不设计“智能判断什么值得记住”，也不把未来读取成本硬塞进 loss。预算 \(B\) 直接作为架构限制；训练目标只评价在这个限制下任务是否完成：

\[
\mathcal{L}=\operatorname{CE}(y,y^*)
\]

### 9.1 R 怎样混入现实 H

为了不把取回结果退化成向量拼接，最直接的 TreeHeap-native Mix 是再执行一次 lifting merge。把现实 TreeHeap 和取回 TreeHeap 的 root 状态分别记为 \(U_H,U_R\)：

\[
D_{\mathrm{mix}}=U_R-P_m(U_H)
\]

\[
U_{H'}=U_H+A_m(D_{\mathrm{mix}})
\]

新的 \(H'\) 保留 \(H\)、mixed-resolution \(R\) 和 \(D_{\mathrm{mix}}\) 的结构引用，而不是只留下 \(U_{H'}\) 一个向量。对应逆变换仍然是：

\[
U_H=U_{H'}-A_m(D_{\mathrm{mix}})
\]

\[
U_R=D_{\mathrm{mix}}+P_m(U_H)
\]

这给出了一个明确、可逆的候选 Mix，但不保证 Decoder 会使用 \(R\) 的细节。如果训练后 Decoder 只读 \(U_{H'}\)，或者清零 \(R\) 不造成损伤，记忆协议仍然失败。

### 9.2 离散路由怎样获得梯度

`stop/left/right/both` 是离散动作，而梯度下降要求连续计算图。这是当前理论原型里尚未解决、不能藏起来的部分。

读取 kernel 可以先产生连续概率：

\[
\pi_i=\operatorname{softmax}(K_{\theta_r}(q,U_i,D_i,p_i,h_i))
\]

候选训练方法之一是 straight-through 估计。前向传播使用硬动作：

\[
a_{\mathrm{hard}}=\operatorname{onehot}(\arg\max\pi_i)
\]

反向传播使用：

\[
a_{\mathrm{ST}}
=
a_{\mathrm{hard}}+\pi_i-\operatorname{stopgrad}(\pi_i)
\]

这样前向过程严格遵守 \(B\) 次展开预算，反向过程给概率 kernel 近似梯度。但 straight-through 梯度有偏，不能视为数学定理。

另外两种公开备选是：

1. 小规模 proof 中对全部动作做 soft mixture，梯度稳定，但训练成本可能达到 \(O(N)\)；
2. 用 policy gradient/REINFORCE 优化硬动作，理论上不需要连续化，但方差较大。

第一轮实验必须把所选估计器、训练时访问节点数和推理时访问节点数分别记录，防止“训练时全树扫描、推理时宣称有限预算”的口径混淆。

### 9.3 梯度到底更新什么

对一个训练 episode：

\[
(x_1,x_2,\ldots,x_T,q,y^*)
\]

前向过程依次执行：

\[
e_t=E_w(x_t)
\]

\[
M=\mathcal{T}_{\theta_f}(e_1,\ldots,e_T)
\]

\[
R=\operatorname{PartialUnfold}_{\theta_r}(M,q;B)
\]

\[
H'=\operatorname{Mix}_{\theta_m}(H_q,R)
\]

\[
\mathcal{L}=\operatorname{CE}(D(H'),y^*)
\]

若计算图连通，链式法则会产生三类梯度：

\[
\frac{\partial\mathcal{L}}{\partial\theta_m},\qquad
\frac{\partial\mathcal{L}}{\partial\theta_r},\qquad
\frac{\partial\mathcal{L}}{\partial\theta_f}
\]

它们分别训练“怎样融合”“展开哪里”和“怎样折叠”。这仍不保证能找到好协议，只说明学习信号有一条明确路径进入三组参数。协议是否形成，最终必须由预算曲线和因果干预判断，而不是由公式命名。

## 10. 同一份状态可以有多个记忆协议

同一个长期状态 \(M\) 可以面对不同读取协议：

\[
R_{\mathrm{grep}}(M,q)\rightarrow\text{原文}
\]

\[
R_{\mathrm{QA}}(M,q)\rightarrow\text{回答}
\]

GrepCode 协议可能需要展开到较细分辨率；问答协议可能在较粗状态就已足够。两者没有高低之分，只是在相同容量和延迟约束下完成不同目标。

这也说明“理解”不能被偷换成内部必须出现某个语法槽位。更谨慎的定义是：

> 在特定读写协议下，TreeHeap 状态能够稳定产生我们称为检索、问答、续写或推理的行为。

## 11. 怎么证明答案真的来自记忆

“西西弗斯推石头”不是一个好的唯一测试，因为模型参数可能早已学过这个故事。即使完全没有读取当前的 \(M\)，它也可能回答正确。

更可靠的实验应该使用模型不可能预先知道的临时事实：

```text
写入：蓝七正在把紫色方块搬进北屋。
查询：谁在搬紫色方块？
期望：蓝七。

查询：方块被搬到哪里？
期望：北屋。
```

然后执行成组对照：

1. 写入前询问，模型不应知道答案；
2. 写入后询问，答案应改变；
3. 清零 \(R\) 或禁止 UNFOLD，答案应受损；
4. 交换对应 detail/subheap，答案应跟随状态改变；
5. 连续写入无关事实后，旧事实仍应在注册预算内可读；
6. 增加预算应形成可解释的质量曲线，而不是完全无效；
7. 完整展开是质量上界，随机展开是结构对照。

需要记录的指标至少包括：

| 指标 | 回答的问题 |
|---|---|
| Retrieval/Answer accuracy | 取回状态和最终回答是否正确 |
| Visited nodes | 实际访问了多少 TreeHeap 节点 |
| Retrieved state size | 有多少状态进入现实 H |
| Latency | 一次查询花了多久 |
| Capacity | M 中承载了多少经历 |
| Intervention damage | 清零、交换或随机展开造成多少损伤 |

只有同时出现任务收益、预算收益和状态干预因果性，我们才能说系统使用了 TreeHeap 记忆协议。

## 12. 当前边界与下一步

TNM 现在只有逻辑原型，还没有长期记忆 proof。已有基础与缺口是：

| 问题 | 当前基础 | 仍然缺少 |
|---|---|---|
| M 能否形成 TreeHeap | 有递归 FOLD/UNFOLD | 连续经历的写入布局 |
| 局部变换能否闭合 | lifting 公式和数值证据支持 | 长时更新稳定性 |
| 私有协议能否训练 | Echo、翻译和生成已有部分证据 | 记忆读取协议证据 |
| R 能否有限预算合成 | 本文给出 Partial UNFOLD 原型 | 代码与质量--预算曲线 |
| R 能否改变现实 H | 有 Mix 接口定义 | 因果干预 proof |

为了避免把公式、设计和实验结论混成一件事，本文最后按证据等级重新列一次：

| 类型 | 当前内容 |
|---|---|
| 由公式直接成立 | 局部 lifting 的显式逆；完整 root+details 保持总自由度；frontier 展开保持全叶覆盖且互不重叠；展开 \(B\) 次得到 \(B+1\) 个 frontier 节点 |
| 在指定实现条件下成立 | 已知写入地址时局部更新经过 \(O(\log N)\) 个祖先；缓存局部分数并使用优先队列时，预算读取成本为 \(O(B(C_U+C_K)+B\log B)\) |
| 候选算法，尚未证明 | query-conditioned stop/left/right/both kernel；straight-through 路由训练；TreeHeap-native Mix |
| 必须由实验回答 | 是否能形成有用私有协议；少量展开是否接近全树质量；长期写入是否干扰旧记忆；是否获得实际存储压缩 |

下一步不应该立即实现智能遗忘，也不应该先造一个大规模外部索引。更合理的是在固定容量 TreeHeap 上实现一次 Query-Conditioned Partial UNFOLD，验证它是否能在受限节点预算下，从临时事实中合成可用的 \(R\)。

## 结语

TNM 不是要把过去全部塞进当前上下文，也不是要把 TreeHeap 改造成另一棵 B+ Tree。它要研究的是：过去能否被折叠成一棵多分辨率 TreeHeap，并在现实问题到来时，只展开足够回答问题的部分。

```text
长期记忆 M
   + 当前现实 H
   ↓ query 条件下的局部 UNFOLD
取回状态 R
   ↓ Mix
新的现实状态 H'
   ↓ Decoder
结果
```

这不是关于记忆的最终答案，但它已经是一份可以计算访问预算、可以编写接口、也可以被实验否定的逻辑原型。

完整代码、ARA 与实验记录继续保存在 [SameTime 开放仓库](https://github.com/houming818/sametime)。

---

**License:** GPLv3。本文公开 TNM 的问题定义、数学接口与可证伪方向，允许复现、审计和修改，但衍生工作须保留相同开源许可。
