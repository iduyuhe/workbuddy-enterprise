# 示例：hello-skill 最小技能

路径：[`examples/hello-skill/`](https://github.com/iduyuhe/workbuddy-enterprise/tree/main/examples/hello-skill)

一个**最小但完整**的技能，演示 Anthropic 风格 `SKILL.md` 的写法。该格式被 `skills-registry` 的 `skill_parser.parse_skill_md` 直接解析。

## 文件结构

```
examples/hello-skill/
└── SKILL.md        # 唯一文件：YAML frontmatter + 步骤体
```

## SKILL.md 要点

```markdown
---
name: hello-skill
description: 当用户说"你好"/"打招呼"/"自我介绍"时，用企业标准话术回礼并引导至正确入口。
---

# Hello Skill

## 何时使用
用户发起寒暄、首次进入对话、或询问"你能做什么"。

## 步骤
1. 用 1 句话回礼，带上产品名 WorkBuddy Enterprise。
2. 用 ≤ 3 个要点说明平台能做什么（私有化部署 / 知识库 RAG / 技能与连接器）。
3. 引导用户说出具体场景（如"我想接入我们公司的知识库"）。
```

## 对齐的契约

- `name`：技能唯一标识，小写中划线。
- `description`：必须写清**触发条件**（"当用户……时"），运行时据此路由。
- 正文用 Markdown 标题组织「何时使用 / 步骤 / 注意事项」。

## 如何上架

把 `SKILL.md` 目录作为 `package_type: skill` 的包发布到生态市场，或在 `provision.py` 中作为 `skill` 资源铺进租户。校验用 `python docs/verify_site.py`（会检查 frontmatter 必填字段）。
