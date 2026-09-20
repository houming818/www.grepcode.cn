# WSL 发布手册

本仓库是 `www.grepcode.cn` 的独立 Hugo 仓库。`main` 分支推送成功后，Gitea CI 会构建站点、执行 SEO 审计，并部署到腾讯 COS。

## 首次安装

在 WSL Ubuntu 中执行：

```bash
cd /mnt/e/ws/codexspace/log/blogs/www.grepcode.cn
sh scripts/install-hugo-wsl.sh
```

Hugo Extended `0.146.7` 固定安装到 `~/.local/share/grepcode-blog/hugo/`，入口为 `~/.local/bin/hugo`，不需要 `sudo`。该版本满足当前 PaperMod 的 `>=0.146.0` 合同。

安装完成后，本机还提供统一入口 `~/.local/bin/grepcode-blog`。在任意目录都可以运行：

```bash
grepcode-blog status
grepcode-blog build
grepcode-blog preview
```

## 构建与预览

```bash
sh scripts/build-site.sh
sh scripts/preview-site.sh
```

预览默认监听 `http://localhost:1313/`。可用 `HUGO_PORT=1413` 修改端口。

## 新建 SPR

框架会扫描现有文章并分配下一个编号，同时生成符合发布合同的 Front Matter、Claim 和 Evidence 骨架：

```bash
grepcode-blog new local-axis-routing "局部主轴如何形成递归路由" \
  --description "本文定义局部主轴路由的计算合同、可证伪条件与第一阶段证据边界。"
```

从 `SPR-089` 起，构建会严格检查编号、标题、`weight`、日期、作者、摘要、关键词和标签。历史文章只检查文件编号唯一性，不要求一次性返工。

专题首页的“最新研究”由 `latest-spr` shortcode 自动生成，不再手工维护链接列表。

研究组件写法：

```markdown
{{< claim id="C090-01" status="hypothesis" >}}
这是一个可被否证的假设。
{{< /claim >}}

{{< evidence grade="E2" source="ARA/F01" >}}
这里记录证据、来源和适用边界。
{{< /evidence >}}
```

## 发布

发布脚本只暂存明确列出的文件，不会使用 `git add .`：

```bash
sh scripts/publish-site.sh \
  "blog: publish SPR-089 local-axis fall design" \
  src/spr/089-treeheap-simplex-local-axis-fall.md
```

等价的全局命令是：

```bash
grepcode-blog publish \
  "blog: publish SPR-089 local-axis fall design" \
  src/spr/089-treeheap-simplex-local-axis-fall.md
```

脚本依次执行完整构建、SEO 审计、凭据特征检查、提交和 `git push origin main`。COS 密钥只存在于 Gitea Secrets，本地脚本不保存也不打印这些值。
