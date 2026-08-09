# shared — 跨服务共享代码

集中存放各服务共用的：
- `schemas/`：Pydantic / OpenAPI 公共数据模型（与 `docs/API_CONTRACT.md` 对齐），避免各服务重复定义。
- 公共客户端封装（auth 客户端、audit 事件发送器）、错误码常量、配置加载器。

> 实现建议：作为 Python 包 `wb_shared` 以路径/workspace 方式被各服务引用；前端共享 TS 类型另置于 `frontend/src/types`。

## 实现团队
后端（统一维护契约模型）。
