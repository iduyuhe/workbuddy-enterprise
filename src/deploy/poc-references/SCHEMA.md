# 标杆 POC 包 Schema 规范

本文件是 `poc-references/` 下所有骨架的**权威 schema**。任何新增行业骨架都应按此规范编写，
`validate_poc.py` 会据此做静态校验，`provision.py` 会据此调用平台 API。

---

## 1. `manifest.yaml`（包根清单）

顶层字段分为三块：**市场包元数据**（对齐 `marketplace-service` 的 `PackageCreate`）、
**scenario**（Killer Scenario 定义）、**resources**（落地资源清单）。

```yaml
# ---- ① 市场包元数据（PackageCreate 兼容）----
slug: wb-poc-manufacturing-qc        # 全局唯一，建议 wb-poc-<行业>-<主题>
name: 制造业·智能质检标杆 POC
package_type: expert                 # 行业解决方案 = expert；单技能可选 skill
publisher: 工业5点0产业生态联盟
summary: 一句话价值主张（≤280 字）
description: |
  长描述，讲清解决什么、给谁、带来什么。
license: CC-BY-NC-4.0
price_model: free                    # free | paid | subscription
tags: [制造业, 质检, 设备运维]          # 市场筛选用
categories: [标杆POC, 制造业]
homepage: https://github.com/iduyuhe/zhiyan-evolviq
repository: https://github.com/iduyuhe/zhiyan-evolviq
supported_platforms: [k8s, docker-compose]
version: 0.1.0

# ---- ② Killer Scenario 定义 ----
scenario:
  target_customer: 离散制造中型工厂（质检 + 设备部门）
  pain_points:                       # 客户痛点（3-5 条）
    - 缺陷归因靠老师傅经验，MTTR 长
    - 设备突发停机造成停线损失
  killer_scenario: |                 # 端到端杀手级场景描述
    质检员拍照/录入缺陷 → 系统在知识库检索相似案例 →
    调用归因技能生成根因假设 → 回查 MES 历史数据印证 →
    输出归因报告 + 整改建议，并沉淀为新案例。
  success_metrics:                   # 可度量成功指标
    - id: defect-mttr
      name: 缺陷归因平均耗时(MTTR)
      baseline: "4 小时/次"
      target: "≤15 分钟/次"
      measure: 系统时间戳

# ---- ③ 资源清单（provision.py 据此在租户内创建）----
resources:
  knowledge_bases:
    - id: qc-kb                      # 逻辑 id（playbook.defaults.kb_id 引用）
      name: 质检知识库
      seed_dir: knowledge/seed       # 相对 manifest 的路径，首次铺包灌入
  skills:
    - id: qc-defect-attribution      # 逻辑 id（playbook.defaults.skill_id 引用）
      slug: qc-defect-attribution
      path: skills/qc-defect-attribution   # 含 SKILL.md 的目录
  mcp_servers:
    - id: mes-connector              # 逻辑 id（playbook.defaults.mcp_server_id 引用）
      name: MES 连接器
      spec: mcp/mes-connector.yaml   # 见 §3
  agents:
    - id: qc-agent                   # 逻辑 id
      name: 智能质检助手
      playbook: agent/playbook.yaml  # 见 §4
```

**引用完整性（validate_poc.py 强校验）**：
- 每个 `playbook.defaults.{kb_id,skill_id,mcp_server_id}` 必须出现在 `resources` 对应清单里。
- `seed_dir` / `path` / `spec` / `playbook` 指向的文件必须**存在**。
- `mcp_servers[].spec` 里声明的 `tools[].name` 必须覆盖 playbook 中引用的 `mcp_tool`。

---

## 2. `skills/<slug>/SKILL.md`（Anthropic 风格文件式技能）

与 `skills-registry` 的 `skill_parser.parse_skill_md` 完全兼容：头部 YAML frontmatter 至少含 `name` / `description`，其后为步骤体。

```markdown
---
name: 质检缺陷归因
description: 根据缺陷现象，在知识库检索相似案例并生成根因假设与整改建议。
---
# 适用场景
质检员上报缺陷（现象/图片/产线/批次）。

# 执行步骤
1. 解析输入：提取缺陷代码、产线、批次。
2. 检索：search_kb 在质检知识库找相似历史缺陷。
3. 归因：比对缺陷代码库与工艺标准，生成 Top-3 根因假设。
4. 印证：call_mcp_tool 回查 MES 该批次的工艺参数与设备状态。
5. 输出：归因报告（根因 + 置信度 + 整改建议），并建议沉淀为新案例。

# 注意事项
- 仅给建议，不自动下发工艺变更指令。
- 涉及安全件需人工确认。
```

`provision.py` 调用 `POST /api/skills`（`storage_path` = 解压后的技能目录路径）注册。

---

## 3. `mcp/<conn>.yaml`（MCP 连接器规格）

对齐 `mcp-connector` 的 `POST /api/mcp/servers` 与 `POST /api/mcp/servers/{id}/sync`。

```yaml
name: MES 连接器
transport: sse                       # sse | stdio | streamable-http
endpoint: http://mes-internal:9000/sse
secret_ref: vault://mes-readonly     # 走平台密钥保管，不落明文
tools:                               # 给实施方/评估方的工具清单（sync 时由服务端实际拉取）
  - name: query_defect_records
    description: 按时间段/产线/缺陷代码查询质检记录
    schema_json:
      type: object
      properties:
        line: { type: string }
        code: { type: string }
        from: { type: string, format: date-time }
        to: { type: string, format: date-time }
      required: [from, to]
  - name: query_equipment_telemetry
    description: 查询设备传感器时序数据
    schema_json: { type: object, properties: { equipment_id: { type: string } }, required: [equipment_id] }
```

`provision.py` 调用 `POST /api/mcp/servers` 注册，`POST /api/mcp/servers/{id}/sync` 拉取工具。

---

## 4. `agent/playbook.yaml`（智能体剧本）

对齐 `agent-service` 的 ReAct 运行时：`search_kb` / `use_skill` / `call_mcp_tool` 三件套 + 默认资源接线。

```yaml
agent:
  id: qc-agent
  name: 智能质检助手
  model: qwen3-235b                  # 或 deepseek-chat / claude-...
  system_prompt: |
    你是该工厂的智能质检助手。默认检索质检知识库、调用质检缺陷归因技能、
    必要时回查 MES 历史数据。输出须包含根因与可执行的整改建议。
  defaults:                          # 与 manifest.resources 的逻辑 id 对应
    kb_id: qc-kb
    skill_id: qc-defect-attribution
    mcp_server_id: mes-connector
    mcp_tool: query_defect_records
  scenario_flow:                     # Killer Scenario 的执行步骤（给评估方看，非运行时强约束）
    - step: 1
      intent: 接收质检员上报的缺陷现象
      tool: search_kb
      detail: 在 qc-kb 检索相似缺陷案例与标准
    - step: 2
      intent: 调用归因技能
      tool: use_skill
      detail: qc-defect-attribution 生成根因假设
    - step: 3
      intent: 回查 MES 历史数据印证
      tool: call_mcp_tool
      detail: mes-connector.query_defect_records
    - step: 4
      intent: 输出归因报告与整改建议
      tool: llm
```

`provision.py` 把 `defaults` 与 `system_prompt` 写入租户的 agent 配置（通过 `POST /api/v1/agent/config` 或等效配置接口），
使该租户的对话默认走此 Killer Scenario 接线。

---

## 5. 认证与多租户

`provision.py --apply` 通过网关调用，需携带：
- `--gateway-url`：网关地址（默认 `http://localhost:8000`）。
- `--token`：平台 JWT（`Authorization: Bearer`）。
- `--tenant-id`：目标租户（`X-Tenant-Id`）。

网关注入 `X-User-Id` / `X-Tenant-Id` 并做 RBAC；所有资源按 `tenant_id` 隔离（见阶段 3 多租户）。
