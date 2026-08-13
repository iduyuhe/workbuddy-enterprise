# marketplace-service —— 生态市场

WorkBuddy Enterprise 的**生态市场**服务，负责 **技能（skill）/ 连接器（connector）/ 专家包（expert）** 三类制品的 **交易与分发**。

## 能力

- **发布（Publish）**：提交包元数据（类型、发布者、摘要、许可证、计费模式 free/paid/subscription、价格、标签、分类、仓库/主页/图标、支持平台）。
- **浏览与发现（Browse）**：按 `type` / `tag` / `license` / `price_model` / `publisher` / 关键词 `q` 筛选，支持 `popular`（按安装量）/ `newest` / `top_rated`（按评分）排序与分页。
- **版本与分发（Versions）**：同一包可发布多个版本（manifest / changelog / download_url / artifact_hash 完整性哈希 / 最低平台版本），最新版本自动推进。
- **租户安装（Install）**：租户级「获取/安装」记录（唯一 package×tenant），写入时维护 `install_count`；支持卸载。多租户隔离：私有包仅对归属租户可见，安装记录按租户隔离。
- **评价与评分（Reviews）**：1–5 星评价，写入时重算 `rating_avg` / `rating_count`。
- **运营统计（Stats）**：总量、按类型分布、总安装量、总评价数、Top 包榜单。

## 端口

默认 `8008`（网关路由前缀 `/api/marketplace`）。

## 身份头（由网关注入）

- `X-Tenant-Id`：当前租户（私有包可见性、安装隔离）
- `X-User-Id`：当前用户（发布者 / 安装者 / 评价者归属）

## 运行

```bash
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://wbadmin:wbsecret@localhost:5432/workbuddy
uvicorn app.main:app --port 8008
```

迁移：`python -m alembic upgrade head`（版本表 `alembic_version_marketplace`）。

## 接入

- **网关**：`gateway/app/core/config.py` 增加 `MARKETPLACE_SERVICE_URL`，`gateway/app/api/proxy.py` 增加 `/api/marketplace` 路由前缀与 `marketplace:read` / `marketplace:write` RBAC 映射。
- **Helm**：`deploy/helm/workbuddy-enterprise/values.yaml` 的 `services` 增加 `marketplace-service`（端口 8008）；`_env.tpl` 注入 `MARKETPLACE_SERVICE_URL`。
