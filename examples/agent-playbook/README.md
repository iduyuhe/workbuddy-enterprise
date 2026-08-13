# Hello 助手剧本 (agent-playbook)

最小智能体剧本，演示 `agent-service` 如何把「知识库 + 技能 + MCP 工具」编排进一个 Killer Scenario。

## 结构

```
agent-playbook/
├── manifest.yaml              # 包元数据（package_type: expert）
├── agent/
│   └── playbook.yaml          # 剧本：默认值接线 + 场景流程
├── mcp/
│   └── crm.yaml               # MCP 连接器规格（被 manifest 引用）
└── README.md
```

## 编排三件套

`agent/playbook.yaml` 的 `scenario_flow` 使用运行时三件套：

| action | 含义 |
|---|---|
| `use_skill` | 调用 `target` 指定的技能（落在 `manifest.resources.skills`） |
| `search_kb` | 检索 `target` 指定的知识库（落在 `manifest.resources.knowledge_bases`） |
| `call_mcp_tool` | 调用 `target` 指定 MCP 服务器的 `tool`（须落在该连接器 `tools` 清单内） |

## 引用完整性（强制）

`validate_poc.py` / `verify_site.py` 会校验：

- `playbook.defaults` 的 `kb_id / skill_id / mcp_server_id` 必须全部落在 `manifest.resources` 内；
- `call_mcp_tool` 的 `tool`（如 `get_customer`）必须落在对应 MCP 连接器 `tools` 清单内。

## 运行

```bash
python docs/verify_site.py                       # 校验引用完整性
python src/deploy/poc-references/provision.py \
  --poc examples/agent-playbook --dry-run        # 预览 API 调用计划
```
