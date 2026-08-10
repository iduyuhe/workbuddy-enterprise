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
- [ ] **生产数据层 · PostgreSQL**：所有服务 `DATABASE_URL` 已配置化（默认 sqlite），docker-compose 已注入 PG；本环境无 PG 服务，未端到端验证
- [x] **Agent 运行时**：LangGraph `StateGraph` 编排 ReAct 循环，Skills / MCP / 知识库检索真实执行（无 GPU 时走 mock-LLM 确定性路由验证全链路）；gateway 已接入 `/api/v1/chat` 代理到 agent-service（2026-08-10 真实验证全绿）
- [x] **内容审核**：`shared/moderation.py` 输入输出双通道管线，PII（手机/身份证/银行卡/邮箱）正则打码 + 涉密/暴力词表；支持 `block` / `redact` / `log` 三模式；agent 内部编排器用 `redact`、网关边缘用 `block`（2026-08-10 单元测试 + E2E 全绿）
- [x] **多模型路由策略**：model-gateway 按模型名/前缀路由 vLLM / SGLang / Claude，真实 `/v1/chat/completions` 调用已具备（无 GPU 时优雅 mock）
- [x] **前端完善**：`npm run build` 通过（修复 tsconfig + Chat.tsx 导入）；OIDC 回调落地（授权码流程 + 前端 token 落地）；知识库文档列表已实现（项目切换 UX 待补）

## 🔜 阶段 3 · 合规与信创

- [ ] **信创适配**：鲲鹏 / 海光 / 飞腾 CPU，统信 UOS / 麒麟 OS，达梦 / 人大金仓库
- [ ] **等保三级**：专控项落地（身份鉴别、访问控制、安全审计、入侵防范、数据完整性与保密性）
- [ ] **密评**：国密算法（SM2/SM3/SM4）支持
- [ ] **多租户**：组织 / 租户隔离，企业级账号体系

## 🔜 阶段 4 · 规模交付与生态

- [ ] **千企规模**：K8s + Helm 生产编排，弹性伸缩，灰度发布
- [ ] **生态市场**：技能 / 连接器 / 专家包的交易与分发
- [ ] **标杆 POC**：制造业 / 金融业样板客户，沉淀行业 Killer Scenario
- [ ] **社区运营**：文档站点、示例库、贡献者激励

## 不确定性

- GPU 推理资源到位时间影响「真实对话 Demo」交付
- 信创适配范围取决于首批 POC 客户的合规要求
- 大模型开源权重演进（Qwen / DeepSeek 新版本）将持续影响选型

---

> 路线图随评估与规划报告演进，详见 `WorkBuddy-企业级本地化部署平台-评估与规划报告-v1.0.md`。
