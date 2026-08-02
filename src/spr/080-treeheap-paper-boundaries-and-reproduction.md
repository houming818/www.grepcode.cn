---
title: "[SPR-080·论文特别篇四] 如何审核 TreeHeap：Claim 边界、否证条件与复现入口"
date: 2026-08-02
lastmod: 2026-08-02
weight: 80
author: Houming818 & Codex Review
description: "TreeHeap 论文特别篇终章：公开当前 Claim 状态、可能推翻结论的实验、计算代价、复现路径，以及读者应该如何审核这项独立研究。"
tags: [SPR, TreeHeap, Paper, Falsification, Reproducibility, ARA, OpenScience]
---

# 如何审核 TreeHeap

> **系列定位：TreeHeap 论文特别篇（4/4）。**
>
> 一项新架构不能只展示最好样例。它必须告诉读者：什么结果会让研究者承认自己错了。

## 系列导航

1. [问题、失败与设计演化](/spr/077-treeheap-paper-origin-and-evolution.html)
2. [数学、参数与数据流](/spr/078-treeheap-paper-math-and-dataflow.html)
3. [三种子 WMT 与双向 Dreams](/spr/079-treeheap-paper-evidence-and-dreams.html)
4. **本篇：Claim 边界、否证条件与复现**

完整中文论文：

```text
https://github.com/houming818/sametime/blob/main/ara/papers/treeheap_emergent_protocol.zh.md
```

开放代码与 ARA：

```text
https://github.com/houming818/sametime
```

## 1. 当前 Claim 体检表

| Claim | 当前状态 |
|---|---|
| Butterfly 正反变换保持数值闭合 | 支持 |
| FOLD/UNFOLD 保持数值闭合 | 支持 |
| root 与多个 detail 深度参与当前 WMT 任务 | 支持机制 |
| 可学习 Update 在保持闭合时改善任务 | 部分支持，未过 0.05 NLL 强 gate |
| Butterfly 配置在当前 WMT 合同中优于 Identity/Adjacent | 三种子支持 |
| 已训练模型依赖通信变换 | 运行时依赖检查支持 |
| 收益严格来自 changing-bit 拓扑 | 开放 |
| 共享 TreeHeap 开始形成中英双向协议 | 规模观察支持，最终质量开放 |
| root 是人类可读摘要 | 未证明 |
| XOR 地址天然具有语义 | 未证明 |
| 当前状态已经实现存储压缩 | 否 |
| 当前实现已经节省 GPU 计算 | 未证明 |
| 当前模型达到产品级翻译质量 | 否 |

这张表比一句“实验成功”更重要，因为它限定了每个结果的有效范围。

## 2. 什么结果会推翻当前判断

### 2.1 推翻可逆性

若在有效输入上，Butterfly inverse 或 FOLD/UNFOLD closure 出现系统性大误差，而且不能由浮点精度解释，那么代数实现不成立。

### 2.2 推翻多分辨率参与

若 root、detail、pairing 和 depth 干预在多种子上都不造成稳定损失，或者 Decoder 被发现只从 leaf 直通读取，那么“TreeHeap 多分辨率参与任务”必须撤回。

### 2.3 推翻 Butterfly 的当前收益

若同数据、同种子、同参数和同训练合同无法重复当前三种子结果，Butterfly 的 WMT Claim 必须降级。

### 2.4 推翻 changing-bit 的特殊性

这是下一轮最关键的反证：

> 如果若干具有相同边数、阶段数和全局覆盖能力的固定随机 topology，与 XOR-Butterfly 表现相同或更好，就不能把收益归因于 changing-bit 调度本身。

Butterfly 仍可能是一种可用调度，但不再具有当前设想的特殊归纳偏置。

### 2.5 推翻双向协议生长

若全量训练长期出现以下情况之一，应停止扩大结论：

- 输出持续与源无关；
- 中英方向混淆；
- 验证损失长期不改善；
- checkpoint 重载后固定输出变化；
- 重复坍缩没有随训练缓解。

## 3. 为什么当前还不能叫“压缩模型”

Lifting 把 $N$ 个 leaf 组织成：

```text
1 root + (N-1) details
```

总状态数量没有减少。

真正的压缩必须进一步证明：

1. 可以删除、量化或延迟加载部分 detail；
2. 质量损失在给定预算内；
3. 存储、显存或计算成本实际下降。

所以论文使用“多分辨率状态”，不使用“已经压缩”。

## 4. 为什么当前还不能叫“高效模型”

理论操作量：

```text
Butterfly: O(N log N)
FOLD/UNFOLD: O(N)
current READ: O(TN)
```

当前代码没有为稀疏 TreeHeap kernel 编写专用 CUDA 实现。Python/PyTorch 张量重排可能让理论稀疏结构在实际 GPU 上更慢。

计算优势必须记录：

- 训练 token；
- GPU 小时；
- tokens/s；
- 峰值显存；
- 估算反向 FLOPs；
- 匹配质量所需的总成本。

复杂度公式不能代替工程测量。

## 5. 如何复现正式三种子实验

核心代码：

```text
ara/s3-generation/src/s2_treeheap_butterfly_wmt.py
```

Logic 与 Evidence：

```text
ara/s3-generation/logic/treeheap_butterfly_wmt_ablation.md
ara/s3-generation/evidence/s2_treeheap_butterfly_wmt_formal/
```

正式配置：

```text
train/valid/test = 200000/5000/5000
length = 8..32
heap_width = 64
dim = 256
hidden = 256
batch = 64
epochs = 5
lr = 0.002
seeds = 8104,8105,8106
```

Evidence 中保存：

- `summary.json`；
- 每个 seed 的 trace；
- 生成样例；
- 干预结果；
- closure 与 inverse 误差；
- checkpoint SHA-256。

## 6. 如何复查全量双向实验

训练代码：

```text
ara/s3-generation/src/s3_treeheap_butterfly_bilingual_full.py
```

实验说明和阶段证据：

```text
ara/s3-generation/logic/treeheap_butterfly_bilingual_full_train.md
ara/s3-generation/evidence/s3_treeheap_butterfly_bilingual_full/
```

`dreams/step-*.txt` 是不可变的固定探针快照。审核时不能只选最好的一次，应按时间顺序阅读全部文件。

## 7. 为什么我们使用 ARA

研究流程为：

```text
直觉
-> Claim
-> Predict
-> Experiment
-> Evidence
-> Audit
-> Revision
```

这套流程已经实际撤回过多项错误：

- token 路径被误写成语义；
- flat 长度路由被误写成递归 TreeHeap；
- geometry feature 把正确方向泄漏给模型；
- CLI 把中文续写错误标成翻译；
- runtime Identity 被过强解释为拓扑因果证据。

ARA 不能保证研究者不犯错。它只保证错误可以被定位，并且不会悄悄变成下一轮前提。

## 8. 下一轮三个决定性实验

### 8.1 冻结最好 checkpoint 与最后 checkpoint

全量训练已经进入震荡平台，最后一次不一定最好。最终报告必须同时保存：

- validation NLL 最好的 checkpoint；
- 时间预算结束时的 checkpoint；
- 两者在固定测试集上的完整比较。

### 8.2 严格 topology-only 干预

保持 checkpoint、kernel、调用次数和验证句相同，只替换地址配对图。对每个句子计算：

$$
\Delta L_i=L_i(wrong\ topology)-L_i(native)
$$

不能再拿不同数量的验证样本做差。

### 8.3 同覆盖能力 topology 的匹配重训

至少比较：

```text
XOR Butterfly
repeated adjacent
fixed random perfect matching A
fixed random perfect matching B
fixed random perfect matching C
```

所有配置保持边数、阶段数、kernel 参数量和训练数据一致。

## 9. 给非专业读者的最终判断

TreeHeap 现在不是一个成熟产品，也不是已经完成的意识理论。

它已经是：

```text
有明确数据结构
有数学逆运算
有梯度路径
有真实语言训练
有多种子结果
有失败档案
有公开反证条件
```

它还缺少：

```text
严格拓扑因果隔离
完整标准质量评价
真正的压缩收益
工程计算优势
跨任务复现
```

读者不需要相信作者或 AI。只需要检查公开代码、配置、原始结果和 Claim 边界。

## 10. 特别篇结语

这四篇特别篇把一篇较长的研究论文拆成了四个可以独立审核的问题：

1. 为什么最终架构会长成这样；
2. 数学和梯度究竟怎样流动；
3. 数据已经支持了哪些结论；
4. 什么实验可能推翻这些结论。

如果未来结论改变，这四篇也不应被删除。新的 Evidence 应更新 Claim，并保留旧判断为何被修正。

---

**License:** GPLv3。碳基和硅基读者均可阅读、复制、修改、复现和分发。
