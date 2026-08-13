"""标杆 POC 共享逻辑：加载 manifest、解析资源引用、构建发布计划。

被 validate_poc.py 与 provision.py 复用。所有路径解析相对 manifest 所在目录，
确保无论从哪个工作目录运行脚本都能正确定位技能 / 知识库 / 连接器文件。
"""
from __future__ import annotations

import os
import sys
from typing import Any, Optional

import yaml

POC_ROOT = os.path.dirname(os.path.abspath(__file__))


def list_pocs() -> list[str]:
    """返回包含 manifest.yaml 的同级子目录名（即已定义的行业 POC）。"""
    out = []
    for name in sorted(os.listdir(POC_ROOT)):
        d = os.path.join(POC_ROOT, name)
        if os.path.isdir(d) and os.path.isfile(os.path.join(d, "manifest.yaml")):
            out.append(name)
    return out


def load_manifest(poc: str) -> tuple[dict, str]:
    """加载某 POC 的 manifest.yaml，返回 (dict, manifest_abs_path)。"""
    path = os.path.join(POC_ROOT, poc, "manifest.yaml")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"POC '{poc}' 缺少 manifest.yaml：{path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} 顶层应为 mapping")
    return data, path


def resolve(poc: str, rel: str) -> str:
    """把 manifest 中的相对路径解析为绝对路径。"""
    return os.path.normpath(os.path.join(POC_ROOT, poc, rel))


def _iter_seed_docs(seed_dir_abs: str) -> list[str]:
    docs = []
    if os.path.isdir(seed_dir_abs):
        for fn in sorted(os.listdir(seed_dir_abs)):
            if fn.lower().endswith((".md", ".txt", ".pdf")):
                docs.append(os.path.join(seed_dir_abs, fn))
    return docs


def build_plan(manifest: dict, poc: str) -> list[dict[str, Any]]:
    """依据 manifest.resources 构建发布计划（一串 API 步骤）。

    每步：{kind, endpoint, method, payload, note}。dry-run 时直接打印；
    apply 时由 provision.py 顺序执行（并维护 logical_id -> real_id 映射）。
    """
    res = manifest.get("resources") or {}
    steps: list[dict[str, Any]] = []

    # 1) 知识库 + 种子文档
    for kb in res.get("knowledge_bases", []):
        kb_id = kb["id"]
        seed_abs = resolve(poc, kb["seed_dir"])
        steps.append({
            "kind": "knowledge_base",
            "logical_id": kb_id,
            "endpoint": "/api/kb/kb",
            "method": "POST",
            "payload": {"name": kb["name"]},
            "note": f"创建知识库「{kb['name']}」（逻辑 id={kb_id}）",
        })
        for doc in _iter_seed_docs(seed_abs):
            steps.append({
                "kind": "kb_document",
                "logical_id": kb_id,
                "endpoint": f"/api/kb/kb/{{{kb_id}}}/ingest",
                "method": "POST",
                "_file_path": doc,  # 真实文件绝对路径，apply 时按 multipart 上传
                "file_field": "file",
                "payload": {},
                "note": f"灌入种子文档 {os.path.basename(doc)} → 知识库 {kb_id}",
            })

    # 2) 技能（文件式，SKILL.md 目录）
    for sk in res.get("skills", []):
        sk_path = resolve(poc, sk["path"])
        steps.append({
            "kind": "skill",
            "logical_id": sk["id"],
            "endpoint": "/api/skills/skills",
            "method": "POST",
            "payload": {
                "slug": sk["slug"],
                "name": sk.get("name", sk["slug"]),
                "storage_path": sk_path,
                "is_public": sk.get("is_public", True),
            },
            "note": f"注册技能「{sk['slug']}」（逻辑 id={sk['id']}，路径 {sk['path']}）",
        })

    # 3) MCP 连接器
    for mc in res.get("mcp_servers", []):
        spec_abs = resolve(poc, mc["spec"])
        with open(spec_abs, "r", encoding="utf-8") as f:
            spec = yaml.safe_load(f)
        steps.append({
            "kind": "mcp_server",
            "logical_id": mc["id"],
            "endpoint": "/api/mcp/servers",
            "method": "POST",
            "payload": {
                "name": spec["name"],
                "transport": spec.get("transport", "sse"),
                "endpoint": spec.get("endpoint"),
                "secret_ref": spec.get("secret_ref"),
            },
            "note": f"注册 MCP 连接器「{spec.get('name')}」（逻辑 id={mc['id']}）",
        })
        steps.append({
            "kind": "mcp_sync",
            "logical_id": mc["id"],
            "endpoint": f"/api/mcp/servers/{{{mc['id']}}}/sync",
            "method": "POST",
            "payload": {},
            "note": f"同步 {spec.get('name')} 工具清单（{len(spec.get('tools', []))} 个工具）",
        })

    # 4) 智能体剧本
    for ag in res.get("agents", []):
        pb_abs = resolve(poc, ag["playbook"])
        with open(pb_abs, "r", encoding="utf-8") as f:
            pb = yaml.safe_load(f)
        agent = pb.get("agent", {})
        steps.append({
            "kind": "agent_playbook",
            "logical_id": ag["id"],
            "endpoint": "/api/agent/playbooks",
            "method": "POST",
            "payload": {
                "name": agent.get("name"),
                "model": agent.get("model"),
                "system_prompt": agent.get("system_prompt"),
                "defaults": agent.get("defaults", {}),
                "scenario_flow": agent.get("scenario_flow", []),
            },
            "note": f"注册智能体剧本「{agent.get('name')}」（逻辑 id={ag['id']}）",
        })

    return steps


def validate_poc(poc: str) -> tuple[list[str], list[str], list[dict]]:
    """校验单个 POC：schema 基本字段 + 资源引用完整性。

    返回 (errors, warnings, plan)。errors 非空则该 POC 不合法。
    """
    errors: list[str] = []
    warnings: list[str] = []

    try:
        manifest, mpath = load_manifest(poc)
    except Exception as e:  # noqa: BLE001
        return [f"manifest 加载失败：{e}"], warnings, []

    # --- ① 市场包元数据必填 ---
    for fld in ("slug", "name", "package_type", "publisher"):
        if not manifest.get(fld):
            errors.append(f"manifest 缺少必填市场字段：{fld}")
    if manifest.get("package_type") not in ("skill", "connector", "expert"):
        errors.append(f"package_type 非法：{manifest.get('package_type')!r}（应为 skill/connector/expert）")

    # --- ② scenario 段 ---
    sc = manifest.get("scenario")
    if not isinstance(sc, dict):
        errors.append("manifest.scenario 缺失或非 mapping")
    else:
        if not sc.get("target_customer"):
            errors.append("scenario.target_customer 缺失")
        if not sc.get("killer_scenario"):
            errors.append("scenario.killer_scenario 缺失")
        if not isinstance(sc.get("success_metrics"), list) or not sc.get("success_metrics"):
            errors.append("scenario.success_metrics 应为非空列表")
        else:
            for i, m in enumerate(sc["success_metrics"]):
                for k in ("id", "name", "baseline", "target"):
                    if not m.get(k):
                        errors.append(f"success_metrics[{i}] 缺少 {k}")

    # --- ③ 资源清单 + 引用完整性 ---
    res = manifest.get("resources")
    if not isinstance(res, dict):
        errors.append("manifest.resources 缺失或非 mapping")
        return errors, warnings, []

    res_index: dict[str, set] = {
        "kb": {kb["id"] for kb in res.get("knowledge_bases", [])},
        "skill": {sk["id"] for sk in res.get("skills", [])},
        "mcp": {mc["id"] for mc in res.get("mcp_servers", [])},
        "agent": {ag["id"] for ag in res.get("agents", [])},
    }

    # 知识库 seed_dir 存在且有文档
    for kb in res.get("knowledge_bases", []):
        if "id" not in kb or "seed_dir" not in kb:
            errors.append("knowledge_bases 项须含 id 与 seed_dir")
            continue
        seed_abs = resolve(poc, kb["seed_dir"])
        if not os.path.isdir(seed_abs):
            errors.append(f"知识库种子目录不存在：{kb['seed_dir']}（{seed_abs}）")
        elif not _iter_seed_docs(seed_abs):
            warnings.append(f"知识库 {kb['id']} 种子目录无文档：{kb['seed_dir']}")

    # 技能目录 + SKILL.md
    for sk in res.get("skills", []):
        if "id" not in sk or "path" not in sk:
            errors.append("skills 项须含 id 与 path")
            continue
        sk_abs = resolve(poc, sk["path"])
        if not os.path.isdir(sk_abs):
            errors.append(f"技能目录不存在：{sk['path']}")
        elif not os.path.isfile(os.path.join(sk_abs, "SKILL.md")):
            errors.append(f"技能目录缺少 SKILL.md：{sk['path']}")

    # MCP spec 文件存在 + tools 覆盖剧本引用
    mcp_tool_names: dict[str, set] = {}
    for mc in res.get("mcp_servers", []):
        if "id" not in mc or "spec" not in mc:
            errors.append("mcp_servers 项须含 id 与 spec")
            continue
        spec_abs = resolve(poc, mc["spec"])
        if not os.path.isfile(spec_abs):
            errors.append(f"MCP 规格文件不存在：{mc['spec']}")
            continue
        try:
            with open(spec_abs, "r", encoding="utf-8") as f:
                spec = yaml.safe_load(f)
            mcp_tool_names[mc["id"]] = {t["name"] for t in spec.get("tools", [])}
        except Exception as e:  # noqa: BLE001
            errors.append(f"MCP 规格解析失败 {mc['spec']}：{e}")

    # 智能体剧本存在 + defaults 引用合法
    for ag in res.get("agents", []):
        if "id" not in ag or "playbook" not in ag:
            errors.append("agents 项须含 id 与 playbook")
            continue
        pb_abs = resolve(poc, ag["playbook"])
        if not os.path.isfile(pb_abs):
            errors.append(f"智能体剧本不存在：{ag['playbook']}")
            continue
        try:
            with open(pb_abs, "r", encoding="utf-8") as f:
                pb = yaml.safe_load(f)
            agent = pb.get("agent", {})
            defaults = agent.get("defaults", {})
            if defaults.get("kb_id") and defaults["kb_id"] not in res_index["kb"]:
                errors.append(f"剧本 {ag['id']} 的 defaults.kb_id={defaults['kb_id']} 不在 knowledge_bases")
            if defaults.get("skill_id") and defaults["skill_id"] not in res_index["skill"]:
                errors.append(f"剧本 {ag['id']} 的 defaults.skill_id={defaults['skill_id']} 不在 skills")
            if defaults.get("mcp_server_id"):
                mid = defaults["mcp_server_id"]
                if mid not in res_index["mcp"]:
                    errors.append(f"剧本 {ag['id']} 的 defaults.mcp_server_id={mid} 不在 mcp_servers")
                elif defaults.get("mcp_tool") and defaults["mcp_tool"] not in mcp_tool_names.get(mid, set()):
                    errors.append(
                        f"剧本 {ag['id']} 的 mcp_tool={defaults['mcp_tool']} 不在连接器 {mid} 的 tools 清单"
                    )
        except Exception as e:  # noqa: BLE001
            errors.append(f"剧本解析失败 {ag['playbook']}：{e}")

    plan = build_plan(manifest, poc) if not errors else []
    return errors, warnings, plan


if __name__ == "__main__":
    # 直接运行：打印所有 POC 的校验结果
    sys.exit(0 if all(not validate_poc(p)[0] for p in list_pocs()) else 1)
