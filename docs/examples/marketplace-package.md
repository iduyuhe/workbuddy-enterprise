# 示例：marketplace-package 最小市场包

路径：[`examples/marketplace-package/`](https://github.com/iduyuhe/workbuddy-enterprise/tree/main/examples/marketplace-package)

一个**可直接 `POST /api/marketplace/packages` 上架**的最小包，含 `manifest.yaml` 与 1 个技能。

## 文件结构

```
examples/marketplace-package/
├── manifest.yaml              # 包元数据（对齐 PackageCreate）
├── skills/
│   └── hello/
│       └── SKILL.md           # 包内技能
└── README.md                  # 包说明
```

## manifest.yaml 要点

```yaml
slug: hello-package
name: Hello 示例包
package_type: skill            # skill | connector | expert
publisher: workbuddy-ent-dev
version: 1.0.0
summary: 一个最小可上架示例包，含打招呼技能。
description: 演示生态市场包的最小结构，用于快速验证上架流程。
tags: [demo, starter]
categories: [示例]
license: Apache-2.0
price_model: free              # free | paid | subscription
visibility: public             # public | tenant_private
resources:
  skills:
    - slug: hello
      storage_path: skills/hello
```

## 对齐的契约

- `slug`：包唯一标识；`package_type` 取值 `skill|connector|expert`。
- `resources`：列出包内资源（knowledge_bases / skills / mcp_servers / agents），`storage_path` 指向相对 manifest 的路径。
- 真实上架走 `gateway` 的 `/api/marketplace`（需 `marketplace:write` 权限），多租户下 `tenant_private` 包仅本租户可见。

## 如何运行

```bash
# 校验 manifest 字段
python docs/verify_site.py

# 上架（需运行中的平台 + 令牌）
python src/deploy/poc-references/provision.py \
  --poc examples/marketplace-package --apply \
  --gateway-url http://localhost:8000 --token <JWT> --tenant-id <TENANT>
```

> 注意：`provision.py` 面向 `poc-references` 的完整骨架；本示例的 `manifest.yaml` 字段与其一致，可直接复用同一上架逻辑。
