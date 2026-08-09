# 贡献指南 (Contributing Guide)

感谢你关注 **WorkBuddy Enterprise Edition**！我们欢迎所有形式的贡献：Bug 报告、功能建议、文档改进、代码提交。

## 行为准则

参与本社区即表示你同意遵守 [行为准则](./CODE_OF_CONDUCT.md)。请保持友善、专业、尊重。

## 如何开始

1. **Fork** 本仓库到你的账号。
2. **创建分支**：`git checkout -b feat/your-feature` 或 `fix/your-bug`。
3. **本地开发**（参见 [QUICKSTART.md](./QUICKSTART.md) 搭建环境）。
4. **提交**：遵循下方提交规范。
5. **推送** 并创建 **Pull Request** 到 `main` 分支。

## 开发环境

- **后端**：Python 3.11+，建议虚拟环境 `python -m venv .venv`
- **前端**：Node.js 22+，`npm install`
- 本地轻量模式使用 SQLite + 内存向量，无需 GPU / Qdrant / PostgreSQL

## 代码规范

### Python（后端微服务）

- 格式化：推荐 `black` + `isort`
- 静态检查：`flake8` / `ruff`
- 类型：Pydantic v2 做接口校验，关键函数加类型注解
- 每个服务独立 `requirements.txt`，新增依赖请同步更新

### TypeScript（前端）

- 格式化：`prettier`
- 检查：`eslint`
- 严格模式（strict）开启

### 提交信息（Conventional Commits）

```
<type>(<scope>): <subject>
```

常用 `type`：`feat` / `fix` / `docs` / `style` / `refactor` / `test` / `chore`
示例：`feat(knowledge): 支持 MinerU 解析 PDF 表格`

## 测试

- 后端：至少保证 `python -m py_compile` 全通过；关键链路补充 pytest
- 前端：`npm run build` 必须通过
- 提交前请在本地跑通最小闭环（登录 → 建库 → 检索）

## Issue 与 PR

- Bug 请使用 **Bug Report** 模板，附复现步骤与环境信息。
- 新功能请使用 **Feature Request** 模板，说明动机与预期行为。
- PR 请关联对应 Issue，并在描述中说明改动范围与验证方式。

## 联系方式

- 安全漏洞：**请勿公开 Issue**，见 [SECURITY.md](./SECURITY.md)
- 一般讨论：GitHub Discussions / Issues
