"""校验全部标杆 POC 骨架的合法性（无副作用，可在 CI 跑）。

校验内容：
  1. 每个 POC 的 manifest.yaml 可解析、必填字段齐全；
  2. scenario / success_metrics 结构合规；
  3. resources 引用完整性：技能目录含 SKILL.md、知识库种子目录存在且有文档、
     MCP spec 文件存在、智能体剧本存在且 defaults 引用落在 resources 内、
     mcp_tool 落在连接器 tools 清单内。

退出码：全部通过为 0；任一 POC 有 error 为 1。
"""
from __future__ import annotations

import sys

from common import list_pocs, validate_poc

PASS, FAIL = "✅", "❌"


def main() -> int:
    pocs = list_pocs()
    if not pocs:
        print("未发现任何 POC（应在各子目录放置 manifest.yaml）。")
        return 1

    total_err = 0
    print(f"== 标杆 POC 校验：共 {len(pocs)} 套 ==\n")
    for poc in pocs:
        errors, warnings, plan = validate_poc(poc)
        status = PASS if not errors else FAIL
        print(f"{status} [{poc}]  {len(errors)} error / {len(warnings)} warn / {len(plan)} 计划步骤")
        for e in errors:
            print(f"   - ERROR: {e}")
        for w in warnings:
            print(f"   - warn:  {w}")
        if not errors:
            for s in plan:
                print(f"   · {s['method']:4} {s['endpoint']:42} {s['note']}")
        print()
        total_err += len(errors)

    print(f"== 结论：{total_err == 0 and '全部通过 ✅' or f'{total_err} 个错误 ❌'} ==")
    return 0 if total_err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
