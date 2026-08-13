# 试点客户交付手册（Pilot Delivery Playbook）

> 适用对象：交付工程师 / 解决方案架构师 / 首批付费客户的驻场实施。
> 目标：把 `src/deploy/poc-references/` 下的「标杆 POC 骨架」一键铺进客户租户，跑通 Killer Scenario，并完成验收与回滚。
> 配套：`provision.py`（铺包/回滚）、`validate_poc.py`（骨架自检）、`SCHEMA.md`（骨架规范）。

---

## 0. 两套可用骨架

| 骨架 | Killer Scenario | 验收核心指标 |
|---|---|---|
| `manufacturing` | 离散制造智能质检（缺陷归因 + 预测性维护 + 工艺参数优化） | 缺陷归因 MTTR 4h→≤15min；FPY 92%→≥96%；非计划停机 12h→≤5h/月 |
| `finance` | 持牌机构智能合规（研报摘要 + 合规条款比对 + 监管报送核对） | 研报周期 3日→≤1日；条款比对覆盖 40%→100%；报送差错 0.8%→≤0.1% |

---

## 1. 环境前置

平台需已按 `src/deploy/` 部署并运行（K8s+Helm 或 docker-compose）。铺包前确认：

1. **网关可达**：`curl http://<GATEWAY>/health` 返回 200（默认 `http://localhost:8000`）。
2. **六个后端就绪**：knowledge / skills / mcp / agent / auth / gateway 均已注册到网关，且 `provision.py` 用到的路由可用：
   - `POST /api/kb/kb`、`POST /api/kb/kb/{id}/ingest`
   - `POST /api/skills/skills`
   - `POST /api/mcp/servers`、`POST /api/mcp/servers/{id}/sync`
   - `POST /api/agent/playbooks`（**本次新增端点**，需 agent-service 含迁移 `0004_playbook`）
3. **租户与凭据**：已为客户创建租户（取得 `tenant-id`），并已发放平台 JWT（`--token`）。
4. **向量库**：knowledge-service 后端 Qdrant/本地向量库可用（ingest 时惰性建集合）。
5. **RBAC**：调用账号需具备 `kb:write`、`skills:write`、`mcp:write`、`agent:write` 权限（对齐网关代理映射）。

> ⚠️ SQLite 仅用于本地开发；**生产部署必须用 PostgreSQL**，因为 `agent_runs.steps_json` 与 `agent_playbooks.defaults/scenario_flow` 在迁移中使用 JSONB。`alembic upgrade head` 在 SQLite 下会因 JSONB 无法渲染而失败——这是预期行为，不是缺陷。

---

## 2. 一键铺包（apply）

```bash
cd src/deploy/poc-references

# 1) 先自检骨架合法性（强校验，0 error 才允许 apply）
python validate_poc.py

# 2) 演练：打印将产生的 API 调用计划（不真正请求）
python provision.py --poc manufacturing --dry-run

# 3) 真实铺包：把 KB / 技能 / MCP / 剧本创建到客户租户
python provision.py --poc manufacturing --apply \
  --gateway-url http://<GATEWAY>:8000 \
  --token <CLIENT_JWT> \
  --tenant-id <CLIENT_TENANT_ID> \
  --state-file manufacturing.state.json
```

执行顺序（由 `build_plan` 保证，依赖自动解析）：
1. 创建知识库 → 灌入种子文档（multipart）
2. 注册技能（SKILL.md 文件式）
3. 注册 MCP 连接器 → 同步工具清单
4. 注册智能体剧本（剧本 `defaults` 内的 logical_id 在运行时递归替换为真实 id）

成功后：
- 终端打印 `成功 N / 失败 0`；
- 资源映射（logical_id→real_id）写入 `--state-file`，**回滚时必须保留**。

### 2.1 嵌套引用如何解析
剧本 `defaults` 形如 `{kb_id: qc-kb, skill_id: qc-defect-attribution, mcp_server_id: mes-connector, mcp_tool: query_defect_records}`。
其中 `qc-kb`/`qc-defect-attribution`/`mes-connector` 是 logical_id，会在 KB/技能/MCP 创建后取得的真实 id **递归替换**进剧本载荷；`mcp_tool`（工具名）不被替换。

---

## 3. 验收（对接 `acceptance.md`）

铺包完成后，按对应骨架的 `acceptance.md` 执行 2 周迭代验收：

1. 用客户真实语料替换 `knowledge/seed/`（种子文档已落库，可经 `POST /api/kb/kb/{id}/ingest` 追加真实文档）。
2. 配置 MCP 连接器 `secret_ref` 指向客户真实凭据（如 `vault://mes-readonly`），并 `POST .../sync` 重新拉取工具清单。
3. 在客户租户内发起 Killer Scenario 真实对话，采集 `success_metrics` 的 baseline→target 数据。
4. 通过门槛（见 `acceptance.md` 的「通过门槛」）即视为 POC 上线，可转付费合同。

---

## 4. 回滚（rollback）

如需撤场或重铺，凭铺包时生成的 state 文件反向删除资源：

```bash
# 演练
python provision.py --poc manufacturing --rollback \
  --state-file manufacturing.state.json --token <CLIENT_JWT> --dry-run

# 真实回滚（删除顺序：剧本 → MCP → 技能 → 知识库）
python provision.py --poc manufacturing --rollback \
  --state-file manufacturing.state.json --token <CLIENT_JWT> --tenant-id <CLIENT_TENANT_ID>
```

- 删除端点：`DELETE /api/agent/playbooks/{id}`、`/api/mcp/servers/{id}`、`/api/skills/skills/{id}`、`/api/kb/kb/{id}`（KB 删除级联清理文档与向量）。
- 若 state 文件丢失，可改用手动删除：先 `GET /api/agent/playbooks?tenant_id=...` 列出真实 id，再逐条 DELETE。

---

## 5. 常见问题

| 现象 | 原因 / 处理 |
|---|---|
| `FAIL POST /api/agent/playbooks → 404` | agent-service 未含 `0004_playbook` 迁移 / 未重启。执行 `alembic upgrade head`（PG）后重启服务。 |
| `FAIL POST /api/kb/kb → 4xx` | 缺少 `kb:write` 权限，或网关未挂载 knowledge 路由。检查 RBAC 与网关 `proxy.py`。 |
| 文档 ingest 一直 `parsing` | 向量库不可达。检查 knowledge-service 的 Qdrant/本地向量库连接与嵌入模型。 |
| MCP sync 返回 502 | 连接器 `endpoint` 不可达或协议握手失败。确认客户侧 MCP server 已启动且地址正确。 |
| 剧本跑了但工具调不动 | `defaults.mcp_server_id` 未解析为真实 id（常见于手动改过 payload）。用 `--apply` 自动替换，勿手填。 |

---

## 6. 交付物清单（本目录）

- `README.md` / `SCHEMA.md` —— 入口与规范
- `common.py` —— 加载/构建发布计划（被校验与铺包复用）
- `validate_poc.py` —— 骨架自检（CI 可用）
- `provision.py` —— 铺包 + 回滚
- `manufacturing/`、`finance/` —— 两套骨架（manifest + skills + knowledge/seed + mcp + agent playbook + acceptance）
- `*.state.json` —— 铺包后生成的资源映射（回滚用，**勿提交到仓库**）
