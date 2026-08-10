# 信创（信息技术应用创新）适配指南

本文档说明 WorkBuddy Enterprise 在信创环境下的部署适配方式。平台代码**与数据库方言无关**（标准 SQLAlchemy ORM，无原生 PG/SQLite 专属 SQL），因此信创适配主要通过「配置数据库连接串」完成，无需改动业务代码。

## 1. 适配矩阵

| 层级 | 信创选项 | 平台适配方式 |
| --- | --- | --- |
| CPU | 鲲鹏 / 海光 / 飞腾 | 纯 Python 服务 + 容器化部署，架构无关；x86/arm64 镜像均支持 |
| 操作系统 | 统信 UOS / 麒麟 OS | 通过 Docker 镜像运行，宿主机发行版不影响服务；达梦/金仓客户端驱动随镜像或宿主机安装 |
| 数据库 | 人大金仓 KingBaseES / openGauss | **PostgreSQL 协议兼容** → 复用 `postgresql+psycopg2` 方言（零改动） |
| 数据库 | 达梦 DM | 使用 `dm://` 连接串，部署侧安装 `dmPython` 驱动 |
| 中间件 | 东方通 TongWeb / 宝兰德 | 以独立进程 + 反向代理方式接入，不绑定特定 Java 中间件 |

## 2. 数据库连接串（DATABASE_URL）

平台统一通过环境变量 `DATABASE_URL` 指定数据库。`shared/db/connect.py` 的
`normalize_database_url()` 在读取后做归一化：

```text
# PostgreSQL（主流 / 云）
postgresql+psycopg2://user:pass@host:5432/workbuddy

# 人大金仓 KingBaseES（PG 兼容，自动映射为 PG 方言）
kingbase://kbuser:kbpass@host:54321/workbuddy

# openGauss（PG 兼容，自动映射为 PG 方言）
opengauss://oguser:ogpass@host:5432/workbuddy

# 达梦 DM（需 dmPython 驱动）
dm://SYSDBA:SYSDBA@host:5236/workbuddy

# 本地开发
sqlite:///./auth.db
```

> KingBase / openGauss 与 PostgreSQL 线协议兼容，平台现有 22 张表、迁移脚本、
> 查询均在 PostgreSQL 16 上真实验证通过，可直接平移至这两类信创库。
> 达梦为独立协议，需安装 `dmPython`（`pip install dmPython`），并由 DBA 提供连接参数。

## 3. 代码可移植性结论

- **ORM 标准**：全部模型使用 SQLAlchemy 通用类型（`String` / `Integer` / `Text` /
  `JSON` / `DateTime` / `UUID`），迁移脚本由 alembic autogenerate 生成，未手写方言 SQL。
- **主键策略**：审计表 `audit_logs` 刻意使用 `Integer` 自增主键（而非 `BigInteger`），
  规避 SQLite 不支持 `BIGINT PK` 自增的不可移植问题。
- **JSON 列**：通用 `JSON` 类型在 PostgreSQL 落 `JSONB`、在其它库落对应 JSON 类型；
  agent 的 `steps_json` 在 SQLite 下自动切原生 JSON，PG 下用通用 JSON。
- **唯一注意点**：`auth-service` 种子逻辑对 SQLite 用 `OR IGNORE`、对 PostgreSQL 用
  `ON CONFLICT`；迁移至达梦时需将该分支改为达梦兼容写法（金仓/openGauss 走 PG 分支即可）。

## 4. 等保 / 密评配套

- 等保三级专控项见 `VERIFICATION_REPORT.md` 第 17 节。
- 国密（SM2/SM3/SM4）见 `src/shared/crypto/`，由 `gmssl` 实现，已单元测试覆盖。

## 5. 验证状态

- [x] 连接归一化 `normalize_database_url` 单元测试（KingBase/openGauss→PG、达梦透传、未知方案 fail-fast）
- [x] 全部 6 服务 `DATABASE_URL` 经归一化读取，PostgreSQL 16 上 22 张表真实验证通过
- [ ] 达梦 / 金仓 / 麒麟 OS 实机联调（需客户提供信创环境，本仓库 CI 为 x86_64 + PostgreSQL）
