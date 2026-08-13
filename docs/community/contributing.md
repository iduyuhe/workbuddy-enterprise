# 贡献指南（社区版）

完整流程见仓库根 [`CONTRIBUTING.md`](https://github.com/iduyuhe/workbuddy-enterprise/blob/main/CONTRIBUTING.md)。本页聚焦**如何快速认领任务并进入贡献者体系**。

## 三步开始贡献

1. **Fork & 分支**：`git checkout -b feat/your-feature` 或 `fix/your-bug`。
2. **本地开发**：后端 Python 3.11+（建议 venv），前端 Node 22+；本地轻量模式用 SQLite + 内存向量，无需 GPU。
3. **提交 & PR**：遵循 Conventional Commits（`feat(scope): subject`），PR 关联对应 Issue 并说明验证方式。

## 认领任务（推荐新贡献者路径）

GitHub Issues 带以下标签，按需认领：

- `good first issue` —— 文档、示例、单测等小任务，最适合第一次贡献。
- `help wanted` —— 中等任务，欢迎社区力量。
- `docs` / `examples` —— 文档站与示例库相关。

在 Issue 下留言 **"I'd like to take this"**，Maintainer 会在 48 小时内确认并 Assign 给你。

## 代码规范速览

- **Python**：`black` + `isort`；`ruff`/`flake8` 检查；Pydantic v2 做接口校验；每服务独立 `requirements.txt`。
- **TypeScript**：`prettier` + `eslint`，开启 strict。
- **测试**：后端至少 `py_compile` 全通过；前端 `npm run build` 必须通过；提交前跑通最小闭环（登录 → 建库 → 检索）。

## 贡献者激励

合并首个 PR 即进入 `CONTRIBUTORS`；持续贡献可晋升 Member / Maintainer，获得路线图投票权、贡献者墙展示、年度榜单与共建邀约。详见 [治理与贡献者激励](governance.md)。

## 行为准则

参与即表示遵守 [行为准则](code-of-conduct.md)。安全漏洞请勿公开 Issue，见仓库 `SECURITY.md`。
