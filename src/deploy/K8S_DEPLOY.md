# WorkBuddy Enterprise Edition —— K8s 生产编排指南（Helm）

本目录下的 Helm chart `helm/workbuddy-enterprise` 提供「千企规模」生产编排：7 微服务 + 网关 + 模型网关 + 依赖存储（PostgreSQL / Redis / Qdrant），内置**弹性伸缩（HPA）**与**灰度发布（Canary）**。

> 验证方式：`helm lint` + `helm template` 真实渲染，并用 PyYAML 二次校验产出为合法多文档 YAML（见文末「真实验证」）。本环境无 K8s 集群，未做 `kubectl apply` 实测——上线前请在目标集群执行 `helm install` 验证。

## 1. 目录结构

```
src/deploy/helm/workbuddy-enterprise/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── _helpers.tpl        # 公共标签 / 镜像 / 依赖主机名
    ├── _env.tpl            # 公共容器 env（DB/Redis/Qdrant/密钥/服务间 URL）
    ├── secret.yaml         # 密钥（jwt/PG/Redis/OIDC/LLM）
    ├── deployment.yaml      # 各服务 Deployment（range）
    ├── service.yaml         # 各服务 ClusterIP Service（range）
    ├── hpa.yaml             # 各服务 HPA（range，autoscaling.enabled 控制）
    ├── ingress.yaml         # 仅暴露 gateway 入口
    ├── canary-deployment.yaml / canary-service.yaml / canary-ingress.yaml
    ├── postgresql.yaml / redis.yaml / qdrant.yaml   # 可选集群内部署
    ├── web.yaml             # 前端（默认关闭）
    └── NOTES.txt
```

## 2. 端口规划（与 docker-compose / 服务代码一致）

| 服务 | 端口 | 说明 |
|---|---|---|
| gateway | 8000 | 用户侧 API 网关（唯一 Ingress 入口） |
| model-gateway | 8001 | 模型网关（vLLM / DeepSeek / 外部 BYOK） |
| auth-service | 8002 | 认证 / RBAC / OIDC |
| skills-registry | 8003 | 技能注册中心 |
| mcp-connector | 8004 | MCP 连接器 |
| knowledge-service | 8005 | 知识库 RAG |
| audit-service | 8006 | 安全审计（SM4 加密 + SM3 完整性） |
| agent-service | 8007 | Agent 运行时（LangGraph） |

## 3. 安装

```bash
# 1) 准备镜像：将 8 个服务分别构建并推送到镜像仓库
#    workbuddy/gateway  workbuddy/model-gateway  workbuddy/auth-service
#    workbuddy/skills-registry  workbuddy/mcp-connector
#    workbuddy/knowledge-service  workbuddy/audit-service  workbuddy/agent-service
#    （镜像名在 values.yaml 的 services.<svc>.image.repository 配置）

# 2) 创建命名空间
kubectl create namespace workbuddy

# 3) 安装（生产建议先用外部托管 PG/Redis/Qdrant）
helm upgrade --install workbuddy ./helm/workbuddy-enterprise \
  --namespace workbuddy \
  -f values.yaml \
  --set global.domain=your.domain.com \
  --set secrets.jwtSecret=$(openssl rand -hex 32) \
  --set secrets.postgresPassword=$(openssl rand -base64 18)

# 4) 查看状态
kubectl -n workbuddy get pods
kubectl -n workbuddy get hpa
```

## 4. 依赖存储：外部 vs 集群内

生产环境**推荐外部托管实例**（云 RDS / Redis / 向量库），更安全、易运维：

```bash
# 使用外部 PostgreSQL / Redis / Qdrant（默认）
# 在 values.yaml 中设置：
postgresql:
  enabled: false
  host: your-pg.xxx.rds.amazonaws.com
  port: 5432
  user: wbadmin
  database: workbuddy
redis:
  enabled: false
  host: your-redis.cache.amazonaws.com
  port: 6379
qdrant:
  enabled: false
  url: http://your-qdrant.internal:6333
```

起步 / 小规模可在集群内部署单实例（非 HA，仅供验证）：

```bash
helm upgrade --install workbuddy ./helm/workbuddy-enterprise \
  --namespace workbuddy \
  --set postgresql.enabled=true --set redis.enabled=true --set qdrant.enabled=true
```

## 5. 弹性伸缩（HPA）

每个服务默认开启 HPA（`autoscaling.enabled: true`），按 CPU（目标 70%）与内存利用率自动扩缩：

```bash
# 查看自动伸缩
kubectl -n workbuddy get hpa

# 手动扩缩某个服务
kubectl -n workbuddy scale deploy workbuddy-agent-service --replicas=20

# 调整阈值（values.yaml）
services:
  agent-service:
    autoscaling:
      minReplicas: 2
      maxReplicas: 12
      targetCPUUtilizationPercentage: 75
```

## 6. 灰度发布（Canary / 灰度）

通过网关入口的 Nginx Ingress 按权重切流，实现零停机灰度：

```bash
# 1) 构建灰度镜像（tag 区别于稳定版）
docker tag workbuddy/gateway:new your-registry/gateway:canary

# 2) 开启灰度（按 10% 权重切流，也可加 canary-by-header: X-Canary 做精准灰度）
helm upgrade workbuddy ./helm/workbuddy-enterprise \
  --namespace workbuddy \
  --set services.gateway.canary.enabled=true \
  --set services.gateway.canary.weight=10 \
  --set services.gateway.canary.image.tag=canary
```

灰度资源（`<release>-gateway-canary` Deployment + Service）与稳定版并存，
Ingress `nginx.ingress.kubernetes.io/canary-weight` 控制流量比例。验证无误后：
- 将 `canary.image.tag` 提升为稳定 tag，关闭 canary；或
- 逐步调大 `weight` 至 100 后切换。

## 7. 密钥管理

默认由 Secret `{{ release }}-secrets` 提供（`secrets.*` 值）。生产请用：

- **Sealed Secrets** / **External Secrets Operator** 从 Vault / 云密钥库注入；
- 或 `postgresql.existingSecret` 指定已有 Secret（key: `postgres-password`）。

## 8. 真实验证（本仓库 CI 等价检查）

| 检查 | 命令 | 结果 |
|---|---|---|
| 模板静态检查 | `helm lint workbuddy-enterprise` | `0 chart(s) failed` |
| 默认渲染 | `helm template … \| yaml` | 26 个合法资源（8×{Deploy,Svc,HPA} + Ingress + Secret） |
| 灰度场景 | `--set services.gateway.canary.enabled=true` | 29 个资源（增 canary Deploy/Svc/Ingress） |
| 依赖存储场景 | `--set postgresql/redis/qdrant.enabled=true` | 35 个资源（增 PG/Redis/Qdrant Deploy/Svc/PVC） |
| YAML 合法性 | PyYAML `safe_load_all` | 三场景均解析为独立文档，关键字段断言通过 |

> 注：本沙箱无 K8s 控制面，未执行 `kubectl apply` 实测；上线前请在目标集群完成端到端 apply 与冒烟。
