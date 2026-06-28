---
title: "[SPR-019] Soft TreeHeap：梯度如何进入树堆结构"
date: 2026-06-22
weight: 19
author: nio (Houming818) & Codex Review
description: "把 TreeHeap 接入机器学习：用 kernel-guided soft plus、soft route 和多核训练让梯度进入树堆算子，并提出 claim、predict、proof 和实验方案。"
tags: [SPR, TreeHeap, Gradient, SoftTreeHeap, Experiment]
---

# Soft TreeHeap：梯度如何进入树堆结构

上一篇 `SPR-018` 把 TreeHeap 的目标说清楚了：

```text
TreeHeap 不是要证明自己完全不同。
TreeHeap 要证明自己和 MLP / CNN / Transformer 一样，
也是一种可以构造预测函数的机器学习结构。
```

但这会立刻遇到一个核心问题：

```text
梯度怎么进入 TreeHeap？
```

线性回归为什么能学习？

因为它有：

```text
y_hat = W x + b
loss = MSE(y_hat, y)
gradient = d loss / d W
update W
```

训练结束后，数据里的规律被蒸馏进参数：

```text
W, b
```

Transformer 也是类似的，只是参数从一个简单矩阵，变成很多矩阵：

```text
Wq, Wk, Wv, Wo, FFN weights
```

loss 仍然通过梯度，把数据里的统计规律写进参数矩阵。

那么 TreeHeap 呢？

如果 TreeHeap 只是硬指针：

```text
if query < node.key:
  go left
else:
  go right
```

或者硬写入：

```text
arr[3] = value
```

那梯度很难传进去。

所以第一版 TreeHeap 不能直接从 hard tree 开始。

我们需要：

```text
Soft TreeHeap
```

也就是：

```text
硬树堆结构的连续松弛版本。
```

## 一句话 Claim

当前 claim 是：

```text
如果把 TreeHeap 的写入、路由、停止、读取都改成可微的 soft distribution，
那么 TreeHeap 就可以像 MLP / Transformer 一样用 loss 和 gradient 学习。

梯度会被写入：
node_key
node_value
write kernel
query kernel
decoder kernel
```

这不是最终证明。

这只是进入机器学习的入口。

如果这个 claim 不成立，TreeHeap 后面不用谈 WMT，也不用谈世界模型。

## 从 Hard TreeHeap 到 Soft TreeHeap

这里有一个很容易误解的点：

```text
Soft TreeHeap 不是推翻前面建立的 TreeHeap 数学基础。
```

更准确的说法是：

```text
Hard TreeHeap 是离散代数对象。
Soft TreeHeap 是它的概率提升，也就是可微近似。
```

原来的 TreeHeap 有确定的地址、确定的子树、确定的路由。

例如一个 hard 操作可以写成：

```text
O_a(H)
```

意思是：

```text
在地址 a 上，对 TreeHeap H 做一次确定操作。
```

比如：

```text
在地址 a 上执行 TreeHeap plus
读取 left(root)
沿着 root -> left -> right 走
在某个 subheap 上做 kernel matching
```

这些都是 hard TreeHeap 的操作。

Soft 以后，不是把这些操作删掉。

Soft 以后变成：

```text
SoftO(H) = sum_a p(a) * O_a(H)
```

翻译成人话就是：

```text
模型暂时不知道应该操作哪个地址，
所以它对多个地址都做一点操作，
每个地址的权重由概率 p(a) 决定。
```

如果概率分布是：

```text
p(5) = 1.0
其他地址 = 0.0
```

那么：

```text
SoftO(H) = O_5(H)
```

也就是说：

```text
Soft TreeHeap 会退化回 Hard TreeHeap。
```

这非常重要。

因为它说明：

```text
Soft TreeHeap 不是另一种东西。
它是 Hard TreeHeap 的连续版本。
```

可以把关系表写成这样：

| Hard TreeHeap | Soft TreeHeap |
|---|---|
| 一个确定地址 | 一个地址概率分布 |
| `H_next = H ⊕_a x` | `sum_a p(a) * (H ⊕_a x)` |
| `left / right / stop` | `p_left / p_right / p_stop` |
| 一个确定子树 | 子树概率分布 |
| 一个确定卷积核位置 | 多个 subheap 上的加权 kernel |
| hard collapse | 低温 softmax / top-k / argmax collapse |

所以 Soft TreeHeap 的本质不是：

```text
把树堆变成普通向量。
```

而是：

```text
让 TreeHeap 的地址、路径、子结构都能携带概率。
```

这样 loss 才能通过概率分布反传。

### 一个小例子

hard 查询是：

```text
query = 6

root = 8
6 < 8
go left
```

soft 查询是：

```text
query = 6
root = 8

stop: 0.05
left: 0.85
right: 0.10
```

这时模型还没有完全确定。

它主要相信：

```text
应该 go left
```

但仍然保留一点：

```text
stop / right 的可能性。
```

如果后面发现答案错了，loss 可以反向告诉它：

```text
left 的概率应该再高一点；
right 的概率应该再低一点；
当前 node_key / query_kernel 应该如何调整。
```

这就是梯度进入 TreeHeap 的入口。

### 但这里有一个工程边界

完整的概率 TreeHeap 应该保存：

```text
所有可能 TreeHeap 的概率分布。
```

这是最干净的数学版本。

但它太贵。

因为树一大，可能结构数量会爆炸。

工程上更可能采用的是近似版本：

```text
每个 node 保存一个 value 分布；
每条 route 保存一个 action 分布；
每个 kernel 保存一个 soft attention 分布。
```

这可以叫：

```text
mean-field Soft TreeHeap
```

它的好处是能训练。

它的风险是：

```text
可能丢失不同路径之间的相关性。
```

所以后续实验不能只看任务准确率。

还要看：

```text
Soft 近似是否破坏了 TreeHeap 原来的代数结构？
```

例如：

```text
hard collapse 以后，是否还能得到合法树？
soft route 是否真的收敛到可解释路径？
subheap kernel 是否还能迁移？
```

这会成为后续 proof 的一部分。

## 为什么 hard TreeHeap 不适合第一版训练

假设我们有一个硬查询 kernel：

```text
if query == node.key:
  return stop
if query < node.key:
  return left
if query > node.key:
  return right
```

这个逻辑很清楚，但对梯度不友好。

因为模型一旦选择：

```text
left
```

它就完全不走：

```text
right
```

如果最后错了，loss 很难告诉模型：

```text
其实刚才 right 更好。
```

同样，硬写入也有问题：

```text
arr[5] = value
```

如果写错位置，梯度很难平滑地告诉 encoder：

```text
你应该往 arr[4] 写 0.2，往 arr[5] 写 0.8。
```

所以第一版必须用 soft 版本。

## Soft Write 的弱版本：神经内存写入

先承认一个问题。

如果我们把可微写入写成：

```text
write_logits = encoder(x, H)
write_prob = softmax(write_logits)
```

然后直接更新数组槽位：

```text
arr_new[i] =
  (1 - write_prob[i]) * arr_old[i]
+ write_prob[i] * write_vector
```

这确实是可微的。

但它更像：

```text
neural memory write
```

也就是神经网络记忆槽更新。

它的问题是：

```text
梯度进入了 arr，
但没有真正进入 TreeHeap 的 plus 算子。
```

换句话说，它能证明：

```text
一个数组内存可以被 softmax 写入。
```

但它不能证明：

```text
TreeHeap 的加法、路径、子结构、卷积核可以被学习。
```

所以这个写法只能作为：

```text
baseline
教学反例
最低可微版本
```

不能作为 TreeHeap 的正式写入机制。

正式机制应该是：

```text
Soft Write = Soft Plus
```

更进一步：

```text
Soft Write = Kernel-guided Soft Plus
```

## Soft Plus：对 TreeHeap 加法的概率提升

先定义 hard plus。

假设：

```text
H = 当前 TreeHeap
x = 新输入的 token / node / 小 TreeHeap
a = 一个地址或路径
```

hard 写入不是：

```text
arr[a] = x
```

而是：

```text
H_next = H ⊕_a x
```

其中：

```text
⊕_a
```

表示：

```text
在地址 a 上，把 x 按 TreeHeap 的规则并入 H。
```

这个规则可以包含：

```text
路径比较
子树重排
局部 merge
权重更新
父子关系维护
```

这才是 TreeHeap 的加法味道。

Soft plus 不是直接改数组。

Soft plus 是：

```text
H_next = sum_a p(a | H, x) * (H ⊕_a x)
```

翻译成人话：

```text
模型不知道 x 应该插入哪个地址，
所以它先生成多个候选 TreeHeap：

candidate_a = H ⊕_a x

然后按概率把这些候选结构混合起来。
```

如果：

```text
p(left.right) = 1.0
其他地址 = 0.0
```

那么：

```text
H_next = H ⊕_{left.right} x
```

这就退化回 hard TreeHeap plus。

所以 Soft Plus 仍然继承原来的 TreeHeap 数学基础。

它不是：

```text
矩阵内存插值。
```

它是：

```text
TreeHeap plus 算子的 soft lifting。
```

## Kernel-guided Soft Plus：用卷积核决定写入

还有一个更关键的问题：

```text
p(a | H, x) 从哪里来？
```

如果只是让一个普通 encoder 直接输出所有地址概率：

```text
p(a) = softmax(MLP(H, x))
```

那仍然有点像普通注意力。

更符合 TreeHeap 的方案是：

```text
p(a) 由 TreeHeap convolution kernel 计算出来。
```

也就是：

```text
score(a) = K_write(subheap(H, a), x)
p(a) = softmax(score(a))
```

其中：

```text
K_write
```

是一个可微卷积核。

它观察：

```text
当前位置的 subheap
新输入 x
局部路径
局部 key/value/weight
局部结构 pattern
```

然后判断：

```text
x 是否应该写到这个位置；
x 是否应该继续往 left；
x 是否应该继续往 right；
x 是否应该在这里 stop 并 merge。
```

这样，写入就不再是 hardcode：

```text
if x < node.key:
  go left
```

而是变成可微 kernel：

```text
local_feature = phi(subheap(H, a), x)

score_stop  = w_stop  · local_feature
score_left  = w_left  · local_feature
score_right = w_right · local_feature

p_action = softmax([score_stop, score_left, score_right])
```

这个 `K_write` 就是 TreeHeap 上的卷积核。

它不是二维图像卷积核。

但它做的是同一类事情：

```text
在局部结构上滑动；
提取局部 pattern；
给出下一步操作分数。
```

图像卷积看的是：

```text
3x3 pixel patch
```

TreeHeap 卷积看的是：

```text
root -> left/right 的小 subheap
```

例如：

```text
        8
      /   \
     4     12
```

现在插入：

```text
x.key = 6
```

卷积核在 root=8 看到：

```text
6 更像应该去 left
```

于是输出：

```text
stop:  0.05
left:  0.90
right: 0.05
```

到 node=4 时，它看到：

```text
6 更像应该去 right
```

输出：

```text
stop:  0.05
left:  0.05
right: 0.90
```

到空位或 node=6 时，它输出：

```text
stop:  0.95
left:  0.025
right: 0.025
```

然后执行：

```text
H_next = sum_a write_mass[a] * (H ⊕_a x)
```

这里的 `write_mass[a]` 不是外部指定的。

它来自 kernel 在树上的逐步传播：

```text
mass[root] = 1

for step in search_steps:
  for each active address a:
    p_action = K_write(subheap(H, a), x)

    write_mass[a]       += mass[a] * p_stop
    mass_next[left(a)]  += mass[a] * p_left
    mass_next[right(a)] += mass[a] * p_right
```

最后：

```text
H_next = sum_a write_mass[a] * Plus_a(H, x)
```

这才是 TreeHeap 版本的可微写入。

它的梯度链条是：

```text
loss
↓
H_next
↓
sum_a write_mass[a] * Plus_a(H, x)
↓
write_mass[a]
↓
K_write(subheap(H, a), x)
↓
kernel parameters
```

所以梯度进入的不是普通内存槽。

梯度进入的是：

```text
TreeHeap convolution kernel
TreeHeap plus candidates
TreeHeap route distribution
TreeHeap collapse path
```

这比 naive soft memory write 更接近我们的目标。

## Soft Route：可微路径选择

硬路由是：

```text
go left
```

Soft route 是：

```text
action_logits = query_kernel(query, node)
action_prob = softmax(action_logits)
```

输出：

```text
{
  stop:  0.10,
  left:  0.75,
  right: 0.15
}
```

这表示：

```text
当前更可能应该走 left，
但 right 和 stop 仍然保留少量概率。
```

如果当前节点有流量：

```text
mass[i] = 0.80
```

那么下一步传播：

```text
stop_mass[i]        += 0.80 * 0.10
mass_next[left(i)]  += 0.80 * 0.75
mass_next[right(i)] += 0.80 * 0.15
```

也就是：

```text
stop_mass[i]        += mass[i] * p_stop
mass_next[left(i)]  += mass[i] * p_left
mass_next[right(i)] += mass[i] * p_right
```

跑多步以后，输出可以是：

```text
y_hat = sum_i stop_mass[i] * node_value[i]
```

或者分类任务里：

```text
logits = sum_i stop_mass[i] * node_logits[i]
```

这仍然是可微的。

梯度能进入：

```text
query kernel
node_key
node_value
路径概率
```

## 一个完整 Toy：查找 key/value

任务：

```text
输入一组 key/value
查询一个 key
输出对应 value
```

样本：

```text
pairs = [(8,A), (4,B), (12,C), (2,D), (6,E), (10,F), (14,G)]
query = 6
target = E
```

理想结构是：

```text
          8:A
         /   \
      4:B     12:C
     /  \     /   \
  2:D   6:E 10:F 14:G
```

如果是硬查找：

```text
6 < 8  -> left
6 > 4  -> right
6 == 6 -> stop
output = E
```

Soft TreeHeap 不会一开始这么硬。

第 1 步在 root：

```text
node.key = 8
query = 6
```

query kernel 输出：

```text
stop:  0.05
left:  0.85
right: 0.10
```

第 2 步进入左子树，节点是 `4:B`：

```text
node.key = 4
query = 6
```

输出：

```text
stop:  0.05
left:  0.10
right: 0.85
```

路径概率：

```text
root -> left -> right
= 0.85 * 0.85
= 0.7225
```

第 3 步到 `6:E`：

```text
node.key = 6
query = 6
```

输出：

```text
stop:  0.80
left:  0.10
right: 0.10
```

最终命中路径概率：

```text
root -> left -> right -> stop
= 0.85 * 0.85 * 0.80
= 0.5780
```

如果模型输出了 `E`，loss 下降。

如果模型输出错了，loss 反传，梯度会告诉系统：

```text
哪些节点 key/value 需要调整
哪些路由概率需要调整
哪个写入位置更合理
```

这就是 TreeHeap 的梯度学习过程。

## Loss 不应该一开始大锅炖

上面讲了：

```text
loss 可以进入 Soft TreeHeap。
```

但这不等于说：

```text
所有 loss 都应该一开始混在一起。
```

一个很自然的教学写法是：

```text
L =
  L_task
+ alpha * L_order
+ beta  * L_depth
+ gamma * L_entropy
```

这个式子适合帮助读者理解：

```text
任务正确性、结构合法性、路径长度、概率坍缩
都可以变成训练信号。
```

但它不一定是好的工程设计。

因为多个 loss 直接相加，会遇到几个问题：

```text
梯度方向可能互相抵消；
某个 loss 的尺度太大，压住其他 loss；
结构 loss 太早生效，导致模型过早坍缩；
熵 loss 太强，导致模型一直不敢做决定；
多个目标一起训练，难以知道到底哪个 kernel 学坏了。
```

这和 Transformer 的经验类似。

Transformer 不是只用一个观察角度看序列。

它用了：

```text
multi-head attention
```

不同 head 可以学习不同关系。

TreeHeap 也应该类似。

更合理的设计不是：

```text
一个巨大 loss 控制所有东西。
```

而是：

```text
多个 TreeHeap kernel / head 各自学习一种结构能力。
```

## Multi-kernel TreeHeap

可以先把 Soft TreeHeap 拆成几个 head。

| Head | 学什么 | 主要梯度来源 |
|---|---|---|
| plus/kernel head | 输入应该通过哪个 subheap kernel 并入 TreeHeap | reconstruction / lookup / structure loss |
| route head | 查询时走 stop/left/right | lookup task loss |
| order head | 是否形成有序树 | order violation loss |
| depth head | 路径是否短 | expected depth loss |
| prefix head | 高频符号是否更短 | compression loss |
| collapse head | 什么时候从概率变成确定结构 | entropy / temperature schedule |

这样每个 head 都比较清楚。

例如查找任务里，route head 主要学：

```text
query 和当前 node 的关系。
```

order head 主要学：

```text
left_key < root_key < right_key
```

prefix head 主要学：

```text
高频符号走短路径。
```

这些目标不一定应该同时强行压到一个参数空间里。

更好的方式是：

```text
让不同 kernel 先学会自己的局部规律，
再由上层组合。
```

## Loss 设计一：任务 Head

任务 head 只负责最终答案。

如果输出是分类：

```text
L_task = cross_entropy(y_hat, target)
```

如果输出是连续值：

```text
L_task = MSE(y_hat, target)
```

例如 key/value 查找任务：

```text
target = E
y_hat = soft_query(H, query)
L_task = cross_entropy(y_hat, E)
```

这个 head 回答：

```text
最后答案对不对？
```

它不直接负责：

```text
树是否漂亮；
路径是否最短；
概率是否已经坍缩。
```

## Loss 设计二：Order Head

如果任务是有序查找树，可以单独给 order head 一个结构目标。

例如：

```text
left_key < root_key < right_key
```

用 hinge loss 写：

```text
L_order =
  max(0, left_key - root_key + margin)
+ max(0, root_key - right_key + margin)
```

如果左子节点比 root 还大，就会罚。

如果右子节点比 root 还小，也会罚。

这个 head 的作用不是替代任务 loss。

它的作用是：

```text
让 TreeHeap 的内部结构更像可搜索结构。
```

这类似 CNN 的卷积结构偏置。

但区别是：

```text
CNN 的局部结构通常是人工固定的二维邻域；
TreeHeap 的局部结构是可学习的地址 / 子树 / 路由。
```

## Loss 设计三：Depth Head

如果查找绕很远，虽然答案对了，也不一定好。

可以单独训练一个 depth head：

```text
L_depth = expected_search_steps
```

例如：

```text
root -> left -> right -> stop
```

路径长度是 3。

如果模型绕成：

```text
root -> right -> left -> left -> right -> stop
```

路径更长，就会被罚。

这个 head 对应的是：

```text
搜索效率。
```

它可以晚一点加入。

因为训练早期模型还不会查找，如果太早惩罚路径长度，可能导致模型学会：

```text
为了路径短，直接 stop。
```

但答案是错的。

## Loss 设计四：Collapse Head

训练早期，我们允许不确定：

```text
left: 0.45
right: 0.40
stop: 0.15
```

训练后期，我们希望它逐渐清晰：

```text
left: 0.95
right: 0.03
stop: 0.02
```

所以可以使用 entropy 或 temperature schedule。

但这里要非常小心。

如果把 entropy loss 一开始就和 task loss 强行混在一起，可能出现两种坏情况。

第一种：

```text
过早坍缩。
```

模型还没学会结构，就已经把概率压成 one-hot。

后面错了也很难改。

第二种：

```text
长期不坍缩。
```

模型为了保留不确定性，永远不形成清晰路径。

所以 collapse head 更像一个控制器：

```text
early:  high temperature, allow exploration
middle: reduce temperature
late:   low temperature, encourage collapse
```

它不应该无脑和所有 loss 相加。

## 推荐训练方式：分阶段或交替训练

更合理的训练流程可以是：

```text
Stage 1:
  只训练 task head / route head。
  目标：答案能不能对。

Stage 2:
  加入 order head。
  目标：内部结构是否变成可搜索树。

Stage 3:
  加入 depth head。
  目标：路径是否更短。

Stage 4:
  加入 collapse head。
  目标：soft distribution 是否能稳定坍缩成 hard TreeHeap。
```

也可以采用交替训练：

```text
step 1: update route kernel
step 2: update write kernel
step 3: update order kernel
step 4: update collapse controller
```

必要时还可以使用：

```text
stop-gradient
freeze kernel
auxiliary probe
gradient clipping
loss normalization
```

这样做的好处是：

```text
每一种梯度信息都有自己的入口；
每个 kernel 学坏了都能被定位；
不会把所有目标搅在一起互相污染。
```

所以 SPR-019 的正式观点应该是：

```text
TreeHeap 可以通过 loss / gradient 学习，
但不应该依赖一个大锅炖总 loss。

TreeHeap 更合理的训练形态是：
multi-kernel + staged training + controlled collapse。
```

## Huffman-like 压缩任务的 Loss

如果任务是学习加权前缀树，loss 可以换成：

```text
L =
  L_reconstruct
+ lambda * L_length
+ mu * L_prefix_free
```

其中：

```text
L_reconstruct:
  decoder 是否能还原符号。

L_length:
  高频符号路径是否更短。

L_prefix_free:
  是否避免一个符号路径成为另一个符号路径的前缀。
```

例如符号频率：

```text
A: 0.50
B: 0.25
C: 0.15
D: 0.10
```

理想 Huffman-like 编码：

```text
A -> 0
B -> 10
C -> 110
D -> 111
```

平均路径长度：

```text
0.50 * 1
+ 0.25 * 2
+ 0.15 * 3
+ 0.10 * 3
= 1.75
```

固定长度编码是：

```text
2.00
```

所以 predict 是：

```text
如果 TreeHeap 能学习加权前缀树，
它的 expected path length 应该接近 Huffman oracle，
并低于 fixed-length baseline。
```

## Predict

当前 predict 分四层。

### Predict 1：可学习性

```text
Soft TreeHeap 的 loss 应该能下降。
```

最小任务：

```text
线性回归
二分类
XOR / parity
key/value lookup
```

如果这些都学不会，TreeHeap 不具备机器学习基本能力。

### Predict 2：可搜索编码

```text
在 key/value lookup 任务中，
TreeHeap encoder 应该能学习一种可被 query kernel 搜索的结构。
```

指标：

```text
query accuracy
expected search depth
OOD key count generalization
tree order violation rate
failure tail
```

### Predict 3：可压缩编码

```text
在 weighted prefix coding 任务中，
TreeHeap encoder 应该能学习接近 Huffman oracle 的路径分配。
```

指标：

```text
reconstruction accuracy
expected path length
prefix-free violation rate
gap to Huffman oracle
gap to fixed-length baseline
```

### Predict 4：Soft 版本不破坏 TreeHeap 代数

```text
如果 Soft TreeHeap 真的是 Hard TreeHeap 的概率提升，
那么当温度降低、分布接近 one-hot 时，
soft 结果应该接近对应 hard 操作的结果。
```

也就是：

```text
kernel-guided soft plus collapse 后，应该接近 hard plus；
soft route collapse 后，应该接近 hard route；
soft subheap kernel collapse 后，应该接近 hard subheap kernel；
soft learned tree collapse 后，应该仍然是合法 TreeHeap。
```

指标：

```text
hard-soft output gap
collapse legality rate
route interpretability
subheap relocation accuracy
gradient stability
```

## Proof 设计

为了证明 claim，需要最少四组实验。

### Experiment 0：Soft TreeHeap 能不能学习

目的：

```text
证明 TreeHeap 和 MLP 一样，可以通过 loss / gradient 学函数。
```

任务：

```text
linear regression
binary classification
XOR
small lookup
```

对比：

```text
MLP
Soft TreeHeap
```

判断：

```text
loss 是否下降；
accuracy 是否上升；
参数梯度是否非零；
训练是否稳定。
```

### Experiment 1：Learned Ordered Tree Search

目的：

```text
证明 encoder 能学习建一棵可搜索树。
```

任务：

```text
输入 N 个 key/value；
查询 key；
输出 value。
```

训练：

```text
N = 7, 15
```

测试外推：

```text
N = 31, 63
```

对比：

```text
flatten MLP
small Transformer
Soft TreeHeap
oracle BST
```

指标：

```text
accuracy
expected search depth
sample efficiency
OOD generalization
tree order violation
```

### Experiment 2：Learned Huffman-like Prefix Tree

目的：

```text
证明 encoder 能学习加权前缀压缩结构。
```

任务：

```text
输入符号频率；
encoder 输出 TreeHeap code；
decoder 根据路径还原符号。
```

对比：

```text
fixed-length code
Huffman oracle
MLP autoencoder
Soft TreeHeap prefix encoder
```

指标：

```text
reconstruction accuracy
expected code length
prefix-free violation
gap to Huffman oracle
```

### Experiment 3：Hard/Soft Consistency 与 Loss Ablation

目的：

```text
证明 Soft TreeHeap 没有破坏 Hard TreeHeap 的核心算子；
同时验证 multi-kernel 训练是否比大锅炖总 loss 更稳定。
```

这个实验分三部分。

第一半验证 hard/soft 一致性。

构造一个确定的 hard TreeHeap：

```text
        8
      /   \
     4     12
    / \    / \
   2   6  10 14
```

hard 查询：

```text
query = 6
8 -> left
4 -> right
6 -> stop
output = E
```

soft 查询使用同一棵树，但每一步不是确定动作，而是概率：

```text
at 8:
  stop  0.01
  left  0.98
  right 0.01

at 4:
  stop  0.01
  left  0.01
  right 0.98

at 6:
  stop  0.98
  left  0.01
  right 0.01
```

这时正确路径概率约为：

```text
0.98 * 0.98 * 0.98 = 0.941192
```

如果 temperature 继续降低，概率会更接近：

```text
1.0
```

那么 soft 输出应该收敛到 hard 输出：

```text
output_soft -> E
```

判断指标：

```text
hard-soft output gap 是否下降；
正确路径概率是否上升；
collapse 后路径是否合法；
collapse 后是否等于 hard route。
```

第二半验证写入机制。

同一个 key/value lookup 建树任务，比较三种写入方式：

```text
A: naive soft memory write
B: encoder soft plus
C: kernel-guided soft plus
```

A 是弱版本：

```text
arr_new[i] =
  (1 - p[i]) * arr_old[i]
+ p[i] * write_vector
```

它测试：

```text
普通神经内存写入能做到什么程度。
```

B 是中间版本：

```text
H_next = sum_a p(a | H, x) * (H ⊕_a x)
```

但 `p(a)` 由普通 encoder 给出。

它测试：

```text
只要有 soft plus，是否就足够。
```

C 是 TreeHeap 正式版本：

```text
score(a) = K_write(subheap(H, a), x)
p(a) = softmax(score(a))
H_next = sum_a p(a) * (H ⊕_a x)
```

它测试：

```text
用 TreeHeap 卷积核来决定写入位置，
是否比普通 encoder 更稳定、更可解释、更能外推。
```

判断指标：

```text
lookup accuracy
OOD N=31/63 accuracy
expected search depth
collapse legality rate
route interpretability
hard-soft output gap
subheap relocation accuracy
```

如果我们的判断正确，C 应该至少在这些地方更好：

```text
更容易形成可解释路径；
更容易坍缩成合法 TreeHeap；
在更大 N 上失败尾部更少；
对 subheap relocation 更稳。
```

第三半验证 loss 设计。

同一个 lookup 任务，比较三种训练方式：

```text
D: only task loss
E: 大锅炖总 loss
F: multi-kernel staged training
```

其中 E 是：

```text
L =
  L_task
+ alpha * L_order
+ beta  * L_depth
+ gamma * L_entropy
```

F 是：

```text
Stage 1: train route/task head
Stage 2: add order head
Stage 3: add depth head
Stage 4: add collapse head
```

如果我们的判断正确，F 应该更稳。

预期结果不是 F 在所有指标上都赢。

更具体的 predict 是：

```text
F 的梯度爆炸/消失次数更少；
F 的 collapse 更晚、更可控；
F 的 order violation 下降更平滑；
F 在 OOD N=31/63 上失败尾部更少；
E 可能训练更快，但更容易过早坍缩或目标对冲。
```

## Falsification：什么结果会否定我们

这也要写清楚。

如果出现这些结果，claim 就要降级：

```text
Soft TreeHeap 的 loss 不下降。
Soft route 梯度长期为 0 或爆炸。
TreeHeap lookup 不如同规模 MLP。
TreeHeap 无法外推到更大 N。
prefix tree 长度不如 fixed-length baseline。
soft collapse 后得不到合法 hard TreeHeap。
kernel-guided soft plus 不如 naive memory write。
multi-kernel 比大锅炖总 loss 更不稳定。
encoder 没有学出任何可解释结构。
```

这些结果说明：

```text
TreeHeap 可能只是复杂包装，
没有带来有效归纳偏置。
```

## 当前 Claim 的边界

到目前为止，我们还没有证明：

```text
Soft TreeHeap 一定能训练成功。
TreeHeap 一定优于 Transformer。
TreeHeap 能做 WMT。
Huffman-like 结构一定能通过梯度学出来。
```

现在只是确定了下一步要证明什么。

真正的 claim 是：

```text
TreeHeap 如果要作为机器学习结构存在，
必须能让梯度进入它的结构状态。

Soft write 不应该只是内存插值。

正式路径应该是：

kernel-guided soft plus、soft route、soft stop/read。

如果这条路径成立，
TreeHeap 就能像 MLP / Transformer 一样用 loss 学习；
并且可能在搜索、压缩、路径解码这类结构任务上表现更好。
```

这就是 `SPR-019` 要进入实验的地方。

> **License: GPLv3**
