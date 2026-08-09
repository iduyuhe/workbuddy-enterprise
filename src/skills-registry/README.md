# skills-registry — 技能注册中心

## 职责
- 兼容 Anthropic Skills 文件式规范（每个 Skill 一个目录含 `SKILL.md`）。
- 技能注册 / 版本管理 / 列表 / 调用元数据；权限与项目隔离。
- 解析 `SKILL.md` 为 manifest 元数据。

## 技术栈
Python 3.11 + FastAPI + SQLAlchemy + PyYAML + Pydantic。

## 运行方式
```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8003
```
环境变量：`DATABASE_URL`、`SKILLS_ROOT`（文件式存储根目录）。

## 实现团队
后端 + AI（manifest 解析/调用协议对接 agent-runtime）。
