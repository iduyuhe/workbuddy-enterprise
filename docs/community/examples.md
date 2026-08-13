# 示例库

示例库位于仓库 [`examples/`](https://github.com/iduyuhe/workbuddy-enterprise/tree/main/examples)，每个示例都是**真实可跑、对齐平台契约**的最小样板，可直接复制修改后上架到生态市场或铺进客户租户。

## 示例清单

| 示例 | 路径 | 说明 | 对齐契约 |
|---|---|---|---|
| 最小技能 | [`examples/hello-skill/`](https://github.com/iduyuhe/workbuddy-enterprise/tree/main/examples/hello-skill) | 一个完整的 `SKILL.md`（Anthropic 风格 frontmatter + 步骤体） | `skills-registry` 的 `skill_parser.parse_skill_md` |
| 最小市场包 | [`examples/marketplace-package/`](https://github.com/iduyuhe/workbuddy-enterprise/tree/main/examples/marketplace-package) | `manifest.yaml` + 1 个技能，可直接 `POST /api/marketplace/packages` 上架 | `marketplace-service` 的 `PackageCreate` |
| 智能体剧本 | [`examples/agent-playbook/`](https://github.com/iduyuhe/workbuddy-enterprise/tree/main/examples/agent-playbook) | `manifest.yaml` + `agent/playbook.yaml`，编排 ReAct 三件套 | `agent-service` 运行时（`search_kb`/`use_skill`/`call_mcp_tool`） |

## 行业标杆 POC（扩展参考）

[`src/deploy/poc-references/`](https://github.com/iduyuhe/workbuddy-enterprise/tree/main/src/deploy/poc-references) 下有两套**可直接铺进客户租户**的行业解决方案包骨架，是示例库的「完整版」：

- **制造业** `manufacturing/` —— 离散制造智能质检（缺陷归因 / 预测性维护 / 工艺参数优化）+ MES 连接器。
- **金融业** `finance/` —— 持牌机构智能合规（研报摘要 / 合规条款比对 / 监管报送核对）+ 监管报送连接器。

每套均含 `manifest.yaml`、`skills/*/SKILL.md`、`knowledge/seed/`、`mcp/*.yaml`、`agent/playbook.yaml`、`acceptance.md`，并可用 `validate_poc.py` 校验、`provision.py --dry-run` 预览发布计划。

## 如何新增示例

1. 在 `examples/<your-example>/` 下放置文件，保证契约字段与对应服务一致。
2. 提供 `README.md` 说明：解决什么场景、如何运行 / 上架、依赖哪些服务。
3. 在本页表格追加一行，并在 `mkdocs.yml` 的 `示例库` 分区加一条导航。
4. 跑 `python docs/verify_site.py` 确认新增文件被校验脚本覆盖（YAML 合法、引用完整）。

> 原则：**示例即文档**。每个示例都应能让人照抄跑通，而不是只看不练。
