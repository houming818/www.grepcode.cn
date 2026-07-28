---
title: "[SPR-067] STONE-1 正式体检：树地址成立，私有协议尚未学会"
date: 2026-07-22
lastmod: 2026-07-22
weight: 67
author: Houming818 & Codex Review
description: "一百万对真实英中语料、三颗随机种子、九次正式训练：STONE-1 为什么证明了 TreeHeap 地址的因果作用，却否定了当前 hard gate 私有协议配方。"
tags: [SPR, TreeHeap, ARA, STONE-1, Private Protocol, WMT, Encoder, Decoder, NLL, BLEU, Falsification]
---

# STONE-1 正式体检：树地址成立，私有协议尚未学会

> **证据状态更新（2026-07-28）：STONE-1 的完成判定与“英文语义进入 TreeHeap”的推断暂停。C10 代码审计发现，teacher forcing 和大面积可见 EOS 尾部没有被既有 gate 排除。地址交换造成 NLL 损伤，仍能证明 decoder 使用了某些树状态；它不能单独证明这些状态携带英文条件语义。详见 SPR-074。**

> 这是一篇正式实验报告，也是一份“架构体检单”。STONE-1 在 io 的 RTX 3090 上连续运行约 7.57 小时，完成了 3 种结构方案、3 颗随机种子、共 9 次训练。程序没有崩溃，checkpoint 和 CLI 都成功产出，但核心 Claim 没有通过。更准确地说：**模型确实依赖 TreeHeap 的左右地址和层级秩序；然而当前的可学习方向 gate 没有形成比固定结构更好的 encoder-decoder 私有协议。**

这不是“TreeHeap 已经失败”，也不是“再多跑几天就一定成功”。它把两个长期混在一起的问题第一次拆开了：

1. TreeHeap 的结构有没有进入模型计算？有，而且因果信号很强。
2. 当前 kernel 是否学会了有价值的内部编码协议？没有，固定 identity 反而更好。

本文从头解释实验设计、指标、数据、结果和下一步。没有读过前 66 篇文章，也可以独立阅读。

---

## 1. 我们到底想证明什么

普通 seq2seq 模型可以把输入句子编码成一组向量，再从这些向量生成输出。只看最终翻译，我们不知道中间状态究竟是一棵 TreeHeap，还是一条换了名字的数组。

STONE-1 因此提出了一个比“能翻译”更严格的目标：

```text
英文 token
  -> 递归 FOLD
  -> 固定容量 TreeHeap H_state
  -> 递归 UNFOLD / 多层读取
  -> 中文 decoder
  -> 非 teacher-forcing 生成
```

其中没有额外的句法标签、旋转标签或“这里应该向左”的答案。模型只能根据最终翻译损失，通过梯度自己决定内部如何编码。

我们希望看到的现象是：

```text
learned structural
  比固定 identity 更好
  比固定 random 更好
  改掉 learned gate 会明显变差
  破坏左右地址也会明显变差
```

如果只满足最后一条，只能证明“地址有用”，不能证明“learned gate 学会了私有协议”。这一区分是整场实验的核心。

---

## 2. 什么叫 encoder-decoder 私有协议

先用一个生活例子。

两个人可以约定：写字时把重要内容放在纸张左侧，补充内容放在右侧。只要写的人和读的人使用同一规则，外人不需要看懂这种布局，信息也能正确传递。

对模型而言，这个约定不必是人类可读的“主语、谓语、宾语”。它可以是训练自行形成的内部协议：

```text
encoder 决定怎样折叠和摆放信息
decoder 学会怎样读取这种摆放
最终任务 loss 同时约束两者
```

这里的 `private` 不是加密，而是“模型内部自洽，不要求人类手写”。

如果这种协议真的存在，那么强制改用另一套左右选择规则，decoder 应该像拿到错误的字典一样，性能明显下降。反过来，如果随便替换 gate 都几乎没影响，就不能说这个 gate 承载了关键协议。

---

## 3. TreeHeap 状态是怎样折叠的

STONE-1 使用固定宽度为 64 的二叉 TreeHeap。句子的 token embedding 放在 leaf 层，然后两两递归合并：

```text
64 leaves
 -> 32 parents
 -> 16 parents
 -> 8
 -> 4
 -> 2
 -> 1 root
```

每次局部 FOLD 只看一对子节点 `left` 和 `right`。系统包含两个可学习函数：

- `P`：根据 anchor 预测另一侧状态；
- `U`：把预测残差更新到 parent。

当左侧作为 anchor 时：

\[
d = R-P(L)
\]

\[
H_{parent}=L+U(d)
\]

这里的 `detail`，也就是 \(d\)，保存“右侧相对左侧还缺少什么”。UNFOLD 时执行：

\[
L=H_{parent}-U(d)
\]

\[
R=d+P(L)
\]

如果右侧作为 anchor，公式左右对换。一个二值 gate \(g\) 决定方向：

```text
g = 1: left 是 anchor
g = 0: right 是 anchor
```

这样做的好处是，FOLD 与 UNFOLD 在数学设计上成对出现。树向上压缩时保存 parent、detail 和方向；树向下展开时使用同一组信息恢复各层状态。

需要注意：这不是无损压缩整个字符串的产品算法。decoder 看不到最终 leaf 层，只能读取 root 和被允许的压缩层。我们故意关闭了最直接的 token 旁路，迫使翻译至少经过一次结构折叠。

---

## 4. learned kernel 学什么

局部方向 kernel 的输入为：

\[
x=[L, R, L-R, L\odot R]
\]

其中 \(L\odot R\) 是逐元素乘积。kernel 是一个小型两层网络：

\[
p=\sigma(K_{\theta}(x)+b_{depth})
\]

\(p\) 是选择左 anchor 的概率。前向计算把它硬化成 0 或 1，反向传播使用 straight-through estimator，让梯度近似穿过这个离散选择。

同一个 kernel 在整棵树上共享，只额外携带每个深度的 bias。这符合我们此前对 TreeHeap 卷积的要求：**不是为每个地址单独训练一张表，而是让同一个局部算子沿树递归复用。**

但是，这种设计也有风险。decoder 正在学习怎样读取内部坐标时，gate 同时在改变内部坐标。就像一个人学习地图期间，地图的东西方向还在变化。STONE-1 正是要用对照实验判断：这种自由度究竟形成协议，还是只增加优化噪声。

---

## 5. 为什么必须有三种实验臂

三种模型参数规模相同，训练数据、优化器、步数和 decoder 都相同。唯一变化是局部方向：

| 实验臂 | 方向规则 | 它回答的问题 |
|---|---|---|
| `identity` | 所有有效节点固定使用左 anchor | 稳定、规范的坐标系有多强？ |
| `learned_structural` | kernel 根据内容和深度学习 0/1 | 学习方向是否带来额外收益？ |
| `frozen_random` | 固定的地址/深度随机 pattern | 只要规则稳定，任意坐标是否也能工作？ |

这里最容易误解的是 random。

`frozen_random` 不是每一步重新掷骰子。它在训练开始前生成一个固定 pattern，此后永远不变。因此 decoder 有机会适应这套奇怪但稳定的坐标系。如果 learned 连 frozen random 都不能击败，问题很可能不是“树不能放信息”，而是“训练时持续变化的方向没有形成稳定协议”。

---

## 6. 数据和训练合同

正式实验在结果出现前就锁定了配置，不能看完数字再修改及格线：

| 项目 | 正式设置 |
|---|---:|
| 数据源 | WMT-massive 英中 TSV |
| 原始声明行数 | 14,170,275 |
| 独立训练样本 | 1,000,000 |
| 验证 / 测试 | 2,000 / 2,000 |
| 句长过滤 | 8 到 32 token |
| tokenizer | 32K SentencePiece BPE |
| 每个实验臂随机种子 | 3 |
| 总训练臂 | 9 |
| batch size | 64 |
| 每臂更新 | 15,625 |
| 每臂参数量 | 27,769,097 |
| heap width | 64 |
| GPU | RTX 3090 |

训练、验证和测试内容经过 hash 检查，没有交叉泄漏。正式任务运行 `27,268.44` 秒，也就是约 `7.57` 小时，退出码为 0，`stderr.log` 为空。

因此，后面的负结果不是程序崩溃、GPU 掉卡、测试集泄漏或某个文件没有加载造成的。

---

## 7. 先学会看 NLL 和 BLEU

### 7.1 NLL：模型给正确答案多少概率

假设正确 token 是 \(y_t\)，模型给它的概率是 \(p(y_t)\)，平均负对数似然为：

\[
\operatorname{NLL}=-\frac{1}{T}\sum_{t=1}^{T}\log p(y_t)
\]

NLL 越小越好。它不是“错误百分比”，而是模型对正确答案分配概率的总体成本。

例如：

```text
模型 A 给正确词概率 0.50 -> -log(0.50) 约 0.69
模型 B 给正确词概率 0.10 -> -log(0.10) 约 2.30
```

模型 A 的 NLL 更低，说明它更确信正确答案。

### 7.2 BLEU-4：生成句和参考句有多少局部片段重合

BLEU-4 检查 1 到 4 token 片段的重合情况，并惩罚过短输出。它越高越好，但不是语义理解的完整评价。两个意思相近、措辞不同的句子，BLEU 可能仍然不高。

本实验使用 token BLEU-4，主要用来防止一种假进步：teacher-forcing NLL 下降了，但模型自由生成时仍然是空字符串或重复乱码。

### 7.3 标准差：换颗随机种子还可靠吗

同一程序从不同随机初始化出发，结果可能不同。三颗种子的 NLL 标准差越小，说明方案越稳定。

STONE-1 预注册的主要产品目标是：

```text
learned mean NLL <= 3.90
learned BLEU-4   >= 13.5
NLL 标准差       <= 0.05
非空生成率        = 1.00
严重重复率        <= 0.10
```

---

## 8. 正式结果：identity 赢了

三颗种子的平均结果如下：

| 方案 | Test NLL，越低越好 | NLL 标准差 | BLEU-4，越高越好 | 严重重复率 |
|---|---:|---:|---:|---:|
| identity | **4.0719** | **0.0058** | **11.1735** | **0.0397** |
| learned structural | 4.2269 | 0.1125 | 9.7875 | 0.0558 |
| frozen random | 4.1210 | 0.0106 | 10.7198 | 0.0430 |

learned 相对 identity 的 NLL 差值是：

\[
4.2269-4.0719=+0.1550
\]

正数意味着 learned 更差。它相对 frozen random 也差 `+0.1059`。

这不是一颗坏种子造成的。逐种子比较：

| Seed | identity NLL | learned NLL | random NLL | learned - identity |
|---:|---:|---:|---:|---:|
| 71901 | 4.0799 | 4.3858 | 4.1359 | +0.3059 |
| 71902 | 4.0691 | 4.1538 | 4.1121 | +0.0847 |
| 71903 | 4.0666 | 4.1411 | 4.1149 | +0.0746 |

三颗种子全部是 identity 最好，learned 最差。seed 71901 的 learned 出现了明显失败尾部，使 learned 的标准差达到 `0.1125`，超过预注册上限两倍以上。

所以第一层结论很明确：

> **在这一百万样本、一步训练遍历、hard straight-through gate 的配方中，可学习方向没有改善翻译，反而降低了平均质量和稳定性。**

---

## 9. 但是模型真的用了树地址

只看上表，可能会得出一个过快结论：“TreeHeap 没有用。”干预实验否定了这种说法。

我们取 learned seed 71903 的最佳 checkpoint，在测试时主动改变内部结构：

| 干预 | NLL | 相对正常模型的损伤 |
|---|---:|---:|
| 正常 learned | 4.1411 | 0 |
| 强制全部 identity | 4.1293 | **-0.0118，反而改善** |
| 强制 frozen random | 4.1446 | +0.0034，几乎无变化 |
| 交换每层 left/right 地址 | 5.6359 | **+1.4948，严重损坏** |

NLL 从 `4.1411` 上升到 `5.6359` 不是轻微波动。对应的困惑度从约 `62.87` 上升到 `280.32`。

这说明 decoder 不是把所有内部节点当成无序 word bag。它确实区分：

```text
这个状态在左地址
那个状态在右地址
这个节点位于哪一层
```

一旦整体交换左右地址，decoder 原来学到的读取方式就失效了。

但另外两项干预同样关键：把 learned gate 替换成 identity 不但没有伤害，反而稍有改善；替换成 random 也几乎不痛。这说明**地址是协议的一部分，而 learned gate 不是当前协议中不可替代的一部分。**

可以把它类比成一座图书馆：

```text
书架编号非常重要，全部左右互换会让读者找不到书；
但管理员训练出来的临时摆书策略并没有比固定规则更好。
```

---

## 10. gate 内部发生了什么

learned gate 没有完全随机。它显示出一个很有信息量的模式：

- 靠近 root 的深层 gate 大量饱和到固定方向；
- 部分浅层 gate 仍然有较高概率熵；
- 不同 seed 的硬方向比例差异明显；
- 最终策略整体在接近 identity，但保留了一批不稳定的局部翻转。

例如 seed 71903：

| FOLD 深度 | 左 anchor 概率均值 | 概率熵 | 硬 left 比例 |
|---:|---:|---:|---:|
| 0 | 0.5274 | 0.6554 | 0.7334 |
| 1 | 0.5520 | 0.6224 | 0.9971 |
| 2 | 0.6098 | 0.5426 | 1.0000 |
| 3 | 0.6093 | 0.5415 | 0.7070 |
| 4 | 0.9812 | 0.0792 | 1.0000 |
| 5 | 0.9881 | 0.0085 | 0.9844 |

概率熵接近 `0.69` 表示接近五五开，接近 0 表示几乎完全确定。表中浅层仍有较大不确定性，深层则接近固定 left。

一种与证据相容的机制解释是：

1. identity 从训练第一步起就是稳定坐标系；
2. frozen random 虽然奇怪，但也从第一步起不变；
3. learned gate 随参数更新不断改变部分局部坐标；
4. decoder 一边学读取，一边面对坐标变化；
5. 最后 gate 大体退回 identity，但训练已经付出了额外优化成本。

这是**机制诊断**，还不是新 Claim。要证明“移动坐标系是根因”，下一轮必须记录 gate 随训练时间的翻转率，并用稳定化对照直接验证，而不能只凭最终统计讲故事。

---

## 11. FOLD/UNFOLD 闭包通过了吗

从均方误差看，闭包非常接近精确：约 `1e-13`。也就是说，把状态 FOLD 后再 UNFOLD，绝大部分数值可以恢复到浮点精度附近。

但我们预注册了更严格的最大绝对误差门槛：

```text
closure_max_abs < 1e-5
```

learned 的三颗种子分别约为：

```text
2.15e-5
0.51e-5
2.86e-5
```

其中两颗超过阈值，所以结构门 S6 必须记为失败。我们不能在看到结果后说“其实 `3e-5` 也差不多”，然后修改及格线。

从工程判断看，这更像 float32 多层运算积累的尾部误差，而不是 FOLD/UNFOLD 已经失去逆运算关系。但要让它成为可靠数学工具，下一轮仍应加入 float64 审计、误差随深度的增长曲线，以及确定性的闭包单元测试。

---

## 12. 生成效果到了什么水平

learned checkpoint 能由 CLI 加载，能够在没有 teacher forcing 的情况下生成非空输出。它不是只会返回 loss 的实验脚本。

一个例子：

```text
输入：Integrated, standards-based certification labeling and reporting
参考：集成的、基于标准的认证标签和报告
输出：合规性、基于标准、报告和报告
```

可以看到，模型已经抓住了“标准、报告”等局部对应关系，句子也不是完全随机字符；但它丢失了“认证标签”，并重复了“报告”。

另一个例子：

```text
输入：Requested URL: /FixedCamera/ANF24A.aspx
参考：请求的 URL : / ProList.aspx
输出：请求的 URL : / newslist.aspx
```

它学会了网页错误文本的常见模板，却没有忠实复制路径。这也反映了训练语料的现实问题：WMT-massive 中含有网页片段、产品表、错配双语和 mojibake。模型可以学习统计形式，但这些数据不等于高质量翻译知识。

工程指标倒是全部通过：

| 指标 | 结果 | 门槛 |
|---|---:|---:|
| batch-1 greedy P50 | 27.42 ms | <= 1,000 ms |
| 峰值显存 | 约 1.70 GiB | <= 4 GiB |
| checkpoint | 111,087,481 bytes | <= 300 MiB |
| 非空生成率 | 1.00 | = 1.00 |
| 严重重复率 | 0.0558 | <= 0.10 |

因此它是一个可运行的研究 CLI，不是一个达到质量里程碑的翻译产品。

---

## 13. 像体检报告一样读最终裁决

STONE-1 把门槛分为三组：

| 维度 | 通过情况 | 体检解释 |
|---|---:|---|
| 产品质量 Q | 2 / 5 | 能生成，但 NLL、BLEU、稳定性未达标 |
| 结构证据 S | 1 / 6 | 地址因果成立，learned gate 协议不成立 |
| 工程可用 E | 5 / 5 | 运行、显存、延迟、checkpoint、CLI 正常 |

最终状态是：

```text
not_supported_under_recipe
```

中文不是“整个项目失败”，而是：

> **在预先规定的这份配方下，STONE-1 的完整 Claim 不成立。**

具体地说：

### 已有正向证据

1. 固定容量 TreeHeap 可以完成真实英中 seq2seq 训练与生成。
2. decoder 对 left/right 地址高度敏感。
3. 递归 FOLD/UNFOLD 数值上接近闭合。
4. 一百万样本、九次训练的工程流程稳定完成。
5. identity 和 frozen random 的低方差说明稳定结构可以被 decoder 学习。

### 被本实验否定的部分

1. hard learned direction gate 会自然击败固定 identity。
2. learned gate 会自然击败固定 random。
3. 强行替换 learned gate 会造成明显性能损失。
4. 当前 checkpoint 达到 NLL `3.90` 和 BLEU `13.5` 的工程目标。
5. 三颗随机种子已经形成稳定一致的 learned protocol。

### 本实验根本没有证明的事

```text
TreeHeap 已具备开放对话能力
TreeHeap 已学会世界模型
root 具有人类可读语义
内部旋转等价于意识活动
TreeHeap 优于工业规模 Transformer
继续扩数据一定能修复 learned gate
```

把这些边界写清楚，不是削弱研究，而是保护后续工作不被过强故事带偏。

---

## 14. 为什么这个负结果反而推进了理论

在实验前，我们容易把下面两件事当成同一件：

```text
模型使用树结构
=
模型学会了树上的私有协议
```

STONE-1 证明它们不是一回事。

地址交换造成巨大损失，说明树的结构坐标已经参与预测；learned gate 可以被替换，说明“可学习局部方向”还不是有用协议。换句话说：

```text
TreeHeap 是有效载体
不等于
任意可学习算子都会自动成为有效编码协议
```

这与 Transformer 研究中的一个朴素事实一致：可微、参数多、能够反向传播，只能保证“可以优化”；不能保证某个自由度一定被任务识别、一定产生独特功能。

本轮还暴露出一个更深的数学问题：局部左右方向近似一种 \(\mathbb{Z}_2\) 选择，也就是每个节点都有“保持/翻转”两种等价表示。如果任务 loss 无法稳定识别哪种表示更优，这个自由度就可能成为 gauge freedom，而不是知识。identity 相当于先固定一个规范坐标，训练自然更容易。

因此，私有协议不应只定义“模型可以选择什么”，还要定义：

```text
什么信号让某个选择比另一个选择更有价值？
这个选择何时稳定下来？
decoder 如何持续看见同一套坐标？
压缩收益怎样抵消结构选择的优化成本？
```

这正是下一轮 Claim 应该回答的内容。

---

## 15. 下一步不应该只是“再跑久一点”

大部分实验臂在最后一次或倒数一次评估取得最好 NLL，说明绝对质量可能尚未完全收敛。继续训练有可能让 identity、random 和 learned 全部改善。

但当前没有证据表明 learned 会反超。简单把相同配方从一轮数据改成十轮，只会花更多 GPU 时间回答一个不够尖锐的问题。

更合理的下一轮应先定位“移动坐标”假设。可以预注册三个对照：

### A. identity warm-up

训练前期固定 identity，让 encoder-decoder 先建立稳定读取协议；后期才开放 gate。

### B. soft-to-hard annealing

早期使用连续 gate，让结构缓慢变化；温度逐步降低，最后才坍缩为 0/1。

### C. alternating freeze

固定 decoder，短暂训练 gate；再固定 gate，训练 decoder。这样可以区分“gate 没有价值”和“两边同时移动导致学不会”。

下一轮必须额外记录：

```text
每层 gate 的翻转率随 step 如何变化
同一句话跨 checkpoint 的结构地址是否稳定
固定 gate 后 decoder 是否快速恢复
开放 gate 是否真的降低验证 NLL
学习到的结构是否比 identity 节省读取成本或改善泛化
```

只有这些 predict 通过，才能把“移动坐标是根因”升级为 Claim。

---

## 16. 可复现材料

实验 Claim：

```text
S3-STONE1-PRIVATE-PROTOCOL-C01
```

代码与 ARA：

```text
ara/s3-generation/src/s3_stone1_private_protocol.py
ara/s3-generation/src/treeheap_cli.py
ara/s3-generation/logic/stone1_private_protocol_translation.md
ara/s3-generation/evidence/s3_stone1_private_protocol/
```

正式证据目录包含：

```text
REPORT.md
REVIEW.md
summary.json
runs.json
interventions.json
trace.jsonl
dataset_manifest.json
config.json
command.sh
stdout.log
stderr.log
cli_smoke.json
runner_status.json
```

代码和证据已提交到 SameTime 的 `experiment/private-protocol-battle` 分支，正式结果提交为：

```text
c07077b ara: record STONE-1 formal result
```

demo checkpoint 保存在 io，大小 `111,087,481` bytes，SHA-256：

```text
732b9b367a1c473d790a46dfca8698d41608453ab965c747c33639d889c76d56
```

---

## 17. 结论

STONE-1 没有达到我们预注册的完整目标，但它给出了一条比模糊乐观更有价值的分界线：

> **TreeHeap 的左右地址已经是翻译模型的因果变量；当前 hard straight-through 方向 gate 还不是有效私有协议。**

identity 最好，不意味着 TreeHeap 只能固定不动。它意味着在要求结构自由生长之前，我们必须给模型一个能够形成稳定共同语言的学习过程。一个合法、可逆、可微的算子，只是候选工具；只有当任务干预证明模型离不开它时，它才成为协议。

这艘船没有沉。它只是第一次用正式仪器测出：发动机在转，方向舵还没有接上传动轴。

> **License: GPLv3。本文中的 TreeHeap 私有协议、实验设计、数据表述和 ARA 结论按项目许可证公开，欢迎复现、批评和提出反证。**
