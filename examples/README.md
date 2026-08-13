# 示例库 (Examples)

本目录是 WorkBuddy Enterprise 的**真实可跑示例**，每个示例都对齐平台契约，可直接复制修改后上架生态市场或铺进客户租户。

| 示例 | 路径 | 对齐契约 |
|---|---|---|
| 最小技能 | [`hello-skill/`](./hello-skill) | `skills-registry` 的 `skill_parser.parse_skill_md` |
| 最小市场包 | [`marketplace-package/`](./marketplace-package) | `marketplace-service` 的 `PackageCreate` |
| 智能体剧本 | [`agent-playbook/`](./agent-playbook) | `agent-service` 运行时（ReAct 三件套） |

文档站对应说明页见 [`docs/community/examples.md`](https://github.com/iduyuhe/workbuddy-enterprise/blob/main/docs/community/examples.md)。

## 校验

所有示例由仓库根 [`docs/verify_site.py`](https://github.com/iduyuhe/workbuddy-enterprise/blob/main/docs/verify_site.py) 统一校验：

```bash
python docs/verify_site.py
```

该脚本会检查：

- `mkdocs.yml` 语法合法，且 `nav` 引用的文档页全部存在；
- 每个 `SKILL.md` 的 YAML frontmatter 含 `name` / `description`；
- `marketplace-package/manifest.yaml` 必填字段齐全（`slug` / `name` / `package_type` / `publisher` / `version` / `resources`）；
- `agent-playbook` 的 `manifest.resources` 与 `playbook.yaml` 的 `defaults` 引用一致，且 `call_mcp_tool` 的 `tool` 落在对应 MCP 连接器 `tools` 清单内。

## 如何新增示例

1. 在 `examples/<your-example>/` 下放置文件，保证契约字段与对应服务一致。
2. 提供 `README.md`：解决什么场景、如何运行 / 上架、依赖哪些服务。
3. 在本文档表格追加一行，并在 `mkdocs.yml` 的 `示例库` 分区加导航。
4. 跑 `python docs/verify_site.py` 确认通过。

> 原则：**示例即文档**。每个示例都应能让人照抄跑通。
