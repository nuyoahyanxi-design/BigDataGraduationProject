# OULAD 数据来源与引用

## 当前状态与使用口径（2026-10-24整理）

截至2026-10-24，当前代码基线为 ca697535d3f6903785aa63838da5083346dacc97，认证和部分界面改动仍在工作区，尚未提交，也未创建新的冻结标签。当前平台源批次为 20261024T054843Z_de437452。正式范围为已发布、含章节、非验收且未隐藏的5门课程；DWS为任务内逻辑聚合职责，Spark为local[2]离线处理。以下原始内容保留当时的设计、授权边界和验证数字；其中“本轮”“尚未”“等待确认”只指原阶段，不代表本次整理或当前状态。

原始ZIP已完整下载及核验，并已用于独立分析及看板展示，证据分别为 ../outputs/public-education-data-acceptance-report.md 与 ../outputs/oulad-analysis-acceptance-report.md。数据DOI、许可和历史年代保持原样，不将旧数据称为新采集数据。原件和派生数据继续被Git忽略；跨机器部署需另行获取并核验，提交源码不会附带数据。

## 原阶段说明（历史保留）

> 以下保留原始记录，不作为当前数字或新冻结版本的声明。答辩使用上方当前口径；历史测试结果不追写为最新结果。

- 数据集：Open University Learning Analytics dataset（OULAD）。
- 创建者：Jakub Kuzilek、Martin Hlosta、Zdenek Zdrahal。
- 存储机构：UCI Machine Learning Repository。
- DOI：https://doi.org/10.24432/C5KK69 。
- 官方页面：https://archive.ics.uci.edu/dataset/349/open+university+learning+analytics+dataset 。
- 许可：CC BY 4.0，使用和改编时须注明来源与修改。
- 说明论文：https://doi.org/10.1038/sdata.2017.171 。

## 引用格式
Kuzilek, J., Hlosta, M., & Zdrahal, Z. (2015). Open University Learning Analytics dataset [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5KK69.

## 本项目使用边界
原始文件保存于被 Git 忽略的 data/external/oulad/。数据来源是外部匿名教育环境，平台自编课程、可登录账号、收藏与章节完成保持原有含义，不与外部主体合并。保持原课程编号、原始相对日期及点击聚合定义；图表发布时须展示来源和历史数据时间，不能显示为实时业务数据。

论文文献的近期要求与数据集的采集年代是不同要求。该数据集不是2024年之后新采集的数据，不能为了满足近期文献要求修改数据年代；能否使用历史数据由任务书和导师确认。

原始数据文件下载完成和核验结果以 outputs/oulad-intake/audit.json 及阶段验收报告为准；本文件本身不代表已取得或上线数据。
