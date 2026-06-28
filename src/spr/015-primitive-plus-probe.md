---
title: "[SPR-015] primitive plus 实验：把 proof 变成可测的 TreeHeap toy"
date: 2026-06-19
weight: 15
author: nio (Houming818) & Codex Review
description: "用中国大陆本科数学口径解释 primitive_plus_probe：arr[0]、plus、mod base、信息量增长、循环窗口和 kernel 匹配。"
tags: [SPR, TreeHeap, Algebra, Primitive, Experiment]
---

# primitive plus 实验：把 proof 变成可测的 TreeHeap toy

这篇文章解释刚跑完的实验：

```text
primitive_plus_probe.py
```

它对应 ARA 里的：

```text
P-MATH02: Semantic primitive and plus operator
```

这次实验不是语言实验。

不是翻译实验。

不是 WMT。

它是一个纯数学 toy，用来验证一个非常小的想法：

```text
如果 TreeHeap 是一个可寻址的堆结构，
那么 plus 能不能同时承担三件事：

1. successor：走到下一个地址
2. information gain：增加信息量
3. mod fold：超过 base 后折回前面的地址
```

如果这个 toy 都跑不通，就没必要急着谈真实语言里的 TreeHeap 卷积。

## 先说结论

这轮 toy 实验通过了：

```text
pilot_pass = true
successor_ok = true
info_gain_pre_base = true
info_saturates_after_base = true
mod_fold_targets = [0, 1]
mod_fold_ok = true
kernel_hit_at_1 = 1.0
wrap_breaks_old_kernel = true
```

用人话说：

```text
plus 可以从 arr[0] 写到 arr[7]。
base=8 满了以后，再 plus 会折回 arr[0]、arr[1]。
base 没满前，信息量每次 +1。
base 满了以后，信息量不再增加，而是覆盖旧位置。
循环窗口 kernel 能找到 [p0, p1, p2]。
覆盖 arr[0] 后，旧 kernel 分数下降。
```

这说明：

```text
plus = successor + information gain + mod fold
```

至少在这个合成 toy 里是成立的。

## 为什么要做这个实验

前面我们讨论 TreeHeap 卷积。

卷积需要一个有序空间。

一维卷积里，这个空间是：

```text
x[0], x[1], x[2], ..., x[n-1]
```

如果加上取模：

```text
x[(i + 1) mod n]
```

它就变成一个循环空间。

但是 TreeHeap 不是普通数组。

所以问题变成：

```text
TreeHeap 的有序空间从哪里来？
```

如果只是人工编号：

```text
0, 1, 2, 3, ...
```

那只是工程索引。

我们真正想找的是：

```text
这个顺序能不能由 plus 生成？
```

也就是：

```text
H_{n+1} = plus(H_n, primitive)
```

这个实验就是把这个 proof 变成可测程序。

## TreeHeap 对象怎么定义

这次不用单个向量表示 TreeHeap。

我们明确使用可寻址数组：

```text
TreeHeapState = {
  arr: Node[]
  base: int
  cursor: int
  summary: vector
  step: int
}
```

其中：

```text
arr[0] = root
```

这是你指出的关键点。

如果 TreeHeap 是数组式堆，那么 root 本来就在：

```text
arr[0]
```

所以 root 不需要额外幻想出来。

真正重要的是：

```text
arr 是主状态。
summary 只是投影。
```

不要反过来把 summary 当成整棵树。

## 数组堆的地址规律

这次使用二叉堆的本科数据结构公式：

```text
root = 0
left(i) = 2i + 1
right(i) = 2i + 2
parent(i) = floor((i - 1) / 2)
```

例如 `base = 8`：

```text
index: 0 1 2 3 4 5 6 7
```

树关系是：

```text
0
├─ 1
│  ├─ 3
│  └─ 4
└─ 2
   ├─ 5
   └─ 6
```

`7` 是下一层的第一个节点。

这说明 TreeHeap 不是无序集合。

它有地址，有父子关系，也可以有线性顺序。

## 取模 base

这次设置：

```text
base = 8
```

地址只有：

```text
0, 1, 2, 3, 4, 5, 6, 7
```

如果再往后写，就用取模：

```text
target = (cursor + 1) mod base
```

这就是整数模群里最基础的：

```text
Z / 8Z
```

也就是：

```text
0,1,2,3,4,5,6,7,0,1,2,...
```

群论里可以把它看成一个循环群。

但这里只需要理解：

```text
超过 7，就回到 0。
```

## plus 怎么定义

这次的 `plus` 很简单：

```text
plus(H, primitive):
  target = (cursor + 1) mod base
  arr[target] = primitive
  summary = summarize(arr)
```

也就是说：

```text
plus 不是向量加法。
plus 是对 TreeHeap 地址空间的一次写入。
```

它做三件事：

1. 找下一个地址。
2. 把新 primitive 写进去。
3. 更新 summary。

如果用 `[ ]` 表示空 TreeHeap，那么：

```text
H0 = []
H1 = plus(H0, p0)
H2 = plus(H1, p1)
...
```

实际写入顺序是：

```text
step 1: p0 -> arr[0]
step 2: p1 -> arr[1]
step 3: p2 -> arr[2]
...
step 8: p7 -> arr[7]
step 9: p8 -> arr[0]
step 10: p9 -> arr[1]
```

这就是 successor：

```text
n -> n + 1
```

也是 mod fold：

```text
n + base -> n
```

## 信息量怎么测

你说：

```text
[] 信息量是 0
[cat] 信息量是 1
[cat, run] 信息量是另一个值
```

这次 toy 先用最简单的信息量：

```text
I(H) = 非空节点数量
```

也就是：

```text
I([]) = 0
I([p0]) = 1
I([p0, p1]) = 2
```

这个指标很粗。

但适合第一版 toy。

因为我们只是想验证：

```text
base 没满之前，plus 是否增加信息量？
```

实验结果：

```text
step 1: info 0 -> 1
step 2: info 1 -> 2
step 3: info 2 -> 3
...
step 8: info 7 -> 8
```

所以：

```text
info_gain_pre_base = true
```

到了 `base = 8` 以后，数组满了。

这时再 plus：

```text
step 9: p8 -> arr[0]
```

它不是新增第 9 个格子。

它覆盖 `arr[0]`。

所以信息量保持：

```text
8 -> 8
```

实验结果：

```text
info_saturates_after_base = true
```

这说明 plus 有两个阶段：

```text
base 未满：信息增长
base 已满：模折叠 / 覆盖 / 循环更新
```

## summary 是什么

实验里每个 primitive 是一个 64 维向量：

```text
p0, p1, ..., p9 ∈ R^64
```

TreeHeap 的 `summary` 也是一个向量。

但它不是主状态。

主状态是：

```text
arr
```

summary 是从 arr 算出来的投影：

```text
summary = summarize(arr)
```

代码里用了一个简单的地址敏感求和：

```text
summary = normalize(Σ roll(node.value, shift(index)))
```

这里用到了线性代数：

```text
向量求和
归一化
向量距离
余弦相似度
```

`roll` 的意思是按地址改变向量坐标，让同一个 primitive 放在不同地址时，对 summary 的影响不同。

这相当于给地址一个位置编码。

实验检查：

```text
summary_consistency_ok = true
```

意思是：

```text
summary 每次都确实等于 summarize(arr)，没有和 arr 脱节。
```

还有：

```text
summary_min_delta = 0.4124
```

意思是每次 plus 后，summary 都发生了明显变化。

## kernel 是怎么测的

我们定义一个循环窗口：

```text
window(i) = [
  arr[(i - 1) mod base],
  arr[i],
  arr[(i + 1) mod base]
]
```

这就是一维卷积最小窗口：

```text
[-1, 0, +1]
```

然后设置 kernel：

```text
K = [p0, p1, p2]
```

在 base 填满后：

```text
arr[0] = p0
arr[1] = p1
arr[2] = p2
```

所以以 `i = 1` 为中心：

```text
window(1) = [arr[0], arr[1], arr[2]]
          = [p0, p1, p2]
```

应该完全匹配。

实验结果：

```text
kernel_hit_at_1 = 1.0
kernel_top_score = 1.0
```

这说明循环 kernel 能在地址环上找到正确窗口。

## 覆盖以后为什么分数下降

第 9 步：

```text
p8 -> arr[0]
```

于是原来的：

```text
[p0, p1, p2]
```

变成：

```text
[p8, p1, p2]
```

这时再用旧 kernel：

```text
K = [p0, p1, p2]
```

去匹配，分数应该下降。

实验结果：

```text
kernel_top_score = 1.0
kernel_after_wrap_top_score = 0.6731
wrap_breaks_old_kernel = true
```

这说明：

```text
mod fold 不是空操作。
它真的改变了局部结构。
```

这点重要。

因为如果折回以后 kernel 分数不变，说明地址环没有真正影响结构。

## 概率论在这里怎么出现

这次没有做复杂概率模型。

但有一个概率容器思想的前置形式：

```text
对每个 center 计算 kernel score
然后按分数排序
```

这还不是 softmax 概率。

但它已经是概率容器之前的一步：

```text
候选位置集合 + 分数
```

下一步可以把分数变成概率：

```text
P(i) = exp(score(i)) / Σ exp(score(j))
```

这就是本科概率论里常见的归一化思想。

先有 score。

再有 probability。

最后才有 collapse。

## 这次到底 proof 了什么

这次不是证明 TreeHeap 会推理。

它 proof 的是一个很窄的数学命题：

```text
在一个可寻址 TreeHeap toy 里，
plus 可以被定义为 successor 写入；
在 base 未满时增加信息量；
在 base 满后按 mod 折回；
循环窗口 kernel 可以在这个地址环上匹配局部模式。
```

对应实验结果全部通过：

```text
closure_ok = true
root_ok = true
successor_ok = true
info_gain_pre_base = true
info_saturates_after_base = true
mod_fold_ok = true
kernel_hit_at_1 = 1.0
wrap_breaks_old_kernel = true
```

这说明：

```text
P-MATH02 作为 M0 toy 成立。
```

但这还不是语言 claim。

## 这次没有证明什么

它没有证明：

```text
真实语义空间里一定有 primitive
真实 TreeHeap checkpoint 已经学到 plus
TreeHeap 会翻译
TreeHeap 会推理
kernel 能处理真实句子
```

这些都还要后续实验。

这次只是把地基往前铺了一格。

## 下一步怎么走

下一步应该做两个方向。

第一，把信息量从：

```text
非空节点数量
```

升级为：

```text
rank
entropy
description length
reconstruction bits
distinguishability
```

第二，把 primitive 从人工 `p0,p1,...` 换成可学习的 basis：

```text
learned primitive basis
```

也就是问：

```text
模型能不能自己找到那个类似“1”的基元？
```

然后才进入：

```text
TreeHeap-object echo
structure invariant
S2 translation
```

## 一句话

这次实验把一句抽象话：

```text
TreeHeap 需要 primitive 和 plus 来生成有序性。
```

变成了可测 toy：

```text
arr[0] 是 root。
plus 写入下一个地址。
base 前信息量增长。
base 后按 mod 折回。
kernel 能在循环地址环上滑动。
```

这就是进入 Echo 之前，TreeHeap 工具箱需要补上的数学基础。

> **License: GPLv3**
