#!/usr/bin/env python3
"""Create the next SPR article from the publishing contract."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import tomllib
from pathlib import Path


NUMBER_RE = re.compile(r"^(\d{3})-")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def yaml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def next_number(directory: Path) -> int:
    numbers = []
    for path in directory.glob("[0-9][0-9][0-9]-*.md"):
        match = NUMBER_RE.match(path.name)
        if match:
            numbers.append(int(match.group(1)))
    return max(numbers, default=0) + 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("slug", help="lowercase URL slug, for example local-axis-routing")
    parser.add_argument("title", help="article title without the SPR number")
    parser.add_argument("--description", required=True)
    parser.add_argument("--author")
    parser.add_argument("--dry-run", action="store_true", help="print the article without writing it")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    if not SLUG_RE.fullmatch(args.slug):
        parser.error("slug must contain lowercase ASCII letters, digits and single hyphens")

    repo = args.repo.resolve()
    config = tomllib.loads((repo / "publishing.toml").read_text(encoding="utf-8"))
    spr_dir = repo / "src" / "spr"
    number = next_number(spr_dir)
    date = dt.date.today().isoformat()
    author = args.author or config["spr"]["default_author"]
    path = spr_dir / f"{number:03d}-{args.slug}.md"
    if path.exists():
        parser.error(f"article already exists: {path}")

    text = f'''---
title: {yaml_string(f"[SPR-{number:03d}] {args.title}")}
date: {date}
lastmod: {date}
weight: {number}
author: {author}
description: {yaml_string(args.description)}
keywords: [TreeHeap, SPR, ARA]
tags: [SPR, TreeHeap, ARA]
---

# 问题

本文要验证什么？

{{{{< claim id="C{number:03d}-01" status="hypothesis" >}}}}
写出可以被实验否证的 Claim。
{{{{< /claim >}}}}

# 方法

记录公式、控制变量、数据与实现合同。

# 证据

{{{{< evidence grade="E0" source="pending" >}}}}
尚无正式证据。实验完成后更新等级、来源和边界。
{{{{< /evidence >}}}}

# 结论边界

明确本文证明了什么，以及没有证明什么。
'''
    if args.dry_run:
        print(f"# target: {path}")
        print(text, end="")
        return 0

    path.write_text(text, encoding="utf-8", newline="\n")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
