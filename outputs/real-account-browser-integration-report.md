# 真实账号浏览器全流程联调报告

日期：2026-10-05。状态：本轮授权的真实账号全流程浏览器联调已完成；管理员与学习者正式登录、资源学习、Spark完整链路和重算后两类账号回访通过。独立events查询接口未专项复测，详见验证边界。

## 1. 使用账号与环境

admin_demo（ID135、管理员），student_demo（ID134、学习者）。用户手工登录，密码不记录。正式系统 http://localhost:5173；FastAPI http://127.0.0.1:8000；MySQL80 8.0.45；WSL Ubuntu22.04、PySpark3.5.7。MySQL服务运行，API和Vue返回200，数据库连接正常。未使用模拟HTML页面、未修改密码或结构、未删除旧数据。

## 2. 浏览器操作与页面结果

1. 管理员登录：首页显示管理员身份；/admin 用户列表显示6个用户。
2. 正式资源表单创建“Spark 真实浏览器联调演示资源 20261005-01”，标签python、spark，自编正文，草稿ID406、版本1。
3. 正式发布确认：状态published、版本2、创建者135。
4. 切换student_demo，首页显示学习者及python/spark兴趣；刷新后仍能进入受保护资源页。
5. 资源列表7项；搜索演示标题命中1项；打开/resources/406，自动产生浏览事件。
6. 开始学习：未开始→学习中；收藏→已收藏；取消→未收藏；再次收藏→已收藏；标记完成→已完成且已收藏。所有业务请求返回HTTP200。
7. 重算前推荐页显示该用户画像尚未生成、推荐为空。重算后刷新显示行为画像与5条内容推荐、分数1及“与你的行为兴趣画像匹配：python、spark”的理由。
8. 重算后学习者重新登录，推荐和学习状态持久化通过；管理员重新登录，Dashboard、Spark批次、用户列表及资源状态通过。

## 3. 数据库变化与真实接口证据

|表|联调前|学习操作后|Spark后|
|---|---:|---:|---:|
|users|6|6|6|
|resources|6|7|7|
|learning_progress|1|2|2|
|favorites|0|1|1|
|learning_events|6|13|13|
|user_profiles|6|6|10|
|recommendation_results|90|90|130|

student_demo事件ID339–344：resource_view、learning_start、favorite_add、favorite_remove、favorite_add、learning_complete，六条均is_effective=1且event_uuid不同。进度406为completed，开始04:29:58.813 UTC、完成04:30:21.343 UTC；最终favorites存在406。旧dbstage_user账号状态和updated_at与基线一致。

事件总增量7中，6条为本次学习者操作；另1条是admin_demo于04:24:58 UTC浏览旧资源6（ID338），不归入本次学习者动作，数据库审计有明确记录，不猜测其操作来源。

浏览器实际调用GET /api/users/me/progress与GET /api/users/me/favorites均返回200，页面状态与数据库一致。学习事件通过实际写入及只读数据库核对；本轮尚未单独调用GET /api/users/me/events，不将其写为已验证。

证据：real-integration-before-database.json、real-integration-after-browser-database.json、real-integration-after-spark-database.json、real-integration-all-event-audit.json、real-integration-backend.log。

## 4. Spark批次结果

暂停页面行为写入后，顺序执行现有python -m spark.jobs.pipeline、user_profiles、recommendations、dashboard_metrics，整体退出码0，无算法改动。

|任务|新批次|结果|
|---|---|---|
|pipeline|20261005T043104Z_05387fdc|ODS五表快照；事件输入13，过滤无状态变化1，DWD12；Spark SQL、Parquet回读、校验和通过|
|user_profiles|20261005T043104Z_05387fdc_p1_338342c9c5d6|4份学习者画像，Parquet和MySQL发布通过|
|recommendations|20261005T043104Z_05387fdc_r1_3de476e3e9a5f6bc9fee|popular_v1/content_v1，Top5，共40条；Parquet和MySQL发布通过|
|dashboard_metrics|20261005T043104Z_05387fdc_d1_6ac78a86e6f0|看板发布completed；同源批次可追溯|

student_demo画像：浏览1、开始1、完成1、收藏2、取消1；活跃1天；Python/Spark各50%；开始1项、完成1项，流程完成率100%，不代表学习能力。

看板快照：用户6，活跃学习者4，管理员2；已发布资源7；有效学习者行为11；已开始2项、已完成2项。DWD12含管理员浏览1条，而看板统计11为学习者口径，两者不同并非丢失学习者事件。生成时间04:32:29.630 UTC。

## 5. 推荐变化

student_demo从无画像、无推荐变为行为画像和5条content_v1推荐，资源1–5，分数均1，具有明确理由；完成的406不在推荐中。现存资源标签相近，不以相同分数证明算法效果提升。新批次推荐整体40条，旧批次结果保留，数据库累计130条。

## 6. 截图编号

00登录准备；01管理员首页；02管理员用户；03新资源草稿；04发布成功；05学习者首页刷新；06标题搜索；07学习中；08a首次收藏；08b取消收藏；09已完成且已收藏；10a重算前推荐为空；10b重算后画像与推荐。文件均位于outputs，前缀real-integration-。重新登录和管理员最终回访截图见下方完整索引。

## 7. 问题、限制与待完成

发布点击遇到一次工具瞬时节点失效，重新观察后成功；发布成功等待文案与实际文案不同导致一次等待超时，页面已明确显示成功，没有重复创建或重复发布。

数据来源仍混合开发验收种子与本次演示行为，不是教学研究样本，不能据此宣称推荐效果提升。账号密码由用户掌握，每次账号切换需手工登录，不读取浏览器Token或密码。

本轮流程已完成。保留FastAPI与Vue运行及正式看板页用于用户查看，本阶段停止，不进入AI问答或其他功能开发。

## 8. 重算后学习者重新登录验收（已通过）

用户手工重新登录student_demo，正式首页显示学习者身份。进入/recommendations，确认新批次画像、5条内容推荐及理由仍正常展示；资源406未被推荐。再次打开/resources/406，确认学习状态为已完成、收藏状态为已收藏，持久化通过。截图11：real-integration-11-student-relogin-recommendations.jpg；截图12：real-integration-12-student-relogin-progress.jpg。

详情回访会按正式页面设计新增一条resource_view事件，该事件发生于Spark快照之后，未纳入本次已发布画像和看板；不能据此认为离线统计实时包含回访行为。原6条动作及最终进度/收藏保持。

学习者回访后已退出；用户已手工重新登录admin_demo，管理员最终回访完成，详见第9节。

## 9. 管理员最终回访与最终结果

正式首页确认admin_demo管理员身份。/dashboard显示20261005T043104Z_05387fdc_d1_6ac78a86e6f0，来源与快照截止可追溯；4个ECharts canvas均有非零尺寸，实际截图确认趋势折线、资源分类环图、完成情况环图、推荐统计柱图均已绘制。

/admin的Spark批次显示数据管道、画像、推荐、看板四阶段completed，分别12条清洗事件、4份画像、40条推荐、30天趋势。用户列表显示6用户且两演示账号active；资源406状态已发布、版本2，已有6资源仍已发布。

实际GET /api/dashboard/overview、GET /api/admin/batches、GET /api/admin/users、管理员资源列表均返回200。没有新增业务代码、数据库迁移、账号密码修改或删除既有数据。

新增展示限制：pipeline的latest元数据没有generated_at，批次页显示生成时间“未记录”及“旧管道产物未记录生成时间”，即使本次为新跑批仍出现该提示。真实快照截止仍有记录。画像批次列表也显示快照截止“未记录”，但推荐页和配套源批次可追溯；本轮只记录问题，不跨范围修改实现。

最终只读证据real-integration-final-database.json：users6、resources7、learning_progress2、favorites1、learning_events14、user_profiles10、recommendation_results130。student_demo最终有7条事件（原6动作+重算后详情回访浏览1），完成状态和收藏不变。回访事件发生在04:31:05.298 UTC快照之后，下次重算才进入统计；本次画像仍为浏览1，其余动作不变，属于正常离线时效边界。

## 10. 完整截图索引

|编号|文件|结果|
|---|---|---|
|00|real-integration-00-login.jpg|正式登录准备|
|01|real-integration-01-admin-home.jpg|管理员身份|
|02|real-integration-02-admin-users.jpg|首次用户列表|
|03|real-integration-03-resource-draft.jpg|406草稿|
|04|real-integration-04-resource-published.jpg|406发布|
|05|real-integration-05-student-home.jpg|学习者首页|
|06|real-integration-06-resource-search.jpg|搜索命中1项|
|07|real-integration-07-learning-started.jpg|学习中|
|08a|real-integration-08a-favorite-added.jpg|首次收藏|
|08b|real-integration-08b-favorite-removed.jpg|取消收藏|
|09|real-integration-09-learning-completed.jpg|完成且收藏|
|10a|real-integration-10a-recommendation-before.jpg|重算前为空|
|10b|real-integration-10b-recommendation-after.jpg|重算后画像推荐|
|11|real-integration-11-student-relogin-recommendations.jpg|重新登录推荐|
|12|real-integration-12-student-relogin-progress.jpg|重新登录学习状态|
|13|real-integration-13-admin-dashboard.jpg|真实四图表及批次|
|14|real-integration-14-admin-batches.jpg|四阶段completed|
|15|real-integration-15-admin-users-final.jpg|最终用户列表|
|16|real-integration-16-admin-resource-final.jpg|最终资源状态|

截图来自正式系统，未记录密码或Token。截图在当前窄侧栏视口采集，长页面和批次编号有换行；答辩展示宜使用宽桌面窗口重新截图。验收不等于真实教学效果实验，现有样本规模和标签同质性限制继续保留。