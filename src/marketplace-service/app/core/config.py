"""marketplace-service 配置加载（env 驱动，零依赖）。"""
import os

SERVICE_NAME = "marketplace-service"
PORT = int(os.getenv("PORT", "8008"))

# 网关 / 上游注入的身份头；MVP 仅读取，不强制鉴权（由 gateway 统一校验）
HEADER_USER_ID = "X-User-Id"
HEADER_TENANT_ID = "X-Tenant-Id"

# 包类型与计费模式枚举（生态市场覆盖：技能 / 连接器 / 专家包）
PACKAGE_TYPES = ("skill", "connector", "expert")
PRICE_MODELS = ("free", "paid", "subscription")
