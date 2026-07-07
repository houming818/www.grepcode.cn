---
title: "[SPR-046] 航行问题：TreeHeap route 点燃了，但 compact state 还没过海"
date: 2026-07-06
author: Codex Review
description: "SPR-046 记录 S1 route 的新位置：content-aware dense TreeHeap route 是第一次真正读堆内容的 route proof；compact 压缩版失败在随机 token sum 的精度损失上，下一步问题是 learned token/subheap embeddings。"
tags: [SPR, TreeHeap, ARA, S1, Routing, State]
---

# 航行问题：TreeHeap route 点燃了，但 compact state 还没过海

这篇不是庆功，也不是翻车记录。

更准确地说，它是一张航海图。

SPR-045 解决了一个很严重的审计问题：

```text
以前有些 echo / mirror 实验用的是 L x L route matrix。
那能恢复句子，但不是 TreeHeap route。
```

所以 SPR-045 重新要求：

```text
从 arr[1] 出发；
每一步只看当前 node；
输出 stop / left / right；
沿着 TreeHeap 地址递归走下去。
```

这才叫 TreeHeap route。

但 SPR-045 之后，DS 又指出一个新问题：

```text
route kernel 虽然递归走树，
但它读的是预计算几何区间 feature，
不是堆里真实装的 token / subheap state。
```

也就是说，它确实走树了，但像拿着答案地图走树。

所以 SPR-046 的问题变成：

> kernel 能不能真的读 `arr[i]`、`arr[left]`、`arr[right]` 的内容，然后决定 stop / left / right？

这一步很关键。

如果能，就说明 S1 route 第一次真正进入了 TreeHeap 的数据结构内部。

如果不能，说明我们仍然只是在做外部几何导航。

## 先把粗糙算法讲清楚

这里先用一个粗糙类比入门。

注意，这不是最终理论定义。

它只是帮本科读者先看见：

```text
TreeHeap route 至少不是 L x L 矩阵。
它必须在树地址上一步一步发生。
```

先看普通数组。

一句话可以写成：

```text
["I", "like", "small", "cats"]
```

如果只用数组，我们会说：

```text
第 0 个词是 I
第 1 个词是 like
第 2 个词是 small
第 3 个词是 cats
```

TreeHeap 会先把这句话放进一棵二叉堆。

为了简单，假设最多 4 个 leaf：

```text
              arr[1]
             /      \
        arr[2]      arr[3]
        /   \       /   \
    arr[4] arr[5] arr[6] arr[7]
      I    like   small  cats
```

这里有一个很重要的规则：

```text
left child  = arr[2i]
right child = arr[2i + 1]
```

例如：

```text
arr[1] 的 left  是 arr[2]
arr[1] 的 right 是 arr[3]
arr[2] 的 left  是 arr[4]
arr[2] 的 right 是 arr[5]
```

leaf 里面放具体 token。

internal node 里面放这个子树的摘要。

比如：

```text
arr[2] 表示 ["I", "like"] 这个子堆
arr[3] 表示 ["small", "cats"] 这个子堆
arr[1] 表示整句话 ["I", "like", "small", "cats"]
```

现在问一个问题：

> query = "cats"，怎么从 root 找到它？

TreeHeap route 的走法是：

```text
从 arr[1] 开始。

看当前 node、left child、right child。

如果 query 更像在 left 里，就走 left。
如果 query 更像在 right 里，就走 right。
如果当前 node 已经是答案，就 stop。
```

对 `"cats"` 来说，路线应该是：

```text
arr[1] -> right -> arr[3] -> right -> arr[7] -> stop
```

用动作表示：

```text
right, right, stop
```

如果 query 是 `"like"`，路线就是：

```text
arr[1] -> left -> arr[2] -> right -> arr[5] -> stop
```

动作是：

```text
left, right, stop
```

所以 TreeHeap route 的本质是：

```text
用一串 stop / left / right 动作，
在堆地址里递归查找目标。
```

这和一个 `L x L` 矩阵完全不同。

`L x L` 矩阵像这样：

```text
我要第 3 个输出，所以直接从第 0/1/2/3 个输入里加权拷贝。
```

它处理的是“序列位置表”。

TreeHeap route 处理的是“树上的递归路径”。

这就是为什么我们一直强调：

```text
矩阵可以有用，但不能冒充 TreeHeap route。
```

## 但更准确的类比不是查找树，而是信息编码树

上面的例子说：

```text
query = cats
从 root 一路找 cats
```

这个说法容易误导。

它会让 TreeHeap route 听起来像二叉搜索树：

```text
比较 key
选择 left/right
找到目标
```

这不是我们真正想要的 TreeHeap。

更准确的类比应该是霍夫曼编码树一类的信息编码树。

在霍夫曼树里，重点不是“比较大小”。

重点是：

```text
root      表示一整团信息
internal  表示还能继续细分的信息集合
left/right 表示不同的信息分支
leaf      表示更具体的信息状态
path      就是编码
```

TreeHeap route 也应该这样理解。

当前 node 不是一个普通容器。

它应该是一个信息状态：

```text
H_i = 当前 node 所承载的信息分布
```

例如：

```text
H_1 表示整句话的信息
H_2 表示左半句的信息
H_3 表示右半句的信息
```

route 不是问：

```text
cats 在左边还是右边？
```

更深一层，它是在问：

```text
在当前问题 Q 下，
当前 node 的信息是否已经足够？

如果不够，
应该坍缩到哪个信息分支，
才能获得更多有效信息？
```

所以 `stop / left / right` 的含义应该改成：

| 动作 | 信息论含义 |
|---|---|
| `stop` | 当前 node 的信息已经足够回答 Q |
| `left` | 左分支的信息增益更高 |
| `right` | 右分支的信息增益更高 |

这样看，TreeHeap route 就不是：

```text
SearchTreeRoute
```

而是：

```text
InformationCollapseRoute
```

也就是：

```text
在一棵信息编码树上，
根据 Q 对当前信息状态做概率坍缩。
```

这个修正很重要。

因为 echo 任务里我们可以假装自己在“找 token”。

但翻译任务里，模型通常不是在找一个确定 token。

它可能是在问：

```text
当前中文生成位置需要英文哪一块信息？
这个时间状语是否应该前置？
这个修饰语应该归到哪个短语里？
当前 node 是否已经是一个可读短语？
```

这些都不是普通查找树问题。

它们更像：

```text
在当前信息分布中，
选择一个最有用的信息粒度。
```

## 语义前缀压缩：为什么这可能带来推理

这里还要再加一层。

如果 TreeHeap 只是把词放进树，它仍然不够。

真正有价值的是：

```text
树的 internal node 不是随便分组，
而是形成可迁移的语义前缀类。
```

例如：

```text
吃
├─ 食物类
│  ├─ 米饭
│  ├─ 面条
│  └─ 苹果
├─ 药品类
│  ├─ 阿莫西林
│  └─ 布洛芬
```

如果模型只背 pair，它只能知道：

```text
吃 + 米饭
吃 + 面条
吃 + 苹果
```

但当新组合出现：

```text
吃 + 阿莫西林
```

它没有见过这个 pair。

这时如果 TreeHeap 有语义前缀，它可以走另一条路：

```text
阿莫西林 -> 药品
药品 -> 可摄入对象
吃 接受 可摄入对象
所以 吃 + 阿莫西林 可以成立
```

这不是枚举所有可能句子。

这是用 internal node 做演绎迁移。

所以 TreeHeap 的前缀压缩，不应该只是霍夫曼树那种频率压缩。

它应该更像：

```text
按语义可推理性压缩。
```

也就是说，root / internal node 要尽量保存这样的东西：

```text
这个子堆属于什么语义类？
这个语义类能参与哪些关系？
这个关系能不能迁移到未见过的叶子？
```

这就把 TreeHeap route 的问题从：

```text
我该走 left 还是 right？
```

推进到：

```text
当前 Q 下，哪个语义前缀类最能解释这个问题？
```

## 一个最小 proof：吃阿莫西林

为了不让这段只停留在理论，我做了一个很小的 toy proof。

它不是自然语言理解实验。

它只是检查：

```text
语义前缀结构是否能带来 pair memory 没有的演绎迁移。
```

toy ontology：

```text
rice        -> entity -> consumable -> food
noodle      -> entity -> consumable -> food
apple       -> entity -> consumable -> food
amoxicillin -> entity -> consumable -> medicine
ibuprofen   -> entity -> consumable -> medicine
water       -> entity -> drinkable  -> beverage
shirt       -> entity -> wearable   -> clothing
car         -> entity -> drivable   -> vehicle
```

谓词规则：

```text
eat   accepts consumable
take  accepts medicine
drink accepts drinkable
wear  accepts wearable
drive accepts drivable
visit accepts visitable
```

关键设置：

```text
训练集不包含 eat + amoxicillin。
```

但是训练集中有：

```text
eat + rice
eat + noodle
eat + apple
take + amoxicillin
```

也就是说，模型见过：

```text
eat 和 consumable/food 的关系
amoxicillin 和 medicine/consumable 的关系
```

但没有见过：

```text
eat + amoxicillin
```

对照组：

```text
pair_memory       只记见过的正例 pair
pair_logistic     只用 verb-object pair id
token_additive    只用 verb id + object id
semantic_prefix   使用 object 的语义前缀 path
```

实验结果：

| 模型 | test acc |
|---|---:|
| pair memory | `0.4` |
| pair logistic | `0.4` |
| token additive | `0.6` |
| semantic prefix | `1.0` |

关键例子：

```text
Question:
  Can eat + amoxicillin be accepted without that pair in training?

pair_memory:
  gold = 1
  pred = 0

semantic_prefix:
  path = [entity, consumable, medicine]
  gold = 1
  prob = 0.7088
  pred = 1
```

这支持一个很窄的结论：

```text
如果 TreeHeap state 里有语义前缀类，
那么它可以支持“未见叶子”的演绎迁移。
```

但边界也必须写清楚：

```text
这个 ontology 是手工给的；
semantic prefix path 是监督的；
这不证明模型已经能从自然语料中学出“药品类”；
这不证明 WMT 翻译；
这不证明自然语言理解。
```

它证明的是一个更基础的点：

```text
TreeHeap root/internal node 不应该退化成 word bag。
它应该朝“可解码、可压缩、可迁移的语义前缀结构”发展。
```

## route kernel 到底做什么

上面说“当前信息是否足够、哪个分支信息增益更高”，这句话要变成代码，就需要一个函数。

这个函数就叫 route kernel。

它的输入是：

```text
q          = 要找的东西，比如 "cats" 的向量
arr[i]     = 当前子堆摘要
arr[2i]    = left 子堆摘要
arr[2i+1]  = right 子堆摘要
```

它的输出是三个分数：

```text
score_stop
score_left
score_right
```

然后取最大值：

```text
如果 score_left 最大，就走 left。
如果 score_right 最大，就走 right。
如果 score_stop 最大，就停下。
```

伪代码就是：

```python
i = 1

while True:
    q_vec = encode(query)

    current = arr[i]
    left    = arr[2 * i]
    right   = arr[2 * i + 1]

    score_stop, score_left, score_right = K(q_vec, current, left, right)

    action = argmax([score_stop, score_left, score_right])

    if action == "stop":
        return arr[i]

    if action == "left":
        i = 2 * i

    if action == "right":
        i = 2 * i + 1
```

本科数据结构课里，这很像二叉树查找。

不同点在于：

```text
普通二叉搜索树靠 key 的大小比较。
TreeHeap route 靠 kernel 从向量状态里判断方向。
```

也就是说，在更准确的口径里，TreeHeap 不是问：

```text
cats > like 吗？
```

而是问：

```text
在当前 Q 下：
  当前 node 是否已经足够？
  left subheap 是否提供更多有效信息？
  right subheap 是否提供更多有效信息？
```

这就是为什么我们关心 `arr[i]` 到底怎么表示。

如果 `arr[i]` 表示得好，kernel 就容易判断。

如果 `arr[i]` 表示得差，kernel 就会迷路。

## 这里必须停一下：H、Q、Theta 到底是什么

上面的二叉树查找只是工程近似。

如果我们把它上升到 TreeHeap 理论层，不能只说：

```text
有个 kernel，输出 left/right/stop。
```

这样太像普通神经网络包装出来的说法。

必须把三个对象说清楚：

```text
H      = 当前样本的 TreeHeap state
Q      = 当前输入问题 / 读取意图 / 求解变量
Theta  = 可学习的参数 TreeHeap
```

然后模型做的事情应该是：

```text
Route_Theta(H, Q) -> ProbabilityBucket(stop, left, right)
```

也就是说，它不是先天直接给一个硬答案。

它先给一个概率桶：

```text
stop  = 0.05
left  = 0.10
right = 0.85
```

如果需要硬执行，就坍缩成：

```text
right
```

如果还不想坍缩，就把这个概率桶传给下一层。

这才更接近我们一直说的：

```text
概率容器
延迟坍缩
结构搜索
```

### H：当前句子的全程状态

假设输入句子是：

```text
I like small cats
```

写入 TreeHeap 后，得到一个 `H`：

```text
H.arr[4] = state("I")
H.arr[5] = state("like")
H.arr[6] = state("small")
H.arr[7] = state("cats")

H.arr[2] = compose(H.arr[4], H.arr[5])
H.arr[3] = compose(H.arr[6], H.arr[7])
H.arr[1] = compose(H.arr[2], H.arr[3])
```

这里的 `H` 不是参数。

它更像一次前向计算里的运行时内存。

同一句话每次输入，都会生成自己的 `H`。

不同句子有不同的 `H`。

所以：

```text
H = data state
```

不是：

```text
H = learned parameter
```

### Q：这次想解决的问题

`Q` 不是整棵树。

`Q` 是“我现在要问什么”。

在 echo 任务里，`Q` 可以很简单：

```text
我要读回第 k 个 token。
```

或者：

```text
我要找 token cats。
```

在翻译任务里，`Q` 会复杂很多，可能是：

```text
我要生成中文第 t 个位置；
我要读英文里和当前中文位置最相关的 subheap；
我要判断某个时间状语是否应该前置。
```

所以：

```text
Q = query / task intent
```

它决定这次 route 的目标。

同一个 `H`，不同的 `Q`，应该得到不同的概率桶。

比如同一句话：

```text
H = TreeHeap("I like small cats")
```

如果：

```text
Q = read("I")
```

路线应该偏 left-left。

如果：

```text
Q = read("cats")
```

路线应该偏 right-right。

### Theta：参数也应该是 TreeHeap

这里是最容易讲糊的地方。

如果我们写：

```text
score = MLP([Q, H.arr[i], H.arr[2i], H.arr[2i+1]])
```

这当然能跑。

但它不一定是 TreeHeap 的理论形态。

更严格地说，`Theta` 应该也是一个参数 TreeHeap。

比如 route kernel 可以有自己的参数堆：

```text
Theta_route.arr[1] = root slot parameter
Theta_route.arr[2] = left slot parameter
Theta_route.arr[3] = right slot parameter
Theta_route.arr[4...] = deeper/local pattern parameters
```

它不是一句话的运行时状态。

它是模型长期学习出来的规则。

类比线性回归：

```text
y = w x + b
```

这里：

```text
w, b = 参数
x    = 输入
y    = 输出
```

放到 TreeHeap 里，就是：

```text
H      = 输入句子形成的 TreeHeap state
Theta  = 模型学到的参数 TreeHeap
Q      = 当前求解意图
P      = 输出概率桶
```

所以更像：

```text
P = Route(H, Q; Theta)
```

而不是：

```text
P = Route(H, Q)
```

### Theta 怎么参与当前 node 的计算

在某个 node `i`，我们有当前局部数据：

```text
local_H(i) = [H.arr[i], H.arr[2i], H.arr[2i+1]]
```

参数 TreeHeap 也提供一个局部算子：

```text
local_Theta = [Theta.arr[root], Theta.arr[left], Theta.arr[right], ...]
```

一个最小形式可以写成：

```text
z_stop  = f_stop(Q, H.arr[i],     local_Theta)
z_left  = f_left(Q, H.arr[2i],    local_Theta)
z_right = f_right(Q, H.arr[2i+1], local_Theta)
```

然后：

```text
P(stop, left, right)
  = softmax([z_stop, z_left, z_right])
```

这里的 `f_stop / f_left / f_right` 可以先用 MLP 近似。

但理论上它应该逐步替换成 TreeHeap kernel：

```text
root slot 怎么比较
left slot 怎么比较
right slot 怎么比较
路径前缀怎么参与
subheap compose 怎么参与
mirror / fold 等算子怎么参与
```

这就是当前理论还没完全闭合的地方。

### Theta 怎么训练

训练过程和普通机器学习一样，需要 loss。

在 echo route 任务里，我们知道正确动作。

比如：

```text
当前 node = arr[1]
query = cats
正确动作 = right
```

模型输出：

```text
P(stop)=0.05
P(left)=0.30
P(right)=0.65
```

那么 loss 可以用交叉熵：

```text
Loss = -log P(right)
```

如果模型把 right 概率调高，loss 下降。

梯度下降更新的是：

```text
Theta_route
```

也就是参数 TreeHeap。

不是直接把这句话的 `H` 当作长期参数。

更完整一点：

```text
for each training sample:
    H = Encode(sentence)
    Q = BuildQuery(task)

    for each route step:
        P = Route_Theta(H, Q, node=i)
        Loss += CE(P, correct_action)

    update Theta by gradient descent
```

如果 encoder 也是可学习的，那么还会更新：

```text
Theta_encode
Theta_compose
Theta_route
Theta_read
```

但这几个最好分开训练或分阶段训练。

不然梯度会混在一起，最后我们不知道到底是谁学会了东西。

### 当前 046 实验实际做到了哪一步

必须诚实说，当前实验没有完全做到上面的理论形态。

当前 dense content-aware proof 做到的是：

```text
H.arr[i] 使用 dense vocab-count subheap state；
Q 使用 supervised query token；
Theta 使用一个普通神经网络参数；
输出 stop/left/right 概率；
用交叉熵训练；
最后硬坍缩成路径。
```

也就是说，它证明了：

```text
如果 H.arr[i] 真的包含子堆内容，
一个可学习 route function 可以读 H 和 Q，
并学出 stop/left/right 概率桶。
```

但它还没有证明：

```text
Theta 本身已经是一个严格的参数 TreeHeap；
compose/read/route 都已经在 TreeHeap 代数内部闭合；
模型已经能无监督发现 Q；
模型已经能翻译。
```

所以 046 的正确定位应该是：

```text
第一次 content-aware route 工程 proof。
不是完整 TreeHeap route 理论闭包。
```

这个区分必须保留。

如果不保留，我们就会再次把“能跑的近似实现”误写成“理论已经完成”。

## 现在的结论先说清楚

这次结论分两层。

第一层：

```text
content-aware dense route 跑通了。
```

第二层：

```text
compact 压缩版没有跑通严格门槛。
```

这不是 GPU 没点燃。

也不是 io 基础设施问题。

实验在 io 上正常执行，日志、summary、evidence 都保存了。

真正的问题在这里：

```text
dense vocab-count subheap state 能支持 route；
naive random token sum compact state 会丢精度。
```

换句话说，船已经出港了，但现在卡在“船舱怎么压缩物资还不丢关键物品”。

## content-aware route 的实验版算法

上面是算法概念。

这次实验里的 content-aware route，就是把它具体落成下面这个形式：

```text
当前 node = i

kernel 输入：
  q              当前要找的 token/query
  arr[i]         当前子堆状态
  arr[2i]        left child 子堆状态
  arr[2i + 1]    right child 子堆状态

kernel 输出：
  stop / left / right
```

如果输出 left：

```text
i = 2i
```

如果输出 right：

```text
i = 2i + 1
```

如果输出 stop：

```text
return arr[i]
```

这里的核心不是“能不能走到正确叶子”。

核心是：

```text
kernel 的判断依据来自堆内容，而不是外部答案。
```

这和之前被审计的问题不同。

之前的几何版本里，feature 里有类似：

```text
target in left?
target in right?
```

这等于把答案方向直接塞给 kernel。

content-aware 版本不允许这样做。

它只允许读：

```text
query
当前子堆内容
左子堆内容
右子堆内容
```

这就比较像真正的 TreeHeap 局部卷积了。

用刚才的例子说：

```text
query = cats

在 arr[1]：
  left  = ["I", "like"]
  right = ["small", "cats"]

kernel 应该判断 cats 在 right 里，所以输出 right。

到 arr[3]：
  left  = ["small"]
  right = ["cats"]

kernel 应该输出 right。

到 arr[7]：
  当前就是 cats

kernel 应该输出 stop。
```

所以这不是“一次分类”。

它是一串局部判断组成的查找过程。

这也是为什么整条 route exact 很苛刻：

```text
只要某一步 left/right/stop 错了，
整条路径就错。
```

## dense 版本怎么表示 subheap state

dense 版本用的是一个很朴素、但很清楚的表示。

假设词表大小是：

```text
vocab = 1024
```

那么每个 `arr[i]` 是一个 1024 维向量。

它表示：

```text
这个子堆里出现过哪些 token。
```

比如子堆里有：

```text
cat, is, eating
```

那么对应 token 的位置会被计数。

这不是语义向量。

它更像一个子堆内容清单。

优点：

```text
信息非常明确。
query token 在不在 left/right 子堆中，理论上可以从内容清单里学出来。
```

缺点也很明显：

```text
太大。
```

这次 dense proof 的复杂度估计是：

```text
dense_feature_memory_mb = 6191.25
```

大约 6.2GB。

这已经不是优雅方案了。

但它适合作为第一把尺子：

```text
如果 dense 内容清单都跑不通，
那就说明 route 机制本身有问题。
```

结果它跑通了。

## dense proof 的结果

实验数据：

```text
data = /mnt/nas/datasets/wmt_massive/train.massive.zh-en.tsv
samples = 20,000
vocab = 1024
heap max_len = 32
train lengths = 3..24
OOD lengths = 25..32
```

这里的 OOD 是长度外推：

```text
训练只看长度 3 到 24；
测试看长度 25 到 32。
```

这可以检查模型是不是只背了长度表。

结果：

| 指标 | 数值 |
|---|---:|
| train route steps | `352110` |
| OOD route steps | `44130` |
| dense feature memory | `6191.25 MB` |
| OOD step acc | `0.9983` |
| OOD route exact | `0.9902` |
| flat length-matrix OOD token acc | `0.0029` |
| flat length-matrix OOD exact | `0.0000` |
| pilot pass | `true` |

这说明：

```text
content-aware dense TreeHeap route 第一次真正跑通了。
```

这里的“第一次真正”是有边界的。

它不是说：

```text
TreeHeap 会翻译。
TreeHeap 理解语义。
TreeHeap 击败 Transformer。
```

它只说：

```text
在 controlled S1 route 任务里，
kernel 可以读 subheap 内容，
递归执行 stop/left/right，
并在未见过的更长句子上保持接近 99% 的整条路径正确率。
```

这已经够重要。

因为它把 TreeHeap route 从“几何答案导航”推进到了“内容感知导航”。

## 为什么 compact 版本必须做

dense 版本有 6.2GB 的 feature memory。

如果我们每次都用 1024D 甚至更大的词表清单，后面没法往真实 S1/S2 走。

所以自然要问：

```text
能不能把每个 subheap 压成一个小向量？
```

比如：

```text
64D
128D
```

这就更像我们最终想要的 TreeHeap state。

每个 token 不是 one-hot 清单，而是一个向量。

每个子堆状态是：

```text
arr[i] = 子堆里 token vectors 的组合
```

这也是直觉上更接近未来方案的地方：

```text
token embedding
subheap embedding
learned compose
learned read
```

但是这次先做了一个最简单的 compact 版本：

```text
token id -> 固定随机向量
arr[i]   -> 子堆 token 向量求和
```

注意，这里还不是 learned embedding。

它只是测试：

```text
随机向量求和，能不能保住 enough information？
```

## compact 64D 的结果

64D compact run：

| 指标 | 数值 |
|---|---:|
| compact memory | `324.84 MB` |
| dense prior memory | `6191.25 MB` |
| memory reduction | `19.06x` |
| OOD step acc | `0.9973` |
| OOD route exact | `0.9838` |
| flat length-matrix OOD exact | `0.0000` |
| pilot pass | `false` |

这个结果非常有意思。

它不是全失败。

它做到了：

```text
内存从 6.2GB 降到 325MB；
单步 route accuracy 仍然有 0.9973。
```

但是它没有做到：

```text
整条 route exact >= 0.99。
```

为什么 step acc 很高，route exact 却不够？

因为一条 route 是多步决策。

比如从 root 走到 leaf，可能要：

```text
right -> right -> left -> right -> stop
```

只要中间一步错，整条路径就错。

所以：

```text
单步 0.997
```

听起来很好。

但多步相乘以后，整条路径 exact 会下降。

这就是 route 任务比普通分类更苛刻的地方。

## compact 128D 为什么也没救回来

为了检查是不是维度太小，又跑了 128D：

| 指标 | 数值 |
|---|---:|
| compact memory | `637.59 MB` |
| memory reduction | `9.71x` |
| OOD step acc | `0.9973` |
| OOD route exact | `0.9837` |
| pilot pass | `false` |

128D 没有明显变好。

这说明问题大概率不是：

```text
64D 太小，换 128D 就好。
```

更像是：

```text
随机 token vector 求和这个 state 设计本身不够好。
```

随机向量求和会有几个问题：

1. **碰撞**  
   不同 token 集合的向量和可能靠得太近。

2. **噪声积累**  
   子堆越大，里面 token 越多，sum 里的无关噪声越多。

3. **重复 token 不稳**  
   如果一句话里同一个 token 出现多次，query 在哪个位置会更难区分。

4. **没有学习参考系**  
   随机向量没有被训练成适合 route 的坐标系。

所以 compact 失败不是坏消息。

它告诉我们下一步不能再用“随机向量求和”假装世界模型。

## 当前航行问题

现在的位置可以画成这样：

```text
flat LxL route matrix
  -> 被降级：能恢复，但不是 TreeHeap

recursive geometry route
  -> 跑通：真的走树
  -> 被限制：读了几何答案 feature

content-aware dense route
  -> 跑通：真的读 arr[i] / left / right 内容
  -> 问题：6.2GB dense feature，不可持续

compact random-sum route
  -> 内存跑通：325MB
  -> 精度没过：OOD route_exact 0.9838 < 0.99
```

所以现在的航行问题不是：

```text
GPU 没点燃。
io 不稳定。
TreeHeap route 不存在。
```

而是：

```text
我们需要一种更好的 compact subheap state。
```

这句话很重要。

它把问题从基础设施和哲学争论，收束成一个工程/数学对象：

```text
怎样让 arr[i] 在低维空间里保留足够的子堆可读信息？
```

## 为什么我认为下一步是 learned token/subheap embeddings

dense content state 像一本清单：

```text
这个子堆里有 token A、B、C。
```

它很大，但清楚。

random-sum compact state 像把清单撕碎压成一团纸：

```text
体积小了，但有些字看不清。
```

learned embedding 的目标是：

```text
不是随机压缩，而是为了 route 任务学习一种压缩方式。
```

也就是让模型自己学：

```text
哪些 token 维度对 left/right/stop 有用；
哪些组合容易混淆；
哪些子堆状态需要拉开；
哪些状态可以靠近。
```

这和 Transformer 里的 embedding / attention 参数学习有相似之处。

不是把随机向量硬塞进模型，而是让 loss 反过来调整坐标系。

对应到 TreeHeap，就是：

```text
token embedding table      可学习
subheap compose kernel     可学习
route kernel               可学习
read/collapse kernel       可学习
```

但要注意，不能大锅炖。

至少下一步应该把任务拆开：

1. 学 token embedding，让 query 和 subheap state 可比较。
2. 学 subheap compose，让大子堆不只是 token sum。
3. 学 route kernel，让它读 `q, arr[i], arr[left], arr[right]`。
4. 加 repeated-token stress test，防止模型只靠 token 唯一性过关。
5. 加 pointer baseline，防止 TreeHeap claim 被普通指针模型追平。

## 当前 claim 应该怎么写

我建议现在只保留两个很克制的 claim。

第一个：

```text
S1-CONTENT-ROUTE-C01 supported pilot
```

意思是：

```text
TreeHeap route 可以读真实 subheap 内容，
而不是读几何答案 feature。
```

证据是 dense proof：

```text
OOD route_exact = 0.9902
flat length-matrix OOD exact = 0.0000
```

第二个：

```text
S1-COMPACT-CONTENT-ROUTE-C01 open / mixed pilot
```

意思是：

```text
compact state 方向必要，
但 naive random token sum 还不够。
```

证据是 compact proof：

```text
64D memory reduction = 19.06x
OOD route_exact = 0.9838
pilot_pass = false
```

这个 mixed 结果很宝贵。

因为它没有否定 TreeHeap route。

它否定的是一个过于简单的 state 设计。

## 这对 S1 / S2 意味着什么

S1 现在不应该急着冲翻译。

它下一步应该先回答：

```text
TreeHeap 能否把 token 序列写成可读、可压缩、可学习的 subheap state？
```

如果这个问题不解决，S2 会遇到同样的问题：

```text
graph builder / fold / translation 读到的 arr[i] 不是稳定语义结构，
而是一团压缩噪声。
```

所以 SPR-046 的航行方向是：

```text
不要再证明“能不能走树”。
已经能走树了。

现在要证明“树上的 state 怎么学”。
```

这是从 route proof 进入 encoder/state proof。

## 下一步实验建议

我建议下一批不要开太大，先做四个对照：

### A. learned token embedding

把固定随机 token vector 改成可学习表：

```text
E[token_id] = learnable vector
```

目标：

```text
OOD route_exact >= 0.99
memory <= 512MB
```

如果它过了，说明 loss 可以把 token 坐标系调成 route-friendly。

### B. learned subheap compose

不要再用：

```text
arr[i] = sum(children)
```

改成：

```text
arr[i] = Compose(arr[left], arr[right])
```

Compose 可以先很小：

```text
MLP([left, right])
```

或者更 TreeHeap 一点：

```text
root/left/right slot kernel
```

目标是减少大子堆里的噪声积累。

### C. repeated-token stress test

现在实验只用 unique-token query positions。

这太温柔了。

真实语言里会有：

```text
the ... the ...
of ... of ...
that ... that ...
```

如果 query token 重复出现，模型必须知道：

```text
我要找的是哪一个 token 实例，
而不只是这个 token 类型在哪个子堆里。
```

这会迫使 TreeHeap state 引入位置、路径、实例信息。

### D. pointer baseline

必须加普通 pointer model。

否则我们不能说 TreeHeap route 有结构优势。

对照应该包括：

```text
flat shared route
pointer network
small Transformer pointer
TreeHeap content route
```

如果 TreeHeap 赢，才有资格继续往 S2 接。

如果 TreeHeap 只是持平，也不是坏事。

那说明这个任务本身不够区分，需要设计更能暴露 address/path/subheap 归纳偏置的任务。

## 最后的小结

SPR-046 的结论是：

```text
content-aware dense TreeHeap route 跑通了。
这是第一次真正读堆内容的 TreeHeap route proof。
```

但同时：

```text
compact random-sum state 没过严格门槛。
```

所以当前航行问题不是“有没有路”。

而是：

```text
路已经出现了；
船上的状态压缩系统还不够好。
```

下一步要做的不是更大的口号。

而是把 `arr[i]` 这个 TreeHeap state 从：

```text
随机 token sum
```

升级到：

```text
learned token/subheap embedding
```

这是 S1 接 S2 前必须过的一道门。

> ARA: [claims](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/claims.md) / [experiments](https://github.com/houming818/sametime/blob/main/ara/s1-echo/logic/experiments.md) / [dense evidence](https://github.com/houming818/sametime/tree/main/ara/s1-echo/evidence/s1_content_treeheap_route_probe_20k_e5) / [compact evidence](https://github.com/houming818/sametime/tree/main/ara/s1-echo/evidence/s1_compact_content_treeheap_route_probe_20k_e5)
