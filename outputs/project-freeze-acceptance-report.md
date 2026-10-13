# 项目冻结与最终验收准备报告

> 历史资料说明（2026-10-13补注）：下文设计、数量、失败与未验收结论属于原记录日期，不代表当前版本；保留原始证据，不将当时未执行的测试改写为通过。 当前技术栈、视频播放证据和各数据口径统一见[答辩当前状态说明](../docs/defense-current-state.md)；本次仅修订文档，没有重新验收或运行Spark。

日期：2026-10-05。结论：测试与文档准备完成，可冻结新功能；存在Spark发布回归阻断和最终人工演示待验项，不能签署全系统全部通过。

## 实际完成与修改清单

1. backend/tests/test_course_ai.py：新增4项验收用例（课程/通用两种模式匿名拒绝，未授权课程不调用供应商且不写问答，问答不产生学习事件且引用与实际上下文一致）。没有修改业务代码。
2. docs/project-freeze-acceptance-design.md：阶段方案及证据边界。
3. docs/final-project-acceptance-guide.md：当前功能清单、12表/技术架构、AI/Spark说明、工程创新点、8–12分钟演示与截图清单、冻结规则。
4. docs/system-final-architecture.md：增加当前基线入口，明确旧七表/纯余弦快照已过时，保留历史记录。
5. README.md：加入冻结验收与答辩文档入口，提示未通过项。
6. outputs/project-freeze-acceptance-report.md：本报告；测试日志/XML、数据前后摘要/核验文件及失败manifest备份为验收附件。
7. work/project-freeze-before.py、work/project-freeze-after.py：只读摘要辅助工具。

运行恢复：data/ads/user_profiles中既有当前画像manifest在失败回归测试中变为prepared；核对其batch_id、content_sha256、generated_at与既有completed latest完全一致后，恢复为该原成功发布元数据。失败manifest保存outputs/project-freeze-profile-manifest-failed.json。没有改数据库、Parquet或任务逻辑；恢复不是新批次发布。

## 完整链路检查结果

|环节|本轮证据|结论|
|---|---|---|
|管理员创建课程/章节与发布|test_admin_courses/test_courses/test_course_ai中真实API临时资源|通过；不改正式课程|
|学生章节学习与完成|test_full_chapter_flow_and_legacy_bridge、事务/幂等/身份测试|通过；课程桥接start/complete|
|课程AI与通用AI|真实FastAPI/数据库，供应商受控替身|契约通过，未再次真实调用Agnes|
|真实引用|检索上下文、数据库元数据、历史及前端引用测试|通过；不存在章节不伪造来源|
|学习行为记录|章节事件与传统事件测试，新增AI不产生日志断言|通过|
|Spark计算/展示|Spark全套48用例、后端看板/前端统计测试|42项通过，6项发布相关未通过；不认定全链路通过|

上述是分模块/接口组合证据，不是同一正式账号在浏览器一次连续运行。本轮未自动操作浏览器、创建正式课程或发送真实模型问题。AI不能替代学习行为；chapter_events不直接输入当前五表Spark抽取，只有课程开始/完成桥接事件进入现有链路。

## 测试结果

|检查|真实结果|日志|
|---|---|---|
|后端pytest tests -q|376 passed，22.02秒，1项已有Starlette弃用警告|project-freeze-backend-tests.log/.xml|
|前端首次全套|158 passed，1项路由加载30秒超时|project-freeze-frontend-tests.log|
|前端减少并发重跑|22文件159 passed，无跳过，83.20秒|project-freeze-frontend-retest.log|
|TypeScript|通过|project-freeze-typecheck.log|
|生产构建|通过，24.35秒；已有Dashboard>500kB提示|project-freeze-build.log|
|Spark全套|42 passed、1 failed、5 errors，133.12秒|project-freeze-spark-tests.log/.xml|
|测试清理后的数据核验|结构、章节、受保护业务数据摘要均一致|project-freeze-data-verification.json|

后端新增4项，前端复用已有课程/AI/权限/真实接口验收，没有为凑数量添加重复页面测试。Spark包含真实SparkSession、DataFrame/SQL、Parquet与算法/实验断言。失败未改成跳过或忽略，也未伪造全绿结果。

## 问题分析与最小建议

P1：test_profiles::test_real_publication_repeat重跑既有批次触发Existing profile differs; immutable batch publication rejected。随后test_recommendations的5项共享发布fixture报Incomplete profile batch。当前证据确认是既有画像重发布与数据库不可变记录不一致，尚未逐字段确认冲突内容；不能推断为推荐算法错误。应单独进行只读比较，定位时间精度/JSON/批次字段差异，同时考虑将发布测试隔离到测试批次。本阶段未修改画像或Spark。原发布元数据已恢复；不建议反复对线上latest执行同一失败测试。

P2：前端与Spark同时运行时课程路由动态加载超时，前端2 worker重跑通过。属于运行资源竞争的推断，不是已证实业务缺陷；演示前避免同时跑重型测试和Spark。无需改页面逻辑或扩大测试timeout。

人工待验：最终UI在正式localhost:5173完整操作、真实Agnes一次成功回答及真实章节引用、学生行为后暂停写入生成同源四阶段批次，再观察推荐/看板。历史浏览器报告只证明早期资源版，不替代当前课程AI版本截图。

## 冻结与答辩建议

当前功能和文档足以准备答辩材料，但最终签收需解决或明确处置P1，并完成上述真实演示。演示使用admin_demo/student_demo手动密码；Key、密码、Token不得入截图/报告。模型延迟、当时缺少真实媒体、local Spark、合成实验样本与无向量检索均如实说明。生产部署使用明确课程许可，不复制开发通配文件。

本阶段没有改AI业务、数据库结构、Spark代码、推荐、画像、学习流程及正式课程内容。已停止，等待用户确认；不继续开发功能。
