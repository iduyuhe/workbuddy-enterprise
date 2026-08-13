# WorkBuddy Enterprise Edition

> **面向大型企业 / 国企 / 央企 / 金融机构的私有化 AI 智能体平台。**
> 数据不出公司内网；兼容 Claude（Anthropic）/ Codex（OpenAI）/ 国产开源大模型（Qwen3 / DeepSeek）；
> 把企业自己的「技能 / 岗位 / 专家 / 团队」沉淀为可治理、可复用的智能体资产。

## 核心特性

- **🔒 数据不出域** —— 推理、向量、业务元数据全部运行在客户内网；支持私有化大模型（vLLM / SGLang）。
- **🧩 模型无关网关** —— 统一抽象层，同时接入 Claude、Codex、Qwen3、DeepSeek；API Key 托管不落明文。
- **📚 企业知识库 RAG** —— 文档解析（MinerU）+ 向量化（bge-m3）+ 向量库（Qdrant）+ 重排，融入企业私有知识。
- **🛠 Skills 注册中心** —— 兼容 Anthropic Skills 文件式规范，把最佳实践沉淀为可复用技能。
- **🔌 MCP 连接器** —— 复用 Model Context Protocol 生态，接入企业现有系统（数据库 / SaaS / 内部 API）。
- **🛡 企业级治理** —— SSO（OIDC）、RBAC、项目级数据隔离、调用级审计日志；预留等保三级 / 内容审核扩展点。
- **🤝 生态市场与社区** —— 技能 / 连接器 / 专家包可上架复用；示例库与贡献者激励体系降低上手门槛。

## 导航

| 你想做什么 | 去这里 |
|---|---|
| 本地 5 分钟跑通最小闭环 | [快速开始](getting-started.md) |
| 理解微服务与数据流 | [系统架构](ARCHITECTURE.md) |
| 对接 REST / 技能 / MCP / 智能体 | [接口契约](API_CONTRACT.md) |
| 生产部署与排障 | [运维手册](RUNBOOK.md) |
| 抄一个最小技能 / 市场包 / 剧本 | [示例库](community/examples.md) |
| 想贡献代码或认领任务 | [贡献指南](community/contributing.md) |
| 了解贡献者分级与激励 | [治理与贡献者激励](community/governance.md) |
| 看产品演进计划 | [路线图](community/roadmap.md) |

## 本地预览本文档站

```bash
pip install mkdocs mkdocs-material
mkdocs serve      # http://127.0.0.1:8000
```

## 许可证

[Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)。商业使用、修改、分发均被允许，请保留版权与许可证声明。
