# 治理与贡献者激励

WorkBuddy Enterprise 采用**开放治理（Open Governance）**：任何人或组织都可以贡献，贡献越多、越持续，获得的信任与权益越高。本页是贡献者分级与激励的权威说明，也是 [`CONTRIBUTING.md`](../community/contributing.md) 的配套文档。

## 一、贡献者分级

| 等级 | 称号 | 认定标准 | 权益 |
|---|---|---|---|
| L0 | 👋 Contributor（贡献者） | 合并过任意 1 个 PR（文档 / 代码 / 示例均可） | 署名进入 [`CONTRIBUTORS`](https://github.com/iduyuhe/workbuddy-enterprise/graphs/contributors)；PR 进入优先评审队列 |
| L1 | 🥈 Member（成员） | 合并 ≥ 5 个 PR，或持续贡献 ≥ 3 个月 | 可认领 `help wanted` 任务；GitHub Team 成员；参与路线图投票 |
| L2 | 🥇 Maintainer（维护者） | 负责 ≥ 1 个模块（服务 / 文档 / 市场包），通过现有 Maintainer 提名 | 拥有对应模块合并权限；参与发布决策；代表项目对外技术布道 |
| L3 | 🏅 Emeritus（荣誉退休） | 曾为 Maintainer，因客观原因暂停活跃 | 保留顾问身份与荣誉署名；重大决策可受邀评议 |

> 提名与晋升由现有 Maintainer 在每月例会上评议，公开记录在 [`GOVERNANCE` 讨论区](https://github.com/iduyuhe/workbuddy-enterprise/discussions)。所有等级仅看**持续且可验证**的贡献，不设门槛费、不要求公司背书。

## 二、如何认领任务

1. 在 Issues 中筛选带标签的任务：
   - `good first issue` —— 适合新贡献者的小任务（文档、示例、单测）。
   - `help wanted` —— 需要社区力量的中等任务（某服务功能、连接器）。
   - `docs` / `examples` —— 文档与示例库相关。
2. 在 Issue 下留言 **"I'd like to take this"**，Maintainer 会在 48 小时内确认并把你加为 Assignee。
3. 按 [`CONTRIBUTING.md`](../community/contributing.md) 流程开分支、提交、提 PR，关联该 Issue。

## 三、激励体系

我们坚信**公开认可**是最好的长期激励。贡献者将获得：

- **🏷 署名与徽章**：每次合并进入 `CONTRIBUTORS`；年度活跃贡献者获得仓库 `README` 与文档站的「贡献者墙」展示。
- **🗳 路线图投票权**：L1+ 贡献者可对[下一阶段路线图](roadmap.md)提案投票，直接影响产品方向。
- **📣 布道机会**：优秀的市场包 / 示例 / 技术方案，经作者同意后在「工业 5.0 产业生态联盟」公众号与社区活动署名转载。
- **🎁 年度贡献者榜单**：每年评选 Top Contributor / Top Doc / Top Example，颁发电子证书与联盟生态权益（培训、共建名额优先）。
- **🤝 共建邀约**：持续高质量的 L2 贡献者，可受邀成为生态共建伙伴，参与标杆客户 POC 与商业化分成讨论。

## 四、决策原则

- **默认透明**：路线图、治理变更、Release 计划均在 GitHub 公开讨论。
- **懒惰共识（Lazy Consensus）**：无反对即通过在研议题；重大变更（架构、许可证、治理规则）需 ≥ 2 名 Maintainer 明确 +1。
- **安全第一**：任何涉及凭证、数据出域、等保合规的改动，须走安全评审（见仓库 `SECURITY.md`）。

## 五、变更本治理文档

修改本文档须提 PR 并在 [`GOVERNANCE` 讨论区](https://github.com/iduyuhe/workbuddy-enterprise/discussions) 公示 ≥ 5 天，获得 ≥ 2 名 Maintainer +1 后合并。
