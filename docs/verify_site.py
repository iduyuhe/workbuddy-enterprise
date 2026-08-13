#!/usr/bin/env python3
"""
verify_site.py —— WorkBuddy Enterprise 文档站与示例库一致性校验。

校验范围：
  1. mkdocs.yml 语法合法，且 nav 引用的所有文档页真实存在。
  2. examples/ 下每个 SKILL.md 的 frontmatter 含 name / description。
  3. marketplace-package/manifest.yaml 必填字段齐全。
  4. agent-playbook 的 manifest.resources 与 playbook.defaults 引用一致，
     且 call_mcp_tool 的 tool 落在对应 MCP 连接器 tools 清单内。

退出码：0 = 全部通过，1 = 存在错误。可在 CI 中运行。
"""
import os
import re
import sys
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")

ERRORS = []
WARNINGS = []


def err(msg):
    ERRORS.append(msg)


def warn(msg):
    WARNINGS.append(msg)


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def collect_nav_pages(node, out):
    """递归收集 mkdocs nav 中的 .md 页面路径（相对 docs_dir）。"""
    if isinstance(node, str):
        if node.endswith(".md"):
            out.append(node)
    elif isinstance(node, list):
        for item in node:
            collect_nav_pages(item, out)
    elif isinstance(node, dict):
        for v in node.values():
            collect_nav_pages(v, out)


def check_mkdocs():
    mk = os.path.join(ROOT, "mkdocs.yml")
    if not os.path.exists(mk):
        err(f"[mkdocs] 缺少 mkdocs.yml")
        return
    cfg = load_yaml(mk)
    nav = cfg.get("nav", [])
    pages = []
    collect_nav_pages(nav, pages)
    if not pages:
        warn("[mkdocs] nav 未解析到任何 .md 页面")
    missing = 0
    for p in pages:
        target = os.path.join(DOCS, p)
        if not os.path.exists(target):
            err(f"[mkdocs] nav 引用页面不存在: docs/{p}")
            missing += 1
    print(f"[mkdocs] nav 解析到 {len(pages)} 个页面，缺失 {missing} 个")


def check_skill(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        err(f"[skill] 缺少 YAML frontmatter: {os.path.relpath(path, ROOT)}")
        return
    fm = yaml.safe_load(m.group(1))
    if not isinstance(fm, dict):
        err(f"[skill] frontmatter 非字典: {os.path.relpath(path, ROOT)}")
        return
    for field in ("name", "description"):
        if not fm.get(field):
            err(f"[skill] frontmatter 缺字段 '{field}': {os.path.relpath(path, ROOT)}")


def check_examples():
    examples_dir = os.path.join(ROOT, "examples")
    if not os.path.isdir(examples_dir):
        err("[examples] 缺少 examples/ 目录")
        return

    # 1) 所有 SKILL.md 的 frontmatter
    skill_files = []
    for root, _, files in os.walk(examples_dir):
        for fn in files:
            if fn == "SKILL.md":
                skill_files.append(os.path.join(root, fn))
    for sp in skill_files:
        check_skill(sp)
    print(f"[examples] 找到 {len(skill_files)} 个 SKILL.md")

    # 2) marketplace-package/manifest.yaml 必填字段
    mp = os.path.join(examples_dir, "marketplace-package", "manifest.yaml")
    if os.path.exists(mp):
        m = load_yaml(mp)
        required = ["slug", "name", "package_type", "publisher", "version", "resources"]
        for fld in required:
            if not m.get(fld):
                err(f"[marketplace] manifest 缺必填字段 '{fld}': {os.path.relpath(mp, ROOT)}")
        # resources.skills[].storage_path 指向的目录应含 SKILL.md
        for sk in (m.get("resources") or {}).get("skills", []) or []:
            sp = sk.get("storage_path")
            if sp:
                cand = os.path.join(os.path.dirname(mp), sp, "SKILL.md")
                if not os.path.exists(cand):
                    err(f"[marketplace] 技能 storage_path 无 SKILL.md: {sp} ({os.path.relpath(mp, ROOT)})")
        print(f"[marketplace] manifest 校验完成: {m.get('slug')}")
    else:
        warn("[marketplace] 缺少 examples/marketplace-package/manifest.yaml")

    # 3) agent-playbook 引用完整性
    ap = os.path.join(examples_dir, "agent-playbook", "manifest.yaml")
    if os.path.exists(ap):
        m = load_yaml(ap)
        res = m.get("resources") or {}
        logical_ids = set()
        mcp_specs = {}
        for kind in ("knowledge_bases", "skills", "mcp_servers", "agents"):
            for item in res.get(kind, []) or []:
                lid = item.get("logical_id")
                if lid:
                    logical_ids.add(lid)
                if kind == "mcp_servers" and item.get("spec"):
                    mcp_specs[lid] = os.path.join(os.path.dirname(ap), item["spec"])
        # 读取每个 mcp spec 的 tools
        mcp_tools = {}
        for lid, spec_path in mcp_specs.items():
            if os.path.exists(spec_path):
                spec = load_yaml(spec_path)
                mcp_tools[lid] = [t.get("name") for t in (spec.get("tools") or [])]
            else:
                err(f"[agent] MCP spec 不存在: {spec_path}")

        pb_path = os.path.join(examples_dir, "agent-playbook", "agent", "playbook.yaml")
        if os.path.exists(pb_path):
            pb = load_yaml(pb_path)
            defaults = (pb.get("agent") or {}).get("defaults") or {}
            for key in ("kb_id", "skill_id", "mcp_server_id"):
                val = defaults.get(key)
                if val and val not in logical_ids:
                    err(f"[agent] playbook.defaults.{key}={val} 不在 manifest.resources 中")
            for step in (pb.get("agent") or {}).get("scenario_flow") or []:
                if step.get("action") == "call_mcp_tool":
                    tgt = step.get("target")
                    tool = step.get("tool")
                    if tgt not in mcp_tools:
                        err(f"[agent] scenario_flow 引用未知 mcp_server: {tgt}")
                    elif tool not in (mcp_tools.get(tgt) or []):
                        err(f"[agent] scenario_flow tool '{tool}' 不在 MCP '{tgt}' 的 tools 清单内")
            print(f"[agent] playbook 引用完整性校验完成")
        else:
            err("[agent] 缺少 examples/agent-playbook/agent/playbook.yaml")
    else:
        warn("[agent] 缺少 examples/agent-playbook/manifest.yaml")


def main():
    print("=== WorkBuddy Enterprise · 文档站与示例库校验 ===")
    check_mkdocs()
    check_examples()
    print("")
    for w in WARNINGS:
        print(f"  ⚠ {w}")
    for e in ERRORS:
        print(f"  ✗ {e}")
    print("")
    if ERRORS:
        print(f"结果：失败 —— {len(ERRORS)} 个错误，{len(WARNINGS)} 个警告")
        sys.exit(1)
    print(f"结果：通过 ✅ —— 0 错误，{len(WARNINGS)} 个警告")
    sys.exit(0)


if __name__ == "__main__":
    main()
