# 金融业·智能合规标杆 POC（参考骨架）

> 阶段 4 · 标杆 POC 的金融业样板。把本目录整体「铺」进客户租户即可跑通一个金融业 Killer Scenario。
> 包结构、字段含义见 [`../SCHEMA.md`](../SCHEMA.md)，校验与发布工具见 [`../README.md`](../README.md)。

## 这个 POC 解决什么
银行/券商/保险等持牌机构受强监管：研报产出慢、合规条款比对靠人工、监管报送易错且差错即受罚。
本 POC 用 WorkBuddy Enterprise 把**知识库 + 技能 + 报送系统连接器 + 智能体**串成一条可复用的合规与投研闭环。

## 包含的杀手级场景（Killer Scenario）
研究员上传研报草稿 → 智能体摘要与问答、核对数据口径 → 「合规条款比对」逐条比对内部制度与监管红线 →
「监管报送核对」经报送系统连接器核对报表字段口径、提示缺失与差错 → 输出合规结论 + 报送校验报告（全程留痕）。

## 目录结构
```
finance/
├── manifest.yaml            # 市场包 + scenario + resources（provision 输入）
├── README.md                # 本文件
├── acceptance.md            # 验收标准 + 成功度量（给客户/评估方）
├── skills/
│   ├── research-report-summary/SKILL.md     # 研报摘要与问答
│   ├── compliance-clause-match/SKILL.md    # 合规条款比对
│   └── regulatory-filing-check/SKILL.md    # 监管报送核对
├── knowledge/seed/          # 知识库种子（监管法规摘要 / 内部合规制度）
├── mcp/regulatory-filing-connector.yaml   # 报送系统连接器（4 个工具）
└── agent/playbook.yaml      # 智能合规助手剧本（默认资源接线 + 场景流）
```

## 三个核心技能
1. **研报摘要与问答**：素材 → 执行摘要 + 关键数据抽取 + 口径问答 + 红线预警。
2. **合规条款比对**：材料 → 逐条比对制度/红线 → 风险分级（红线/限用/提示）+ 修改建议。
3. **监管报送核对**：经连接器核对报表口径、缺失项、勾稽异常 → 报送校验报告 + 草稿。

## 如何跑
```bash
# 校验骨架合法性
python ../validate_poc.py

# 干跑：查看将产生的 API 调用
python ../provision.py --poc finance --dry-run

# 真实铺包（替换真实报送凭证与模型后）
python ../provision.py --poc finance --apply \
    --gateway-url http://<gateway> --token $WB_TOKEN --tenant-id $WB_TENANT
```

## 交付后
通过验收后，把 `manifest.yaml` 直发 `POST /api/marketplace/packages` 即可作为 `expert` 包上架生态市场，
供同行业其他租户「一键获取」（见阶段 4 ② 生态市场）。
