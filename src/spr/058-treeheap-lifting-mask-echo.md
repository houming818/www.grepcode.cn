---
title: "[SPR-058] TreeHeap 信息抽水机：先形成 H_state，再遮住 token，能否完整 Echo？"
date: 2026-07-15
lastmod: 2026-07-15
weight: 58
author: Houming818 & Codex Review
description: "区分三种完全不同的 mask 时序，并报告 TreeHeap lifting information pump 的真实结果：所有 leaf 被遮住后，仅凭训练形成的 root 与多层 detail，token 和 16-token block 均可 100% Echo。"
tags: [SPR, TreeHeap, ARA, Echo, Lifting Scheme, Mask, Encoder, Decoder, Original Research]
---

# TreeHeap 信息抽水机：先形成 H_state，再遮住 token，能否完整 Echo？

这篇文章要回答一个很具体的问题：

> 一句话已经被 encoder 写进 TreeHeap，形成完整的 $H_{state}$ 以后，如果把原始 token 和 leaf 读取通道全部遮住，还能不能只凭 $H_{state}$ 把它恢复出来？

答案是：

~~~text
可以。

token echo       = 100%
16-token exact   = 100%
~~~

但这句话很容易被误解。

这里不是先把输入 token 删除，再要求模型猜出一个从未见过的答案。真正的数据流是：

~~~text
完整 token
    ↓ WRITE
Lifting FOLD 逐层上传
    ↓
H_state = root + 每一层 addressed details
    ↓
屏蔽全部 leaf/token 读取通道
    ↓
从 root 开始逐层 UNFOLD
    ↓
恢复 token
~~~

所以，mask 的对象是**已经编码完成后的表面读取通道**，不是 encoder 的原始输入。

这是 TreeHeap encoder/decoder 是否形成闭合协议的测试。

---

## 1. 为什么我们之前会争论 mask

“mask 一个 token”至少有三种完全不同的含义。

### 1.1 编码前 mask：让模型猜缺失信息

~~~text
小明 喜欢 吃 [MASK]
    ↓ encoder
H_state
    ↓
预测：米饭 / 面条 / 苹果 / 药……
~~~

原词在进入 encoder 以前就被删除了。

因此，$H_{state}$ 中没有原词的完整信息。模型只能学习条件概率：

$$ P(x_{\mathrm{mask}}\mid x_{\mathrm{visible}}). $$

对于“小明喜欢吃 [MASK]”，“米饭”“面条”“苹果”都可能合理，所以不能要求模型一定恢复数据集原句。

这种任务测试语言预测、世界经验和概率补全。它不是本文完成的 Echo。

### 1.2 编码后 mask：遮住 leaf，只读 H_state

~~~text
完整句子
    ↓ encoder
root + details
    ↓ 删除原始 leaf 读取
decoder
    ↓
恢复完整句子
~~~

原始 token 已经参与 WRITE 和 FOLD，但 decoder 不能直接复制它。

它必须从压缩后的 TreeHeap 状态逆运算回来。本文测试的正是这一种，而且不是只 mask 一个 token，而是**同时禁止读取全部 16 个 leaf**。

### 1.3 H_state 内部 mask：删除某层 detail

第三种更加困难：

~~~text
完整句子
    ↓ encoder
root + details
    ↓ 删除目标路径上的某个 detail
不完整 H_state
    ↓
尝试恢复 token
~~~

此时精确逆运算所需的信息真的缺失了。模型必须利用 root、其他尺度和语料中学到的规律，预测缺失 detail 的概率分布。

这是后续的“归纳补全”问题。本文只做了消融诊断，没有宣称它已经解决。

---

## 2. 上一版 FOLD 为什么没有把信息抽到高层

上一轮实验使用普通递归 FOLD：

~~~text
16 leaf
  ↓
8 parent-1
  ↓
4 parent-2
  ↓
2 parent-3
  ↓
1 root
~~~

代码确实算到了 root。但是 decoder 可以为每个输出位置选择读取哪一层。训练最后找到的捷径是：

~~~text
两个 token
    ↓
一个 parent-1
    ↓
直接恢复这两个 token
~~~

READ 权重分布为：

~~~text
parent-1   99.9786%
parent-2    0.0084%
parent-3    0.0051%
root        0.0079%
~~~

删除 parent-1，NLL 增加 74.4254；删除 root，变化约为零。

因此，旧实验只证明一个共享 FOLD 可以把两个 token 编进一个 parent。它没有证明信息继续上传。

问题不在于 FOLD 有没有被递归调用，而在于系统缺少类似抽水机的基本规律：

- 哪部分信息必须向上；
- 哪部分细节留在本层；
- decoder 是否必须从高层向下解码；
- 有没有绕开高层的旁路。

---

## 3. 抽水机的基本规则：Lifting Scheme

我们采用 lifting scheme，也就是可逆小波中常用的“预测与更新”结构。

设左右子节点状态为 $L$ 和 $R$，共享 predictor 为 $P_\theta$。

先计算 detail：

$$ D=R-P_\theta(L). $$

再计算向上的 parent：

$$ U=L+\frac{1}{2}D. $$

其中：

- $D$ 是留在当前深度的带地址细节；
- $U$ 是唯一允许继续上传的 parent；
- $P_\theta$ 是所有节点、所有深度共享的卷积 kernel。

当 $P_\theta(L)=L$ 时：

$$ D=R-L, $$

$$ U=L+\frac12(R-L)=\frac{L+R}{2}. $$

这时可以直观理解为：

~~~text
U = 左右子树的粗粒度轮廓
D = 左右子树之间的差异
~~~

换一个可学习 predictor 后，内部坐标系可以完全不同，但结构规律不变：

~~~text
两个 child
→ 一个 upward parent
→ 一个 local detail
~~~

---

## 4. 为什么它可以严格逆运算

decoder 从 $U,D$ 恢复 $L,R$：

$$ L=U-\frac12D, $$

$$ R=D+P_\theta(L). $$

代入 FOLD 公式：

$$ U-\frac12D =L+\frac12D-\frac12D =L, $$

然后：

$$ D+P_\theta(L) =R-P_\theta(L)+P_\theta(L) =R. $$

因此，只要 encoder 和 decoder 使用同一个 $P_\theta$，就有：

$$ UNFOLD_\theta(FOLD_\theta(L,R))=(L,R). $$

这里有一个重要事实：

> $P_\theta$ 不需要线性，也不需要自己可逆。

decoder 不是计算 $P_\theta^{-1}$，而是在恢复出 $L$ 以后，再调用一次同一个 $P_\theta(L)$。

这就像两个人使用同一本私人字典。字典内容可以通过数据学习，但写入和读出必须遵守同一个协议。

---

## 5. 16 个 token 如何被抽到 root

对于 16 个 leaf，编码过程是：

~~~text
16 leaf
  ↓ FOLD
8 parent + 8 detail-1
  ↓ FOLD
4 parent + 4 detail-2
  ↓ FOLD
2 parent + 2 detail-3
  ↓ FOLD
1 root   + 1 detail-4
~~~

最终状态不是只有 root，而是：

$$ H_{state} =(root,D^{(4)},D^{(3)},D^{(2)},D^{(1)}). $$

decoder 不允许跳到 parent-1，也不能读取原始 leaf。它必须从 root 开始：

~~~text
root + detail-4
    ↓ UNFOLD
2 个 parent-3
    ↓ 加 detail-3，再 UNFOLD
4 个 parent-2
    ↓ 加 detail-2，再 UNFOLD
8 个 parent-1
    ↓ 加 detail-1，再 UNFOLD
16 个 leaf state
    ↓ READ
16 个 token
~~~

这就是“抽上去，再放下来”。

---

## 6. 演绎 Echo 和归纳 Echo 是什么关系

### 6.1 演绎部分：代数保证闭包

只要保存完整的 root 和 details，无论 $P_\theta$ 的参数是什么，FOLD/UNFOLD 都应该闭合。

我们用随机连续向量测试深度 1 到 6 的树：

| 指标 | 结果 |
|---|---:|
| 深度 6 最大 FP32 闭包误差 | 3.70e-6 |
| 真实 token state MSE | 3.14e-14 |
| 最大 state 误差 | 2.86e-6 |

这是演绎证据：结果来自公式本身。

### 6.2 归纳部分：语料决定私人坐标系

如果 Echo 永远精确，单独用 Echo loss 训练 $P_\theta$ 是没有意义的。

因为任何 predictor 都会被自己的 UNFOLD 抵消：

$$ UNFOLD_\theta(FOLD_\theta(X))=X. $$

所以，这次没有用 Echo 作为训练 loss。训练任务是自然语料 next-token：

~~~text
观察 16 个真实中文 token
    ↓ Lifting FOLD
root
    ↓
预测第 17 个自然出现的 token
~~~

其 loss 为：

$$ L_{\mathrm{next}} =-\log P(x_{17}\mid root(x_1,\ldots,x_{16})). $$

这给 root 制造了真正的“压力差”：如果 predictor 产生的 root 对语料预测无用，NLL 就不会下降。

实验结果：

| 模型 | 验证 NLL，越低越好 |
|---|---:|
| frozen predictor | 8.06377 |
| learned predictor | 8.03468 |
| learned 改善 | 0.02910 |

predictor 的最大梯度范数为 0.50191，参数变化量为 16.13119。语料梯度确实改变了抽水 kernel。

然后，我们使用这个**经过归纳学习的 $P_\theta$**，遮住全部 leaf，只凭训练形成的 $H_{state}$ 逆运算：

| Echo 指标 | 结果 |
|---|---:|
| token top-1 | 1.0000 |
| 16-token block exact | 1.0000 |

因此，更准确的说法是：

> 归纳学习决定 TreeHeap 的私人坐标系；演绎闭包保证这个坐标系可以被同一协议读回。

---

## 7. 它真的使用 root 和每层 detail 吗

只看 100% Echo 仍然不够。我们继续做因果消融。

### 7.1 删除 root

| 条件 | token top-1 | block exact |
|---|---:|---:|
| 完整 H_state | 1.0000 | 1.0000 |
| root 清零 | 0.93042 | 0.0000 |
| root 换成另一句 | 0.93701 | 0.0078125 |

删除 root 后，大多数单词仍可能因为局部 detail 而落在正确 embedding 附近，但没有一个 block 能完整恢复。

所以 root 不是全部细节，却是完整闭合链的一部分。

### 7.2 打乱不同深度的 detail 地址

| 被换址的 detail | token accuracy 下降 |
|---|---:|
| detail-1 | 49.88% |
| detail-2 | 25.00% |
| detail-3 | 12.35% |
| detail-4 | 6.32% |

这个接近逐层减半的规律很好理解：detail-1 直接区分每一对 leaf；越高层的 detail 数量越少，但覆盖范围越大。

### 7.3 破坏每一层的左右配对

在 next-token 任务中，分别把某一深度的右子树换成其他样本：

| 被破坏的 FOLD 深度 | NLL 增加 |
|---|---:|
| depth 1 | +0.03221 |
| depth 2 | +0.03838 |
| depth 3 | +0.04324 |
| depth 4 | +0.05634 |

四个深度都产生损失。

这和旧版 99.9786% 停在 parent-1 的情况不同：新的 root 预测确实依赖完整递归路径。

---

## 8. 为什么预注册 Claim 仍然没有全过

我们事先规定：

~~~text
root 被删除后，Echo token accuracy 至少下降 10%
~~~

实际下降是：

~~~text
6.96%
~~~

所以 P3 没有通过，完整 Claim 必须保持 not fully supported。

我们不能看到 block exact 从 100% 降到 0% 后，再偷偷把评价标准从 token accuracy 换成 block exact。

不过可以保留一个更窄的结论：

1. lifting FOLD/UNFOLD 已经闭合；
2. 全部 leaf 被 mask 后，可以只凭 $H_{state}$ 完整 Echo；
3. 每层 detail 都是地址敏感且有因果作用的；
4. root 对整块闭合和 next-token 都有因果作用；
5. 真实语料梯度能够训练 predictor；
6. learned predictor 小幅但明确优于 frozen predictor。

---

## 9. 高层不需要对应人类命名的语义

Houming818 对这一步提出了一个重要修正：

> 我们不需要证明 root 一定表示“主题”，parent 一定表示“短语”。这些结构可以通过数据涌现，而且换一种抽水算法，形成的内部意义可能完全不同，解并不唯一。

我们同意这个判断。

假设两个 TreeHeap 使用不同 predictor：

$$ P_{\theta_1},\qquad P_{\theta_2}. $$

它们可能形成完全不同的 root/detail 坐标系，但只要分别满足：

$$ UNFOLD_{\theta_1}(FOLD_{\theta_1}(X))=X, $$

$$ UNFOLD_{\theta_2}(FOLD_{\theta_2}(X))=X, $$

并且都能降低真实任务 loss，它们就可以是两个不同但有效的私人协议。

这类似每个人的笔迹不同，但各自可以读懂自己写下的内容。

因此，我们不应强迫内部节点对应预先定义的主谓宾、词性或人工类别。真正需要验证的是操作意义：

- 能否写入；
- 能否读回；
- 地址是否有因果作用；
- 删除节点是否按结构损坏结果；
- 学习是否改善真实任务；
- 更大的任务是否能站在这个协议上继续训练。

---

## 10. 当前边界和下一步

当前已经完成的是：

~~~text
完整 token
→ 归纳学习过的 lifting encoder
→ H_state
→ mask 全部 leaf
→ 演绎 UNFOLD
→ 100% Echo
~~~

还没有完成的是：

~~~text
完整 token
→ H_state
→ 删除 H_state 中某个必要 detail
→ 根据其他尺度和世界经验补回缺失信息
~~~

后一种任务不再是严格逆运算，而是：

$$ P(D_{\mathrm{missing}}\mid root,D_{\mathrm{visible}},context). $$

它才是从“私人可逆编码”走向“缺失信息推断”的下一步。

但至少现在，TreeHeap 不再只是执行了几次形式上的递归卷积。我们已经有了一套明确的信息流规则：

~~~text
FOLD：向上抽取 parent，留下 addressed detail
UNFOLD：从 root 出发，逐层补回 detail
LEARN：真实语料梯度改变 predictor 和内部坐标系
ECHO：遮住全部表面 leaf 后，仍可精确恢复
~~~

这是一台已经能运转的信息抽水机。

它是不是语言智能，还远远没有证明；但它终于不再是一根只在第一层取水的管道。

---

## Evidence

ARA 声明：

~~~text
ara/s1-echo/logic/lifting_information_pump.md
~~~

实验代码：

~~~text
ara/s1-echo/src/s1_lifting_information_pump.py
~~~

正式 Evidence：

~~~text
ara/s1-echo/evidence/s1_lifting_information_pump/main/
~~~

SameTime commit：

~~~text
f17ab3f
~~~

本文记录的是可复现实验和当前边界，不是对 TreeHeap 语义、意识或通用智能的完成声明。
