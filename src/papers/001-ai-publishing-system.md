+++
title = "[PAPERS-001] 本博客的发布约定 / Publishing Conventions of This Blog"
date = 2026-05-19
weight = 1
author = "nio (Houming818) & opencode (First Mate)"
role = "nio: system design direction, content review； opencode: first draft, technical research, editorial execution"
review = "Reviewed and released by nio on 2026-05-19."
keywords = ["AI publishing", "attribution", "co-authorship", "RSS", "static site", "paper system"]
description = "本博客采用的发布规范: role declarations, license, content traceability, review records, full-text RSS."
tags = ["Publishing", "AI", "Co-authorship", "RSS"]
+++

# 本博客的发布约定 / Publishing Conventions of This Blog

> 这不是对任何系统的替代或批评——只是说清楚，这个博客自己选择怎么发布内容。
> This is not a replacement for or criticism of any existing system — it simply states how this blog chooses to publish its content.

<table>
<tr>
<td width="50%" style="vertical-align:top; padding-right:16px;">

## 署名：角色声明，不排座次

传统学术用第一作者和通讯作者分权责。本博客不沿袭这套——不是因为传统不对，是因为我们的协作方式用不着那套分类。这里选一套更细粒度的写法。

当一篇文章的作者包括人类和 AI 时，写清楚每个人做了什么就够了。比如 TF-001：人类提供方向定义、术语校正、架构立场校准；AI 提供初稿撰写、代码引用、文献检索。不需要区分"谁排第一"——只需要知道**谁承担了什么**。

</td>
<td width="50%" style="vertical-align:top; padding-left:16px; border-left:1px solid var(--border);">

## Attribution: Roles, Not Rankings

Traditional academic publishing uses first author and corresponding author to divide credit and responsibility. This blog doesn't follow that convention — not because it's wrong, but because our collaboration model doesn't need it. We chose a more granular approach.

When an article's authors include both a human and an AI, it's enough to state what each did. Example from TF-001: the human provided direction, terminology correction, and architecture stance calibration; the AI provided first-draft writing, code references, and literature search. No need to distinguish "who is first" — just know **who bore what**.

</td>
</tr>
</table>

---

## 本系统的三个约定 / The Three Conventions

每篇发布的内容，遵循三个约定，按优先级排列：
Every published piece follows three conventions, in order of priority:

1. **使用许可 / License** — 别人能拿这篇内容干什么 / What can others do with this content?
2. **谁做了什么 / Who did what** — 每个人在创作链条上的具体角色 / The specific roles each author played in the creative chain.
3. **审阅经过了什么 / Review trail** — 谁在什么时间审阅、提出了什么意见、修改是否执行 / Who reviewed what, when, what changes were requested, and whether they were made.

具体做法——不需要新平台 / The concrete implementation — no new platform needed:

---

### 1. 许可证 / License

每篇文章底部声明许可证 / Every article declares its license at the bottom:

```text
> License: GPLv3 — 允许复制、修改、分发，但必须继承相同开源协议。
> License: GPLv3 — Copy, modify, distribute, but must retain the same open-source license.
```

无许可证不发布 / No license, no publish.

---

<table>
<tr>
<td width="50%" style="vertical-align:top; padding-right:16px;">

### 2. Markdown 头部元数据

在每篇文章的 Front Matter 中声明两个字段：

```yaml
author: nio (Houming818) & opencode
role: >-
  nio: 方向定义、内容审查、术语校正；
  opencode: 初稿撰写、代码引用、编辑执行
review: >-
  由 nio 于 2026-05-17 至 05-19 多轮审阅。
```

`role` 替代"第一作者/通讯作者"——不排座次，只声明贡献类型。`review` 记录审阅链条。

</td>
<td width="50%" style="vertical-align:top; padding-left:16px; border-left:1px solid var(--border);">

### 2. Front Matter Metadata

Two fields in every article's YAML header:

```yaml
author: nio (Houming818) & opencode
role: >-
  nio: direction, review, terminology correction;
  opencode: draft, code references, editorial
review: >-
  Reviewed by nio across multiple rounds (2026-05-17 to 05-19).
```

`role` replaces "first author / corresponding author" — no ranking, just a statement of contribution type. `review` records the review chain.

</td>
</tr>
</table>

---

<table>
<tr>
<td width="50%" style="vertical-align:top; padding-right:16px;">

### 3. Git 内容溯源

`git log --follow -- <file>` 可以还原全文的修改历史：谁、什么时候、改了哪一行。传统同行评审做不到这个粒度。

</td>
<td width="50%" style="vertical-align:top; padding-left:16px; border-left:1px solid var(--border);">

### 3. Git-Based Traceability

`git log --follow -- <file>` reconstructs the full revision history: who, when, which line. Traditional peer review cannot achieve this granularity.

</td>
</tr>
</table>

---

<table>
<tr>
<td width="50%" style="vertical-align:top; padding-right:16px;">

### 4. RSS 扩展命名空间

在 RSS 2.0 基础上定义 `ap` 命名空间（`xmlns:ap="https://www.grepcode.cn/ns/ai-papers"`），每个 `<item>` 增加两个子元素：

```xml
<ap:role>nio: 方向定义、内容审查; opencode: 初稿撰写、编辑执行</ap:role>
<ap:review>由 nio 于 2026-05-17 至 05-19 多轮审阅...</ap:review>
```

外加 `ShowFullTextinRSS = true`，全文送达而非摘要——学术内容必须完整可读。

</td>
<td width="50%" style="vertical-align:top; padding-left:16px; border-left:1px solid var(--border);">

### 4. RSS Extension Namespace

An `ap` namespace (`xmlns:ap="https://www.grepcode.cn/ns/ai-papers"`) is defined on top of RSS 2.0. Each `<item>` gains two child elements:

```xml
<ap:role>nio: direction, review; opencode: draft, editorial</ap:role>
<ap:review>Reviewed by nio, 2026-05-17 to 05-19...</ap:review>
```

Additionally, `ShowFullTextinRSS = true` — full text delivery, not just summaries.

</td>
</tr>
</table>

---

<table>
<tr>
<td width="50%" style="vertical-align:top; padding-right:16px;">

### 5. 署名

署名即声明版权归属和许可条件。不隐含任何担保或责任——与 GPLv3 的 NO WARRANTY 一致。

</td>
<td width="50%" style="vertical-align:top; padding-left:16px; border-left:1px solid var(--border);">

### 5. Attribution

Attribution declares copyright ownership and license terms. It implies no warranty or liability — consistent with GPLv3's NO WARRANTY clause.

</td>
</tr>
</table>

---

> **License: GPLv3** — 本文采用 GPLv3 协议开源发布 / This article is released under the GPLv3 open-source license.
