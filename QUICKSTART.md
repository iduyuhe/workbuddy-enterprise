# 本地快速体验 (Quick Start · 无需 GPU)

本文档帮你在**笔记本 / 开发机**上跑通 WorkBuddy Enterprise 的最小闭环，使用 SQLite + 内存向量降级，**不依赖 GPU、Qdrant、PostgreSQL**。验证环境（Windows，Python 3.11）实测通过。

## 1. 准备后端

```bash
# 进入项目
cd workbuddy-enterprise

# 建虚拟环境（任选一个服务目录复用即可，各服务依赖独立）
python -m venv .venv
source .venv/Scripts/activate        # Windows Git Bash
# source .venv/bin/activate          # macOS / Linux

# 安装 7 个服务的依赖
for s in gateway auth-service model-gateway knowledge-service skills-registry mcp-connector audit-service; do
  pip install -r src/$s/requirements.txt
done
```

> 注意：`knowledge-service` 需要 `python-multipart`（文件上传）与 `sentence-transformers`（bge-m3）。首次会自动下载 bge-m3 模型（约 2GB），无 GPU 时仅用 CPU 推理，速度较慢但可用。

## 2. 启动 7 个服务

每个服务单独开一个终端，或后台启动：

```bash
cd src/auth-service      && uvicorn app.main:app --port 8002 > /tmp/auth.log 2>&1 &
cd src/model-gateway     && uvicorn app.main:app --port 8001 > /tmp/mgw.log 2>&1 &
cd src/audit-service     && uvicorn app.main:app --port 8006 > /tmp/audit.log 2>&1 &
cd src/knowledge-service && uvicorn app.main:app --port 8005 > /tmp/kb.log 2>&1 &
cd src/skills-registry   && uvicorn app.main:app --port 8003 > /tmp/skills.log 2>&1 &
cd src/mcp-connector     && uvicorn app.main:app --port 8004 > /tmp/mcp.log 2>&1 &
cd src/gateway           && uvicorn app.main:app --port 8000 > /tmp/gw.log 2>&1 &
sleep 8
```

## 3. 验证核心链路（curl）

```bash
# 登录拿 token
curl -s -X POST http://127.0.0.1:8002/auth/login/local \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}'

# 创建知识库
KB=$(curl -s -X POST http://127.0.0.1:8005/kb \
  -H 'Content-Type: application/json' -d '{"name":"demo","project_id":null}')
echo $KB
```

### 上传文档（重要：Windows 下路径用 Windows 格式）

```powershell
# 用 PowerShell 起服务时，curl 上传文件需 Windows 路径，例如：
curl.exe -X POST "http://127.0.0.1:8005/kb/<KB_ID>/ingest" -F "file=@D:\path\to\doc.txt"
```

> ⚠️ 在 Windows Git Bash 中用 `curl -F "file=@/d/.../doc.txt"` 会因路径格式静默失败；请改用 Windows 绝对路径（如 `D:\...\doc.txt`）。这是测试命令的坑，与服务代码无关。

### 检索

```bash
curl -s -X POST http://127.0.0.1:8005/kb/<KB_ID>/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"你的检索问题","top_k":3}'
```

应返回语义匹配片段（score > 0）。

## 4. 前端

```bash
cd src/frontend
npm install
npm run dev        # http://localhost:3000
```

浏览器打开 → 用 `admin / admin123` 登录 → 进入「对话」选知识库、「知识库」上传文档并检索。

## 5. 关于「对话」

本机无 GPU / 无 vLLM 时，网关 `/api/v1/chat` 会返回**明确的错误提示**（而非崩溃）。要跑通真实对话，需要：

- GPU 节点 + `vLLM` 加载 `Qwen3-235B-A22B-FP8`（见 `src/deploy/`）
- 或配置 `model-gateway` 接入 Claude / Codex（API Key 经合规网关）

## 6. 清理

```bash
# 停服务（Windows 用任务管理器或 PowerShell 停止 uvicorn 进程）
Get-NetTCPConnection -LocalPort 8000,8001,8002,8003,8004,8005,8006 -State Listen |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

---

生产级部署（GPU / Qdrant / PostgreSQL / 监控）见 [`src/deploy/README.md`](./src/deploy/README.md)。
