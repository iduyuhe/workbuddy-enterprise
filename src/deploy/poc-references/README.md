# 标杆 POC 参考骨架（Killer Scenario Reference）

WorkBuddy Enterprise 在 **阶段 4 · 规模交付与生态** 中，需要把平台能力沉淀为**行业标杆 POC（Proof of Concept）**——
用一套可直接部署到客户租户的「行业解决方案包」，向样板客户证明平台价值，并固化该行业的 **Killer Scenario（杀手级场景）**。

本目录提供两个开箱即用的参考骨架：

| 行业 | 目录 | Killer Scenario 主题 | 包类型 |
|---|---|---|---|
| 制造业 | [`manufacturing/`](./manufacturing) | 离散制造·智能质检（缺陷归因 + 设备预测性维护 + 工艺参数优化） | `expert` |
| 金融业 | [`finance/`](./finance) | 金融机构·智能合规（研报摘要 + 合规条款比对 + 监管报送核对） | `expert` |

> 每个骨架都是**完整、自洽、可直接对接平台**的：包含市场包清单、技能目录、知识库种子、MCP 连接器、智能体剧本、验收标准。
> 用 `provision.py` 即可把骨架「铺」进某个客户租户；用 `validate_poc.py` 在做任何操作前校验骨架合法性。

---

## 目录约定

```
poc-references/
├── README.md                 # 本文件
├── SCHEMA.md                 # manifest / skill / mcp / agent 剧本 schema 权威规范
├── common.py                 # 加载 / 校验 / 发布共享逻辑（供 validate / provision 复用）
├── validate_poc.py           # 校验全部 POC：YAML 解析 + 引用完整性
├── provision.py              # 把指定 POC 铺进租户（--dry-run 仅打印；--apply 真实调用；--rollback 回滚）
├── PILOT_DELIVERY.md         # 试点客户交付手册（环境前置 / 一键铺包 / 验收 / 回滚 / 排错）
├── manufacturing/            # 制造业骨架
│   ├── manifest.yaml         # 市场包 + scenario + resources（provision 的输入）
│   ├── README.md             # 行业 POC 说明（给售前/交付看）
│   ├── acceptance.md         # 验收标准 + 成功度量（给客户/评估方看）
│   ├── skills/<slug>/SKILL.md# Anthropic 风格文件式技能（frontmatter + 步骤体）
│   ├── knowledge/seed/*.md   # 知识库种子文档（首次铺包时灌入 KB）
│   ├── mcp/<conn>.yaml       # MCP 连接器规格（name/transport/endpoint/tools）
│   └── agent/playbook.yaml   # 智能体剧本：system 提示 + 默认资源接线 + 场景流
└── finance/                  # 金融业骨架（同构）
```

---

## 三个核心概念

1. **Killer Scenario（杀手级场景）**：该行业客户「用了就回不去」的端到端场景。写在 `manifest.yaml` 的 `scenario` 段，并在 `agent/playbook.yaml` 的 `scenario_flow` 拆为可执行的工具调用步骤。
2. **Resources（资源清单）**：骨架落地到租户时创建的四类资源——`knowledge_bases` / `skills` / `mcp_servers` / `agents`，由 `manifest.yaml` 的 `resources` 段声明，`provision.py` 依此调用平台 API。
3. **Acceptance（验收）**：把 Killer Scenario 翻译成**可度量**的成功指标（baseline → target），写在 `acceptance.md`，作为 POC 验收的「合同」。

---

## 快速开始

```bash
# 1) 校验两套骨架是否合法（无副作用，CI 可跑）
python src/deploy/poc-references/validate_poc.py

# 2) 干跑：打印「把制造业 POC 铺进租户」会产生哪些 API 调用（不真正请求）
python src/deploy/poc-references/provision.py --poc manufacturing --dry-run

# 3) 真实铺包（需可达的网关 + 租户凭证；见 SCHEMA.md 的认证说明）
python src/deploy/poc-references/provision.py --poc manufacturing \
    --gateway-url http://localhost:8000 \
    --token $WB_TOKEN --tenant-id $WB_TENANT

# 4) 撤场/重铺：凭铺包生成的 .state.json 反向删除（详见 PILOT_DELIVERY.md）
python src/deploy/poc-references/provision.py --poc manufacturing --rollback \
    --state-file manufacturing.state.json --token $WB_TOKEN --tenant-id $WB_TENANT
```

> **交付工程师请看 [`PILOT_DELIVERY.md`](./PILOT_DELIVERY.md)**：环境前置清单、一键铺包命令、验收步骤（对接 `acceptance.md` 的 success_metrics）、回滚流程与常见排错。

---

## 与生态市场的关系

骨架本身是 `package_type: expert` 的市场包。完成 POC 验证后，可把 `manifest.yaml` 直接 `POST /api/marketplace/packages` 发布到生态市场，
供其他同行业租户「一键获取」（见 `阶段 4 ② 生态市场` 的 marketplace-service）。换言之：**标杆 POC = 生态市场里最优质的 expert 包的来源**。
