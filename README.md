# WorkBuddy Enterprise Edition · 企业级本地化部署 AI 智能体平台

> 面向大型企业 / 国企 / 央企 / 金融机构 / 信息安全敏感行业的 **私有化部署版 AI 智能体工作台**。
> 数据不出公司内网；兼容 Claude（Anthropic）/ Codex（OpenAI）/ 国产开源大模型（Qwen3 / DeepSeek）；
> 融入企业自己的「技能 / 岗位 / 专家 / 团队」业务资产。

---

## 项目状态

🟡 **MVP 阶段 1 开发中**（智能体团队 `workbuddy-ent-dev` 并行实现中）

- [x] 架构设计（`docs/ARCHITECTURE.md` / `docs/API_CONTRACT.md`）
- [x] 私有化部署底座（`src/deploy/`：vLLM + Qdrant + Postgres + Redis + 监控全编排）
- [x] 微服务骨架（`src/` 9 个服务目录）
- [ ] 后端核心链路（gateway / auth / model-gateway / audit）— 实现中
- [ ] 后端 AI 链路（knowledge / skills / mcp）— 实现中
- [ ] 前端控制台（React/TS）— 实现中

---

## 目录结构

```
enterprise-platform-plan/
├── README.md                  # 本文
├── docs/
│   ├── ARCHITECTURE.md        # MVP 技术架构（拓扑/服务/DDL/数据流/安全）
│   └── API_CONTRACT.md        # 服务间 REST 接口契约（唯一接口事实来源）
├── deploy/                    # 私有化部署资产（DevOps）
│   ├── docker-compose.yml     # 一键编排
│   ├── .env.example           # 配置样例
│   ├── vllm/start.sh          # 推理启动脚本
│   ├── prometheus/            # 指标抓取
│   └── grafana/               # 监控面板
└── src/                       # 微服务源码（monorepo）
    ├── gateway/               # API 网关（:8000，唯一入口）
    ├── model-gateway/         # 模型网关（:8001，调 vLLM/SGLang/Claude）
    ├── auth-service/          # 认证授权 + RBAC（:8002）
    ├── skills-registry/       # 技能注册中心（:8003）
    ├── mcp-connector/         # MCP 连接器（:8004）
    ├── knowledge-service/     # 企业知识库 RAG（:8005）
    ├── audit-service/         # 审计服务（:8006）
    ├── frontend/              # React/TS 控制台（:3000）
    └── shared/                # 跨服务共享模型
```

---

## 快速启动

详见 [`src/deploy/README.md`](src/deploy/README.md)：

```bash
# 1. 准备模型权重（Qwen3-235B-A22B）到 /models
# 2. 配置环境变量
cp src/deploy/.env.example src/deploy/.env
# 3. 启动全栈
cd src/deploy && docker compose up -d
```

---

## 关键设计原则

1. **数据不出域**：推理、向量、业务数据均在客户内网。
2. **模型无关**：上层通过模型网关统一接入 Qwen3 / DeepSeek / Claude。
3. **薄网关 + 微服务**：gateway 只做鉴权与路由，业务逻辑下沉各微服务。
4. **最小闭环优先**：MVP 先跑通「带企业知识的对话」，治理（内容审核/等保三级）阶段 2 扩展。

---

## 相关文档

- 整体战略评估与规划：`WorkBuddy-企业级本地化部署平台-评估与规划报告-v1.0.md`
- 技术架构：`docs/ARCHITECTURE.md`
- 接口契约：`docs/API_CONTRACT.md`

---

_由智能体开发团队 `workbuddy-ent-dev` 构建。_
