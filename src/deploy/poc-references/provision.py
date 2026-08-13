"""把指定标杆 POC 骨架铺进某个客户租户。

两种模式：
  --dry-run  （默认）仅打印「将产生哪些 API 调用」，不真正请求，用于评审/演练。
  --apply              经网关真实调用平台 API，把技能/知识库/MCP/智能体剧本创建到租户内。

认证（仅 --apply 需要）：
  --gateway-url  网关地址（默认 http://localhost:8000）
  --token        平台 JWT（Authorization: Bearer）
  --tenant-id    目标租户（X-Tenant-Id）

注意：apply 模式下 logical_id -> 真实 id 的映射在运行时建立（如创建 KB 后拿回 kb_id 再灌文档）。
本脚本聚焦「正确的调用顺序与载荷」，真实环境的端点/字段以平台 API_CONTRACT.md 为准。
"""
from __future__ import annotations

import argparse
import sys

import yaml

try:
    import httpx
except ImportError:  # 干跑模式下不强依赖 httpx
    httpx = None

from common import build_plan, list_pocs, load_manifest, validate_poc


def _print_plan(poc: str, plan: list[dict]) -> None:
    print(f"== 发布计划：[{poc}] 共 {len(plan)} 步 ==\n")
    for i, s in enumerate(plan, 1):
        print(f"{i:2}. {s['method']:4} {s['endpoint']}")
        print(f"     {s['note']}")
        print(f"     payload: {s['payload']}")
    print()


def _apply(poc: str, plan: list[dict], gateway: str, token: str, tenant: str) -> int:
    if httpx is None:
        print("apply 模式需要 httpx：pip install httpx")
        return 2
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Id": tenant}
    # logical_id -> 真实 id 映射（创建类步骤回填依赖）
    id_map: dict[str, str] = {}
    base = gateway.rstrip("/")
    ok, fail = 0, 0

    print(f"== 真实铺包：[{poc}] → {base} (tenant={tenant}) ==\n")
    for s in plan:
        url = base + s["endpoint"]
        # 把端点模板里的 {logical_id} 替换为真实 id
        for lid, rid in id_map.items():
            url = url.replace("{" + lid + "}", rid)

        payload = dict(s["payload"])
        # 用真实 id 替掉 logical 引用
        for k, v in list(payload.items()):
            if isinstance(v, str) and v in id_map:
                payload[k] = id_map[v]

        try:
            r = httpx.request(s["method"], url, json=payload, headers=headers, timeout=30)
            if r.status_code < 300:
                ok += 1
                print(f"OK   {s['method']:4} {url} → {r.status_code}")
                # 尝试捕获返回的真实 id
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

    print(f"\n== 结果：成功 {ok} / 失败 {fail} ==")
    return 0 if fail == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="把标杆 POC 骨架铺进租户")
    ap.add_argument("--poc", required=True, choices=list_pocs(), help="要发布的 POC 名称")
    ap.add_argument("--dry-run", action="store_true", help="仅打印计划（默认）")
    ap.add_argument("--apply", action="store_true", help="经网关真实调用 API")
    ap.add_argument("--gateway-url", default="http://localhost:8000")
    ap.add_argument("--token", default="")
    ap.add_argument("--tenant-id", default="")
    args = ap.parse_args()

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
    # 重新取 manifest 仅为打印场景摘要（optional）
    manifest, _ = load_manifest(args.poc)
    sc = manifest.get("scenario", {})
    print(f"Killer Scenario 目标客户：{sc.get('target_customer')}\n")
    return _apply(args.poc, plan, args.gateway_url, args.token, args.tenant_id)


if __name__ == "__main__":
    sys.exit(main())
