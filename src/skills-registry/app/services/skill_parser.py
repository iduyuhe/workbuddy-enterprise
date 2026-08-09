"""Anthropic Skills 文件式规范解析：读取目录中的 SKILL.md，解析 frontmatter 为 manifest。"""
import os
import re
import uuid
from typing import Any

import yaml

_FRONT_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


def parse_skill_md(text: str) -> dict[str, Any]:
    """解析 SKILL.md 文本，返回 {frontmatter, description, body_preview}。

    Anthropic Skills 规范中 SKILL.md 头部是 YAML frontmatter，
    至少包含 name / description 字段。
    """
    frontmatter: dict[str, Any] = {}
    body = text
    m = _FRONT_RE.match(text)
    if m:
        try:
            frontmatter = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            frontmatter = {}
        body = m.group(2)

    return {
        "frontmatter": frontmatter,
        "name": frontmatter.get("name"),
        "description": frontmatter.get("description", ""),
        "body_preview": body[:1000],
        "raw_length": len(text),
    }


def load_manifest_from_storage(storage_path: str) -> dict[str, Any] | None:
    """尝试从 storage_path 读取 SKILL.md 并解析为 manifest。

    storage_path 可以是：
      - 目录（含 SKILL.md）
      - 直接的 .md 文件
    读取失败返回 None（调用方决定是否降级为仅存路径）。
    """
    if not storage_path:
        return None
    if os.path.isdir(storage_path):
        candidate = os.path.join(storage_path, "SKILL.md")
    else:
        candidate = storage_path

    if not os.path.isfile(candidate):
        return None
    try:
        with open(candidate, "r", encoding="utf-8") as f:
            return parse_skill_md(f.read())
    except OSError:
        return None


def bump_version(current: str | None) -> str:
    """将 semver 的 patch 段 +1，缺省从 0.1.0 起。"""
    if not current:
        return "0.1.0"
    parts = current.split(".")
    try:
        parts[-1] = str(int(parts[-1]) + 1)
    except (ValueError, IndexError):
        return "0.1.0"
    return ".".join(parts)


def new_invocation_id() -> uuid.UUID:
    return uuid.uuid4()
