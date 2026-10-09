# 数据分析看板设计

日期：2026-10-05。范围为答辩用只读统计接口和 ECharts 页面，不开发CRUD、AI、ALS或新算法。

## 数据来源与口径

已检查当前七张数据库表及Spark产物：没有daily_metrics表。新增仅统计聚合的Spark任务，从现有已完成并校验文件哈希的ODS users/resources/learning_progress和DWD learning_events生成daily_metrics Parquet及聚合JSON，不增加数据库表或改变推荐算法。默认与现有推荐发布指针的source_batch_id对应；配套画像和推荐批次一并固定在看板产物中，不混读新旧指针。

用户统计为快照用户总数、活跃学习者数和管理员数。资源统计为资源总数、已发布数量及已发布资源分类分布。行为趋势为统计截止北京时间自然日前30天的有效学习者事件，Spark按日期及五种类型聚合，并补零；不以请求当天滚动窗口替代冻结截止。学习完成情况只统计活跃学习者在ODS中已开始的进度记录，completed / (in_progress + completed)，分母为空为null，不推断未开始组合或学习能力。

每日指标由Spark计算，Parquet读回比对；汇总JSON包括相同窗口趋势、全快照有效事件数、清洗输入/输出/过滤数量、来源和截止。结果路径data/ads/daily_metrics/batch_id=...，发布outputs/dashboard-latest.json。批次含源批次及计算代码摘要；同批次重跑保持生成时间并核对数据，冲突拒绝，不覆盖已成功结果。最新指针原子替换，服务不启动Spark。

后端只在配套profile_batch_id与recommendation_batch_id内聚合user_profiles覆盖用户和证据来源、recommendation_results各算法行数/用户数/不同资源数。推荐统计为离线发布行，不当作当前在线可展示条数或Coverage实验指标。无配套推荐则显示未生成，不用其他批次补齐。缺少看板产物返回友好空数据；损坏或未完成返回503，不伪造0。

## API、权限与模型

新增GET /api/dashboard/overview。复用require_admin；无身份401，学习者403，管理员只读。拒绝额外user_id/batch参数。不输出用户身份、密码、Token、推荐明细或物理路径。响应包含available、data（generated_at、batch_id、source_batch_id、as_of_utc、source、metrics及配套批次）、profiles、recommendations及message。不同统计区块标明来源，时间显式UTC；日趋势的业务时区明确Asia/Shanghai。

不新增DDL或ORM表。DASHBOARD_MANIFEST_PATH可配置结果文件，默认项目outputs/dashboard-latest.json。文件包含内容SHA256并在请求时核对，防止未完成文件被当作成功产物；部署时保持文件和MySQL配套批次一致。

## 前端

新增管理员保护/dashboard。导航仅管理员显示入口，学习者直接访问跳首页并提示权限。通用EChart组件使用ECharts按需注册、canvas渲染，ResizeObserver自适应并在卸载dispose；响应数据已经聚合，前端只映射图表字段，不计算业务统计或比例。

展示用户/资源摘要、每日行为趋势、分类分布、已开始学习完成情况、各算法推荐条数及Spark批次信息。无数据单独友好提示，失败支持重试。推荐分数和实验效果不新增推断。显示数据更新时间、源截止、批次、各区块来源和数据原始性质，明确开发验收样本不是真实用户研究。

## 验证与阶段门禁

Spark测试验证时区、窗口边界、空数据、聚合和重跑；实际任务读取已有冻结Parquet并保存数量和读回证据。后端验证401/403/管理员200、缺失产物、损坏哈希、未完成状态、批次限定和空数据。前端类型/构建、路由/API/图表映射测试；浏览器独立模拟入口验证实际ECharts canvas及空提示，不冒充真实账号端到端。分别记录真实产物、真实API与模拟组件证据。完成docs/dashboard-design.md和outputs/dashboard-acceptance-report.md后停止。
# 实施补充与验证边界（2026-10-05）

已采用daily_metrics Parquet发布，无数据库新增迁移。页面兼容历史无时区时间字段：统一按UTC解释并标记UTC；趋势自然日使用Asia/Shanghai。统计查询只读且仅管理员授权。浏览器组件验收采用模拟身份及冻结快照的隔离测试入口；真实Spark与MySQL结果另由后端测试验证，尚未执行真实管理员浏览器登录端到端测试。
