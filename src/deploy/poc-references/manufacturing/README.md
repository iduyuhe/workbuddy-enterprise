# 制造业·智能质检标杆 POC（参考骨架）

> 阶段 4 · 标杆 POC 的制造业样板。把本目录整体「铺」进客户租户即可跑通一个制造业 Killer Scenario。
> 包结构、字段含义见 [`../SCHEMA.md`](../SCHEMA.md)，校验与发布工具见 [`../README.md`](../README.md)。

## 这个 POC 解决什么
离散制造工厂的质检与设备运维长期依赖老师傅经验：缺陷归因慢、设备突发停机、工艺调整凭感觉。
本 POC 用 WorkBuddy Enterprise 把**知识库 + 技能 + MES 连接器 + 智能体**串成一条可复用的质检与运维闭环。

## 包含的杀手级场景（Killer Scenario）
质检员上报缺陷 → 智能体检索质检知识库 → 调用「质检缺陷归因」技能生成根因假设 →
回查 MES 印证工艺参数与设备状态 → 输出归因报告 + 整改建议并沉淀新案例；
同时「预测性维护」技能提前告警设备劣化、「工艺参数优化」技能给出良率提升区间。

## 目录结构
```
manufacturing/
├── manifest.yaml          # 市场包 + scenario + resources（provision 输入）
├── README.md              # 本文件
├── acceptance.md          # 验收标准 + 成功度量（给客户/评估方）
├── skills/
│   ├── qc-defect-attribution/SKILL.md   # 质检缺陷归因
│   ├── predictive-maintenance/SKILL.md  # 预测性维护
│   └── process-param-optimization/SKILL.md # 工艺参数优化
├── knowledge/seed/        # 知识库种子（缺陷代码库 / 设备手册 / 工艺标准）
├── mcp/mes-connector.yaml # MES 连接器规格（4 个工具）
└── agent/playbook.yaml    # 智能质检助手剧本（默认资源接线 + 场景流）
```

## 三个核心技能
1. **质检缺陷归因**：现象 → 检索 → Top-3 根因假设 + 置信度 → MES 印证 → 报告。
2. **预测性维护**：设备遥测 → 劣化趋势 → 停机前预警 + 维护窗口建议。
3. **工艺参数优化**：良率×参数关联 → Top-3 敏感参数 → 推荐区间 + 预期收益。

## 如何跑
```bash
# 校验骨架合法性
python ../validate_poc.py

# 干跑：查看将产生的 API 调用
python ../provision.py --poc manufacturing --dry-run

# 真实铺包（替换真实 MES 凭证与模型后）
python ../provision.py --poc manufacturing --apply \
    --gateway-url http://<gateway> --token $WB_TOKEN --tenant-id $WB_TENANT
```

## 交付后
通过验收后，把 `manifest.yaml` 直发 `POST /api/marketplace/packages` 即可作为 `expert` 包上架生态市场，
供同行业其他租户「一键获取」（见阶段 4 ② 生态市场）。
