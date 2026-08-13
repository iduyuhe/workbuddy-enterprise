# Hello 示例包 (marketplace-package)

最小可上架的生态市场包，用于验证 `marketplace-service` 的上架流程。

## 结构

```
marketplace-package/
├── manifest.yaml              # 包元数据（对齐 PackageCreate）
├── skills/
│   └── hello/
│       └── SKILL.md           # 包内技能
└── README.md
```

## manifest.yaml 字段说明

| 字段 | 含义 |
|---|---|
| `slug` | 包唯一标识 |
| `package_type` | `skill` / `connector` / `expert` |
| `publisher` | 发布者 |
| `version` | 语义化版本 |
| `visibility` | `public`（全租户可见）/ `tenant_private`（仅本租户） |
| `price_model` | `free` / `paid` / `subscription` |
| `resources` | 包内资源清单（`skills` / `mcp_servers` / `knowledge_bases` / `agents`），`storage_path` 相对 manifest |

## 上架方式

1. **经网关**：`POST /api/marketplace/packages`（需 `marketplace:write` 权限），多租户下 `tenant_private` 仅本租户可见。
2. **经 provision 工具**（推荐，可复用 POC 骨架逻辑）：
   ```bash
   python src/deploy/poc-references/provision.py \
     --poc examples/marketplace-package --apply \
     --gateway-url http://localhost:8000 --token <JWT> --tenant-id <TENANT>
   ```

## 校验

```bash
python docs/verify_site.py   # 检查 manifest 必填字段与 resources 引用
```
