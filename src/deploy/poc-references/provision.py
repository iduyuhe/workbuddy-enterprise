"""把指定标杆 POC 骨架铺进某个客户租户。

三种模式：
  --dry-run  （默认）仅打印「将产生哪些 API 调用」，不真正请求，用于评审/演练。
  --apply              经网关真实调用平台 API，把技能/知识库/MCP/智能体剧本创建到租户内。
  --rollback           按 --state-file 中记录的 logical_id→real_id 映射，反向删除已铺资源。

认证（apply / rollback 需要）：
  --gateway-url  网关地址（默认 http://localhost:8000）
  --token        平台 JWT（Authorization: Bearer）
  --tenant-id    目标租户（X-Tenant-Id / X-Project-Id）
  --state-file   资源映射落盘路径（apply 后写出，rollback 时读取，默认 .provision_state.json）

注意：
  - apply 模式下 logical_id -> 真实 id 的映射在运行时建立（如创建 KB 后拿回 kb_id 再灌文档）。
  - 剧本 defaults 内的嵌套 logical_id（kb_id/skill_id/mcp_server_id）在 apply 时递归替换为真实 id。
  - 所有端点与载荷对齐平台真实契约（knowledge-service / skills-registry / mcp-connector / agent-service）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import yaml

try:
    import httpx
except ImportError:  # 干跑模式下不强依赖 httpx
    httpx = None

from common import build_plan, list_pocs, load_manifest, validate_poc

# logical_id -> (真实 id, 资源类型) 映射，用于回滚时反向删除
STATE_VERSION = 1

# 各资源类型的删除端点模板（{id} 由真实 id 替换）
DELETE_ENDPOINTS = {
    "agent_playbook": "/api/agent/playbooks/{id}",
    "mcp_server": "/api/mcp/servers/{id}",
    "skill": "/api/skills/skills/{id}",
    "knowledge_base": "/api/kb/kb/{id}",
}


def _print_plan(poc: str, plan: list[dict]) -> None:
    print(f"== 发布计划：[{poc}] 共 {len(plan)} 步 ==\n")
    for i, s in enumerate(plan, 1):
        print(f"{i:2}. {s['method']:4} {s['endpoint']}")
        print(f"     {s['note']}")
        if s.get("_file_path"):
            print(f"     file: {os.path.basename(s['_file_path'])} (multipart)")
        else:
            print(f"     payload: {s['payload']}")
    print()


def _substitute(obj, id_map: dict[str, str]):
    """递归把字符串值中命中的 logical_id 替换为真实 id（不影响工具名等非 id 字符串）。"""
    if isinstance(obj, dict):
        return {k: _substitute(v, id_map) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_substitute(v, id_map) for v in obj]
    if isinstance(obj, str) and obj in id_map:
        return id_map[obj]
    return obj


def _apply(poc: str, plan: list[dict], gateway: str, token: str, tenant: str, state_file: str) -> int:
    if httpx is None:
        print("apply 模式需要 httpx：pip install httpx")
        return 2
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": tenant,
        "X-Project-Id": tenant,  # skills/mcp 以 project_id 作隔离键， pilot 中与租户取同一值
    }
    id_map: dict[str, str] = {}
    base = gateway.rstrip("/")
    ok, fail = 0, 0

    print(f"== 真实铺包：[{poc}] → {base} (tenant={tenant}) ==\n")
    for s in plan:
        url = base + s["endpoint"]
        # 把端点模板里的 {logical_id} 替换为真实 id
        for lid, rid in id_map.items():
            url = url.replace("{" + lid + "}", rid)

        # 文档上传走 multipart；其余走 JSON
        files = None
        data = None
        json_body = None
        if s.get("_file_path"):
            fp = s["_file_path"]
            field = s.get("file_field", "file")
            files = {field: (os.path.basename(fp), open(fp, "rb"))}
        else:
            payload = dict(s["payload"])
            # 注入租户/项目隔离键（KB/skill/mcp/playbook 各自字段名不同）
            if s["kind"] == "knowledge_base":
                payload["tenant_id"] = tenant
            elif s["kind"] == "skill":
                payload["project_id"] = tenant
            elif s["kind"] == "mcp_server":
                payload["project_id"] = tenant
            elif s["kind"] == "agent_playbook":
                payload["tenant_id"] = tenant
                payload["project_id"] = tenant
            # 嵌套 logical_id 递归替换（剧本 defaults 等）
            payload = _substitute(payload, id_map)
            json_body = payload

        try:
            r = httpx.request(
                s["method"], url, json=json_body, data=data, files=files,
                headers=headers, timeout=60,
            )
            if r.status_code < 300:
                ok += 1
                print(f"OK   {s['method']:4} {url} → {r.status_code}")
                try:
                    body = r.json()
                    real_id = body.get("id") or body.get("kb_id") or body.get("server_id")
                    if real_id and s.get("logical_id"):
                        id_map[s["logical_id"]] = str(real_id)
                except Exception:  # noqa: BLE001
                    pass
            else:
                fail += 1
                print(f"FAIL {s['method']:4} {url} → {r.status_code} {r.text[:200]}")
        except Exception as e:  # noqa: BLE001
            fail += 1
            print(f"ERR  {s['method']:4} {url} → {e}")
        finally:
            if files:
                for f in files.values():
                    f[1].close()

    # 落盘映射，供 rollback 使用（保留 kind 以便反向删除）
    resources = [
        {"kind": s["kind"], "logical_id": lid, "real_id": rid}
        for lid, rid in id_map.items()
        if lid in {s.get("logical_id") for s in plan}
    ]
    id_map_out = {r["logical_id"]: r["real_id"] for r in resources}
    state = {
        "version": STATE_VERSION,
        "poc": poc,
        "tenant": tenant,
        "gateway": base,
        "id_map": id_map_out,
        "resources": resources,
    }
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"\n== 结果：成功 {ok} / 失败 {fail}；映射已写入 {state_file} ==")
    return 0 if fail == 0 else 1


def _rollback(state_file: str, gateway: str, token: str, tenant: str, dry_run: bool) -> int:
    if not os.path.isfile(state_file):
        print(f"❌ 找不到状态文件 {state_file}，无法回滚（请先 --apply 生成）")
        return 2
    with open(state_file, "r", encoding="utf-8") as f:
        state = json.load(f)
    resources: list[dict] = state.get("resources", [])
    base = (gateway or state.get("gateway", "http://localhost:8000")).rstrip("/")
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Id": tenant or state.get("tenant", "")}

    # 反向顺序删除（剧本→MCP→技能→知识库）
    order = ["agent_playbook", "mcp_server", "skill", "knowledge_base"]
    steps = [(r["kind"], r["real_id"]) for r in resources if r.get("kind") in DELETE_ENDPOINTS]
    # 按 order 排序
    steps.sort(key=lambda kv: order.index(kv[0]) if kv[0] in order else 99)

    if not steps:
        print("状态文件中无可回滚资源。")
        return 0

    print(f"== 回滚：{base} (tenant={tenant or state.get('tenant')}) dry_run={dry_run} ==\n")
    ok, fail = 0, 0
    for kind, rid in steps:
        url = base + DELETE_ENDPOINTS[kind].format(id=rid)
        if dry_run:
            print(f"[dry] DELETE {url}")
            ok += 1
            continue
        try:
            r = httpx.request("DELETE", url, headers=headers, timeout=30)
            if r.status_code < 300:
                ok += 1
                print(f"OK   DELETE {url} → {r.status_code}")
            else:
                fail += 1
                print(f"FAIL DELETE {url} → {r.status_code} {r.text[:160]}")
        except Exception as e:  # noqa: BLE001
            fail += 1
            print(f"ERR  DELETE {url} → {e}")
    print(f"\n== 回滚结果：成功 {ok} / 失败 {fail} ==")
    return 0 if fail == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="把标杆 POC 骨架铺进租户 / 回滚")
    ap.add_argument("--poc", required=True, choices=list_pocs(), help="要发布的 POC 名称")
    ap.add_argument("--dry-run", action="store_true", help="仅打印计划（默认，除非 --apply/--rollback）")
    ap.add_argument("--apply", action="store_true", help="经网关真实调用 API 铺包")
    ap.add_argument("--rollback", action="store_true", help="按 --state-file 反向删除已铺资源")
    ap.add_argument("--gateway-url", default="http://localhost:8000")
    ap.add_argument("--token", default="")
    ap.add_argument("--tenant-id", default="")
    ap.add_argument("--state-file", default=".provision_state.json")
    args = ap.parse_args()

    # rollback 模式
    if args.rollback:
        if not args.token:
            print("❌ --rollback 需要 --token（tenant 可选，缺省用状态文件记录值）")
            return 2
        return _rollback(args.state_file, args.gateway_url, args.token, args.tenant_id, args.dry_run)

    errors, warnings, plan = validate_poc(args.poc)
    if errors:
        print(f"❌ POC '{args.poc}' 校验未通过，拒绝发布：")
        for e in errors:
            print(f"   - {e}")
        return 1
    for w in warnings:
        print(f"   - warn: {w}")

    if not args.apply:
        _print_plan(args.poc, plan)
        return 0

    # apply 模式
    if not args.token or not args.tenant_id:
        print("❌ --apply 需要 --token 与 --tenant-id")
        return 2
    manifest, _ = load_manifest(args.poc)
    sc = manifest.get("scenario", {})
    print(f"Killer Scenario 目标客户：{sc.get('target_customer')}\n")
    return _apply(args.poc, plan, args.gateway_url, args.token, args.tenant_id, args.state_file)


if __name__ == "__main__":
    sys.exit(main())
