"""skills-registry 配置加载（env 驱动，零依赖）。"""
import os

SERVICE_NAME = "skills-registry"
PORT = int(os.getenv("PORT", "8003"))

# 文件式技能的根存储目录；注册时传入的 storage_path 相对/绝对于此或直接使用绝对路径
SKILLS_STORAGE_ROOT = os.getenv("SKILLS_STORAGE_ROOT", "./skills_data")

# 内部调用信任网关注入的头部；MVP 仅读取，不强制鉴权（由 gateway 统一校验）
HEADER_USER_ID = "X-User-Id"
HEADER_PROJECT_ID = "X-Project-Id"
