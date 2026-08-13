# 路线图 (Roadmap)

WorkBuddy Enterprise Edition 采用「先跑通最小闭环、再阶梯式增强」的演进策略。当前已完成 **阶段 1（MVP）**，后续阶段规划如下。

## ✅ 阶段 1 · MVP 最小闭环（已完成 · v0.1.0）

- [x] 私有化部署底座（docker-compose：vLLM + Qdrant + PostgreSQL + Redis + 监控）
- [x] 7 个后端微服务 + React 控制台
- [x] 模型网关（Qwen3 / DeepSeek / Claude 抽象）
- [x] 企业知识库 RAG（解析→切片→向量→检索）
- [x] 认证 / RBAC / 审计埋点
- [x] MVP 全链路真实验证（`VERIFICATION_REPORT.md`）

## 🔜 阶段 2 · 生产化与智能增强（部分完成 · 2026-08-09 晚补充）

- [x] **生产数据层 · Qdrant**：知识库支持 `QDRANT_URL`（独立服务端）/ `QDRANT_LOCAL_PATH`（嵌入式本地引擎，已真实验证）/ InMemory（dev）三级；RAG 闭环走真实 Qdrant 引擎
- [x] **生产数据层 · PostgreSQL**：所有服务 `DATABASE_URL` 已配置化；agent-service 已真实接入 PostgreSQL 16.14（Docker 容器 `wb-pg`）端到端跑通——ORM 自动建 `agent_runs`（id/project_id/user_id/prompt/answer/steps_json/model/status/created_at）、`steps_json` 在 PG 落 JSONB、HTTP 4/4 + DB 8/8 二次校验全绿（详见 `VERIFICATION_REPORT.md` 第 12 节）
- [x] **统一 PG 后端（6 服务）**：auth / audit / skills-registry / mcp-connector / knowledge-service / agent-service 全部注入 `DATABASE_URL=postgresql+psycopg2://...` 接同一真实 PG 实例；psycopg2-binary 加入各服务 requirements；修复 PG 复合主键严格性（`user_roles` 改 surrogate 主键 + 唯一约束）、JSON 列 introspection 兼容；编排脚本 `run_all_pg_e2e.sh` + `e2e_verify_all_pg.py` 做 6 表「精确 id 命中」二次校验（防历史数据假绿），13/13 全绿（详见第 13 节）
- [x] **schema 演进 · alembic**：agent-service 引入 alembic（`alembic.ini` + `migrations/env.py` + `versions/0001_initial.py` 建 `agent_runs`），`init_db()` 改为「优先 `alembic upgrade head`，失败回退 `create_all`」；修复 Windows 下 `alembic.ini` 中文注释触发 configparser gbk 解码失败、及 `db.py` 计算 `_here` 少一层导致回退 create_all 两个工程坑，`run_alembic_pg.sh` 验证 alembic 真正在 PG 建表 + agent 落库全绿（详见第 13 节）。**已推广至其余 5 个服务**（auth/audit/skills-registry/mcp-connector/knowledge-service），每个服务独立 `alembic_version_<svc>` 版本表避免共享库迁移链冲突，autogenerate 对真实 PG 生成初始迁移 + `init_db` 验证全部走 alembic 路径（详见第 15 节）
- [x] **Agent 运行时**：LangGraph `StateGraph` 编排 ReAct 循环，Skills / MCP / 知识库检索真实执行；`real_llm` 经 model-gateway 打真实 LLM（OpenAI 工具调用协议，解析 `tool_calls`），`AGENT_ENABLE_MOCK_LLM=false` 即切换；默认资源 ID 通过 system 提示注入，真实工具调用开箱即用（2026-08-10 真实路径 E2E 全绿）
- [x] **内容审核**：`shared/moderation.py` 输入输出双通道管线，PII（手机/身份证/银行卡/邮箱）正则打码 + 涉密/暴力词表；支持 `block` / `redact` / `log` 三模式；agent 内部编排器用 `redact`、网关边缘用 `block`（2026-08-10 单元测试 + E2E 全绿）
- [x] **多模型路由策略**：model-gateway 按模型名/前缀路由 vLLM / SGLang / Claude，并新增**外部 BYOK OpenAI 兼容 provider**（豆包 Ark / DeepSeek / 通义 / 智谱 等任意 `/v1/chat/completions` 端点，带 `Authorization: Bearer` 鉴权），由 `LLM_API_BASE` / `LLM_API_KEY` / `LLM_MODEL` 配置即插即用；无 GPU 时优雅 mock
- [x] **真实 LLM 接入（DeepSeek 真实验证）**：model-gateway 新增独立 `DEEPSEEK_API_KEY` + `deepseek-*` 前缀路由，直达 `https://api.deepseek.com/v1`；agent `AGENT_ENABLE_MOCK_LLM=false` + `AGENT_DEFAULT_MODEL=deepseek-chat` 经 model-gateway 调真实云端推理。**2026-08-10 用真实 DeepSeek Key 跑通完整 ReAct 闭环**：模型自主决定 `search_kb / use_skill / call_mcp_tool` → `tool_calls` 解析 → 工具真实执行 → 中文综合作答，`run_deepseek.sh` + `e2e_verify_deepseek.py` 真实验证 4/4 连续稳定全绿。修复两个会因真实 LLM 暴露的生产 bug：`_to_openai` 把 `tool_calls.arguments` 序列化为 JSON 字符串（此前塞 dict 被真实 API 拒收 400）；真实 provider 失败重试且不再静默回退 mock（避免「假成功」）
- [x] **前端完善**：`npm run build` 通过（修复 tsconfig + Chat.tsx 导入）；OIDC 回调落地（授权码流程 + 前端 token 落地）；知识库文档列表已实现。**知识库项目切换 UX 补完**：切换知识库时经 `listDocuments` 回填文档列表并带加载态/空态，未终态（pending/parsing）文档继续轮询至 indexed/failed（详见第 16 节）
- [x] **OIDC 单点登录真实回调（E2E 验证）**：手写 `oidc.py`（discovery + authorize URL + code 换 token + jwks RS256 验签 + 自动开通用户）已配合**真实 dev RS256 IdP**（`dev_oidc_idp.py`）做完整授权码闭环真实验证：`/auth/login` → IdP `/authorize` 自动发码回跳 → `/auth/callback` 换 token + 验签 → 自动开通用户并发平台 JWT → `/auth/me` 返回用户。修复 `oidc_login_start` 把 cookie 设在注入 `Response` 参数而非返回的 `RedirectResponse` 导致 `oidc_state` CSRF cookie 丢失的 latent bug，`run_oidc_e2e.sh` + `e2e_verify_oidc.py` 6 项断言全绿（详见第 14 节）

## ✅ 阶段 3 · 合规与信创（已完成 · 2026-08-10）

- [x] **信创适配**：`shared/db/connect.py` 连接串归一化（KingBaseES / openGauss 复用 `postgresql+psycopg2` 方言，达梦透传 `dm://`），6 服务 `DATABASE_URL` 统一经 `normalize_database_url()`；单测 6/6 全绿，`XINCHUANG_DEPLOY.md` 给出适配矩阵与可移植性结论（详见 `VERIFICATION_REPORT.md` 第 17 节）
- [x] **等保三级**：身份鉴别（密码复杂度 + 登录失败锁定）、访问控制（网关 per-IP 限流 + 安全响应头）、安全审计（审计明细 SM4 落盘加密 + SM3 完整性哈希防篡改）、入侵防范（限流中间件）、数据完整性与保密性（国密加密落盘）专控项全部落地，E2E 验证全绿（详见第 18 节）
- [x] **密评**：`shared/crypto/sm.py` 封装国密 SM2/SM3/SM4（gmssl），SM3('abc') 与 GB/T 32905 标准向量一致，SM2 签名/验签/加解密、SM4 roundtrip 单测 8/8 全绿（详见第 19 节）
- [x] **多租户**：核心模型加 `tenant_id` 列，列表端点按 `tenant_id` 过滤（ORM 级 + API 级双重隔离）；auth(users/projects) / knowledge(knowledge_bases) / agent(agent_runs) 0003 迁移真实 PG `upgrade head` 验证 `tenant_id` 列就位，跨租户不可见 E2E 全绿（详见第 20 节）

## 🔜 阶段 4 · 规模交付与生态

- [x] **千企规模**：K8s + Helm 生产编排，弹性伸缩，灰度发布（`helm/workbuddy-enterprise` chart：8 服务 Deployment/Service/HPA + Ingress + 可选 PG/Redis/Qdrant 集群内实例；HPA 弹性伸缩；Nginx Ingress 权重灰度。helm lint + 三场景 helm template + PyYAML 校验全绿，详见 `src/deploy/K8S_DEPLOY.md` 与 VERIFICATION_REPORT 第 21 节）
- [x] **生态市场**：技能 / 连接器 / 专家包的交易与分发（新增 `marketplace-service`：发布 / 浏览筛选 / 版本分发 / 租户安装(获取) / 评价评分 / 运营统计；多租户隔离；真实 PG e2e 7/7 全绿；接入 gateway `/api/marketplace` 路由 + RBAC + Helm 渲染。详见 VERIFICATION_REPORT 第 22 节）
- [x] **标杆 POC**：制造业 / 金融业样板客户，沉淀行业 Killer Scenario（两套可直接铺进租户的参考骨架：`src/deploy/poc-references/` 下的 manufacturing / finance，含市场包清单 + 技能 + 知识库种子 + MCP 连接器 + 智能体剧本 + 验收标准；`validate_poc.py` 校验 0 error、`provision.py` 干跑通过。详见 VERIFICATION_REPORT 第 23 节）
- [x] **社区运营**：文档站点、示例库、贡献者激励（mkdocs 站点 + `examples/` 三示例 + `GOVERNANCE.md` 激励体系；`verify_site.py` 校验 0 error。详见 VERIFICATION_REPORT 第 24 节）

## 🔜 阶段 5 · 商业化与试点交付

- [x] **试点交付包（Pilot Delivery）**：把标杆 POC 从「骨架」升级为「可交付资产」。
  - **补平台缺的剧本端点**：agent-service 新增 `agent_playbooks` 资源（模型 + `0004_playbook` 迁移 + Pydantic schema + REST 路由 `POST/GET/PATCH/DELETE /agent/playbooks` + `tenant_id` 多租户隔离），对齐网关 `/api/agent` 与 `provision.py` 铺包目标。
  - **校准铺包契约**：`provision.py` / `common.py` 端点与载荷对齐平台真实路由——KB 创建 `/api/kb/kb`、文档灌入 `/api/kb/kb/{id}/ingest`（multipart）、技能 `/api/skills/skills`、剧本 `/api/agent/playbooks`；apply 时注入租户/项目隔离键，并对剧本 `defaults` 做嵌套 logical_id→real_id 递归替换。
  - **回滚能力**：`provision.py --rollback` 按 state 文件反向删除（剧本→MCP→技能→知识库），支持 `--dry-run` 演练。
  - **交付手册**：`src/deploy/poc-references/PILOT_DELIVERY.md`（环境前置 / 一键铺包 / 验收 / 回滚 / 排错）。
  - **校验**：`validate_poc.py` 两套 0 error；`provision.py --dry-run` 端点/载荷正确；回滚 dry-run 反向顺序正确；agent-service 新文件语法编译通过、迁移模块导入无误。`0004_playbook` 与既有 `0001_initial` 同样使用 PostgreSQL JSONB（SQLite 无法渲染 JSONB，故 alembic 仅支持 PG——属项目级既有约束，非本次引入）。详见 VERIFICATION_REPORT 第 25 节；**`0004_playbook` 真实 PG 建表已闭环验证（PostgreSQL 16.14 上 `agent_playbooks` 表 + `defaults`/`scenario_flow` JSONB 列 + 租户索引均就位，见 §25.5）**。
- [x] **商业化支撑文档**：面向首份付费合同与规模销售的统一底稿（`docs/commercialization.md`）。含价值主张与三道护城河、目标客群分层、四档定价与授权模型（旗舰版 ¥80-150 万/年 · 行业定制版 ¥50-100 万/年 · SaaS ¥800-3000/席/月 · 生态版分成）、竞品定位、ROI 保守测算（18 月约 ¥1850 万）、销售赋能包（demo 话术 / FAQ / 投标材料清单）、风险与应对。对齐规划报告 2.5 / 4.x。详见 VERIFICATION_REPORT 第 26 节。
- [x] **生产化闭环**：把 MVP 升级为生产环境可长期稳定运行的闭环（`docs/production-readiness.md`）。含生产就绪清单（Go-Live Checklist）、可观测性（Prometheus+Grafana+Langfuse）、备份与容灾（PG/Qdrant/Redis 的 RPO/RTO 与恢复演练）、SLA 与 7×24 值守、升级与补丁（Helm 灰度 + alembic 迁移先行 + 回滚）、客户支持 L1/L2/L3、安全运营常态化（等保三级 / 密评 / 内容审核 / 审计日常化）、闭环校验证据。衔接 RUNBOOK / K8S_DEPLOY / SECURITY / 阶段 3 合规。详见 VERIFICATION_REPORT 第 27 节。

## 不确定性

- GPU 推理资源到位时间影响「真实对话 Demo」交付
- 信创适配范围取决于首批 POC 客户的合规要求
- 大模型开源权重演进（Qwen / DeepSeek 新版本）将持续影响选型

---

> 路线图随评估与规划报告演进，详见 `WorkBuddy-企业级本地化部署平台-评估与规划报告-v1.0.md`。
