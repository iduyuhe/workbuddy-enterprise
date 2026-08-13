# 示例：agent-playbook 智能体剧本

路径：[`examples/agent-playbook/`](https://github.com/iduyuhe/workbuddy-enterprise/tree/main/examples/agent-playbook)

一个**最小智能体剧本**，演示 `agent-service` 的 ReAct 运行时如何把「知识库 + 技能 + MCP 工具」编排进一个 Killer Scenario。

## 文件结构

```
examples/agent-playbook/
├── manifest.yaml              # 包元数据（package_type: expert）
├── agent/
│   └── playbook.yaml          # 剧本：默认值接线 + 场景流程
└── README.md
```

## manifest.yaml 要点

```yaml
slug: hello-agent
name: Hello 助手剧本
package_type: expert
publisher: workbuddy-ent-dev
version: 1.0.0
summary: 最小智能体剧本示例。
resources:
  knowledge_bases:
    - logical_id: kb_faq
      name: 企业 FAQ
  skills:
    - logical_id: skill_hello
      slug: hello
      storage_path: ../hello-skill
  mcp_servers:
    - logical_id: mcp_crm
      spec: mcp/crm.yaml
  agents:
    - logical_id: agent_hello
      playbook: agent/playbook.yaml
```

## agent/playbook.yaml 要点

```yaml
agent:
  name: Hello 助手
  description: 用企业 FAQ + 打招呼技能 + CRM 工具回答用户。
  defaults:
    kb_id: kb_faq
    skill_id: skill_hello
    mcp_server_id: mcp_crm
  scenario_flow:
    - step: 1
      intent: 寒暄
      action: use_skill
      target: skill_hello
    - step: 2
      intent: 查客户信息
      action: call_mcp_tool
      target: mcp_crm
      tool: get_customer
    - step: 3
      intent: 答 FAQ
      action: search_kb
      target: kb_faq
```

## 对齐的契约

- 运行时三件套：`search_kb` / `use_skill` / `call_mcp_tool`。
- `defaults` 中的 `kb_id / skill_id / mcp_server_id` 必须落在 `manifest.resources` 内；`call_mcp_tool` 的 `tool` 必须落在对应 MCP 连接器 `tools` 清单内（由 `validate_poc.py` 强校验）。
- `provision.py` 会按 `logical_id → real_id` 映射顺序创建 KB / 技能 / MCP / 剧本。

## 如何运行

```bash
python docs/verify_site.py                       # 校验引用完整性
python src/deploy/poc-references/provision.py \
  --poc examples/agent-playbook --dry-run        # 预览 API 调用计划
```
