#!/usr/bin/env python3
"""Validate the stable publishing contract without adding YAML dependencies."""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path


ARTICLE_RE = re.compile(r"^(\d{3})-(.+)\.md$")
TITLE_RE = re.compile(r'^\[SPR-(\d{3})\]')
FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$")
TEXT_FENCE_RE = re.compile(r"```text\s*\n(.*?)\n```", re.DOTALL)
MATH_IN_TEXT_RE = re.compile(
    r"(?:sum_|sqrt\(|sigmoid\(|softmax\(|theta_|mu_|delta_|"
    r"P\([^\n]*\|[^\n]*\)|FOLD\([^\n]*\)\s*=)",
    re.IGNORECASE,
)


def parse_front_matter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening front matter delimiter")

    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        match = FIELD_RE.match(line)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    raise ValueError("missing closing front matter delimiter")


def unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def validate(repo: Path) -> list[str]:
    config = tomllib.loads((repo / "publishing.toml").read_text(encoding="utf-8"))
    spr_config = config["spr"]
    strict_from = int(spr_config["strict_from"])
    required = tuple(spr_config["required_fields"])
    description_min = int(spr_config["description_min"])
    description_max = int(spr_config["description_max"])

    errors: list[str] = []
    seen: dict[int, Path] = {}
    articles = sorted((repo / "src" / "spr").glob("[0-9][0-9][0-9]-*.md"))

    for path in articles:
        match = ARTICLE_RE.match(path.name)
        if not match:
            continue
        number = int(match.group(1))
        if number in seen:
            errors.append(f"duplicate SPR-{number:03d}: {seen[number].name}, {path.name}")
        seen[number] = path

        try:
            fields = parse_front_matter(path)
        except ValueError as exc:
            errors.append(f"{path.name}: {exc}")
            continue

        if number < strict_from:
            continue

        title = unquote(fields.get("title", ""))
        title_match = TITLE_RE.match(title)
        if not title_match or int(title_match.group(1)) != number:
            errors.append(f"{path.name}: title must start with [SPR-{number:03d}]")

        for field in required:
            if not fields.get(field):
                errors.append(f"{path.name}: missing required field '{field}'")

        weight = fields.get("weight", "")
        if weight and (not weight.isdigit() or int(weight) != number):
            errors.append(f"{path.name}: weight must equal {number}")

        description = unquote(fields.get("description", ""))
        if description and not description_min <= len(description) <= description_max:
            errors.append(
                f"{path.name}: description length {len(description)} is outside "
                f"[{description_min}, {description_max}]"
            )

    if not articles:
        errors.append("no SPR articles found")

    math_contract_paths = [
        repo / "src" / "treeheap-paper" / "001-treeheap-emergent-protocol.md"
    ]
    for path in math_contract_paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8-sig")
        for block in TEXT_FENCE_RE.finditer(text):
            match = MATH_IN_TEXT_RE.search(block.group(1))
            if match:
                line = text.count("\n", 0, block.start()) + 1
                errors.append(
                    f"{path.relative_to(repo)}:{line}: math-like expression "
                    f"'{match.group(0)}' is inside a text code fence; use LaTeX delimiters"
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    errors = validate(args.repo.resolve())
    if errors:
        for error in errors:
            print(f"content validation failed: {error}", file=sys.stderr)
        return 1

    print("Content validation passed: SPR numbering and current publishing metadata are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
