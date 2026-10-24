# 统一课程进度口径验收报告

日期：2026-10-24。状态：实施、发布与双端页面检查完成，等待人工验收。未提交Git。

## 修复规则
有章节课程：无章节进度记录为未开始；有开始记录且未全完成为学习中；所有章节completed_at非空才为已完成。完成率独立按完成章数/总章数计算，因此学习中可以为0%。无章节资源沿用资源级进度。

历史learning_progress、learning_events及旧批次不覆盖；章节课程当前状态和完成时间从章节记录派生。用户画像的历史完成操作次数继续显示，但不再被当作当前已完成资源数；开始/完成的兴趣贡献、推荐个人行为/资源热度和完成过滤使用统一当前进度。没有补造完成状态、完成时间或事件。

## 本轮代码
- backend/app/services/course_presentation.py：统一状态、首次开始/当前完成/更新时间派生。
- backend/app/services/courses.py：章节响应started；0章完成但已开始返回学习中。
- backend/app/services/learning.py：旧completed也不能绕过全章完成校验；进度查询返回派生时间。
- frontend/src/types/courses.ts、CourseLearningView.vue：started+completed统一判断，章节操作回执同步状态。
- frontend/src/views/RecommendationsView.vue：明确历史操作与当前完成数区别。
- spark/utils/progress.py（新增）：独立统一进度生成/读取，校验章节关联与时间。
- spark/utils/profiles.py、recommendations.py：当前完成统计和评分使用统一进度，历史事件计数保留。
- spark/jobs/clean.py、quality.py、user_profiles.py、recommendations.py、dashboard_metrics.py：DWD effective_progress及发布接入；推荐发布前也按当前章节完成状态核对，避免旧资源状态误拦截。
- tests/test_unified_progress.py（新增）、frontend/tests/courses.test.ts：隔离回归。

## 实际运行
源批次：20261024T052926Z_b70b43da。
画像：20261024T052926Z_b70b43da_p1_0e530226b770。
推荐：20261024T052926Z_b70b43da_r1_6b54d84f49ce7cb043a7。
看板：20261024T052926Z_b70b43da_d1_41014a203a55。

Spark 3.5.7、local[2]，DWS仍为逻辑聚合。快照UTC 2026-10-24 05:29:26，即北京时间13:29:26（此处按秒展示）。画像、推荐、看板最终任务退出码均0，MySQL发布与Parquet往返通过，批次关联一致。

首次画像运行因局部DataFrame变量名遮蔽JSON序列化函数而停止；已修正，保留日志。没有发布失败画像或覆盖旧画像/推荐/看板；源pipeline指针已在其成功时前移，四指针并非组原子切换。修正后复用同一新快照完成其余三个任务，不重新采集或改写原始数据。日志分别位于outputs/unified-progress/和outputs/unified-progress-final/。

## 真实核验结果
student_demo、RDD课程1068：
- 详情页：学习中、章节完成0%、按钮继续学习。
- 学习页：学习中、0%，5章均未完成。
- 在线进度查询：in_progress，当前completed_at=null。
- DWD effective_progress：in_progress，completed_at=null。
- 原始learning_progress：仍为旧completed及旧完成时间，作为历史记录完整保留。
- 推荐页面：RDD实际进入第2位，综合推荐分60%，不是准确率或预测概率。

学生画像：已开始9项、当前完成3项、完成率33.3%；历史完成操作次数仍5。平台看板：已开始10项、当前完成4项、完成率40%。两处人数范围不同；已核对全部4份画像的开始/完成数之和分别等于看板10/4。原课程级有效学习者行为129条保持独立口径。

新规则同时纠正了其他存在类似旧完成状态的章节课程，不只硬编码修RDD。当前完成数减少表示口径修正，不是删除历史完成操作。

## 测试与证据
- 初次隔离Python回归9项通过；扩展统一进度评分/候选过滤验证后，统一进度4项再次通过。SQLite与Spark内存fixture，无生产测试账户创建或完成数据写入。
- 验证无章节资源兼容、未开始、开始但0完成、全部章节完成、旧完成不绕过校验、非法章节关联/时间拒绝、历史完成次数不误作当前完成、未完成课程不被旧完成事件过滤。
- 前端最终类型检查/构建通过；172项通过、12项跳过。旧前端夹具故意返回冲突状态，初次出现2项失败；前端改为使用started+completed一致判断后全部通过。保留初次和最终日志。
- git diff --check通过（换行转换提示仍存在）。
- outputs/unified-progress-final/verification.json：在线课程/进度、当前MySQL结果、RDD快照、画像看板汇总及批次关联核对。
- outputs/unified-progress/rdd-detail.png、rdd-learning.png、student.png、dashboard.png及对应.txt：真实页面证据。

## 历史保护
outputs/unified-progress/protection-verification.json核验：
- learning_progress：12→12，原内容摘要一致。
- chapter_progress：22→22，原内容摘要一致，无新增章节完成。
- course_chapters：26→26，完整记录摘要一致（含视频/章节绑定）。
- learning_events：140→141；原140条内容摘要一致。
- chapter_events：269→270；原269条内容摘要一致。
- 新增两条来自最终浏览器验收：资源浏览、章节浏览；没有新增完成或播放事件。发生在快照之后，按离线口径未计入本批次。
- 25个正式MP4逐文件SHA256一致。

旧四份latest原字节备份在outputs/unified-progress/pre-release/；旧ODS/DWD/ADS文件按原manifest摘要验证通过，旧画像4行、推荐36行仍在MySQL。证据见old-batches-verification.json。所有业务源码与最终发布前记录的摘要一致。

## 边界
不修改数据库表结构、历史进度、视频或章节绑定；不提交Git；保留其他既有修改。仅正常Spark发布向画像/推荐结果表新增批次，切换相应发布指针。没有对真实RDD点击完成按钮；全章完成分支通过隔离fixture验证。结果仍是演示/验收数据，未声称学习效果或性能提升。
