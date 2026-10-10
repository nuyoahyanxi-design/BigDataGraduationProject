# 浏览器验收报告

日期：2026-10-10；正式源批次：20261010T060537Z_fb2d2acb。
代码：19b4739598a86a2307f62b135c7d27de2b78af1e，验收结束 Git 工作区干净。

## 结论

学生及管理员指定浏览器主流程通过，可录制限定范围的系统操作演示（登录、课程正文与章节完成、画像、推荐、后台、看板）。尚不满足包含实际教学视频播放的完整演示条件。资源列表中的旧验收资源及统计文案应在录制脚本中避开或如实解释；本轮未修复。

## 范围与执行方案

沿用 docs/defense-final-acceptance-design.md 的只读验收原则，本轮以用户最新授权为准：不运行该旧方案中的 Spark 重算，不执行收藏或 AI 提问。启动现有服务，正式账号由用户手动输入密码；学生查看课程并完成一章，然后管理员只读查看管理与统计。MySQL只读事务记录前后数量，四个发布指针做SHA256比较。未创建测试账号、资源或人工插入事件；未修改业务代码、数据库结构、发布指针或旧批次。

## 服务与 API

PowerShell原启动入口被执行策略阻止，未修改策略；改用现有 scripts/start-project-service.sh，通过隐藏WSL进程启动。
后端：http://127.0.0.1:8000；前端：http://127.0.0.1:5173。服务保持运行。
FastAPI application startup complete；启动生命周期实际执行SELECT 1数据库连通性检查。
OpenAPI GET 200；前端页面GET 200；前端代理未登录GET /api/resources为401，符合权限规则。没有独立/health结果，健康判断基于启动数据库检查和可用API。

浏览器实际请求（api-access-evidence.log）：
- 两个正式账号 POST /api/auth/login、GET /api/users/me：200。
- GET /api/recommendations/me?algorithm=content_v1：200。
- 资源列表及PySpark搜索、详情、课程内容、个人进度、收藏状态读取：200。
- POST /api/resources/1069/view：200。
- 两次 POST /api/resources/1069/chapters/6/events：200。
- GET /api/admin/courses、/api/dashboard/overview、/api/admin/batches：200。

## 正式演示账号与页面

student_demo：确认learner身份；个人首页正常，首页为账户信息和推荐入口，没有直接推荐卡片。推荐页面同时展示个人画像，兴趣权重、活跃天数、行为数和截止时间正常。课程列表、搜索、1069 PySpark详情和章节学习正常。第一章DataFrame与Schema完成后，章节打勾、按钮禁用，课程进度0%→20%。
admin_demo：确认admin身份；课程管理显示5门已发布正式课程、每门5章，以及1门既有隐藏课程。数据看板四类图表加载、来源及配套批次可见。Spark批次页管道、画像、推荐、看板均为completed。仅检查查看流程，没有执行编辑、发布、下架或创建。

## 最新批次与过滤

浏览器画像：20261010T060537Z_fb2d2acb_p1_5f4a3dd7c998。
浏览器推荐：20261010T060537Z_fb2d2acb_r1_ce8dd66f8a6c5b25f9cd。
看板：20261010T060537Z_fb2d2acb_d1_170f4f800992，源批次同源。
四个latest指针与正式发布最终校验记录SHA256全部一致，见pointer-checks.json。
学生内容推荐只显示1069 PySpark、1071 MySQL、1070 Hadoop三项；数据库原有已完成资源2、5、406、1068、1072均未出现，完成过滤通过。本轮浏览器只检查content_v1，没有重复宣称popular_v1为本轮浏览器通过。
本轮新行为在发布截止时间后，离线画像与推荐仍使用正式快照，未运行Spark，因此不应实时更新画像数字。

## 数据增量与边界

基线采集发生在推荐及列表查看后、资源详情前：learning_events90，chapter_events65。
最终：learning_events91，chapter_events67；新增资源浏览1条（ID2736，UUIDv4，学生134、资源1069、有效），章节浏览1条（ID776）和章节完成1条（ID777，章6）。
users6、resources13、course_chapters26、learning_progress11、chapter_progress17、favorites3、user_profiles34、recommendation_results436、ai_qa_records50、ai_course_contexts25数量保持一致。章节进度为已有行更新，不能将数量不变误认为没有学习更新。
本课程资源级旧状态已是in_progress；本轮只完成一章，未完成整门课程，因此没有新增资源级learning_complete或UUIDv5桥接事件。本轮不能作为新UUIDv5事件端到端重算证据；既有隔离和正式批次验证另见正式发布报告。

## 已发现问题与限制

1. 教学视频未提供：页面明确显示无法播放，不能演示实际视频学习或AI视频课程成品。
2. 正式学生资源列表仍含6项旧“数据库验收资源”；管理员列表还有既有联调资源406。此次没有新增这些数据，也未删除或隐藏它们。
3. 看板资源分类副标题称“ODS.resources · 仅快照已发布资源”，而顶部实际来源说明为current MySQL；统计口径文案不一致。
4. Spark批次页数据管道生成时间及画像快照截止显示未记录；不影响本轮对应批次读取，但元数据展示不完整。
5. 1069详情初始章节进度未开始0%，而旧learning_progress资源状态已为in_progress；说明章节进度与既有资源级历史状态口径不同，录制应说明章节进度，勿称数据完全一致。
6. 本轮没有验证全课程完成、视频播放、AI回答正确性、算法效果评测；没有重新跑Spark或以浏览器验收代替算法验证。

## 截图与证据

目录：D:\BigDataGraduationProject\outputs\post-release-browser-acceptance\
- student-home.jpg：学生账号与首页。
- student-recommendations.jpg：最新推荐与画像。
- student-resources.jpg：完整资源列表。
- course-detail.jpg：课程详情。
- course-learning.jpg：课程学习及缺失视频提示。
- chapter-completed.jpg：章节完成20%。
- admin-home.jpg：管理员身份。
- admin-courses.jpg：课程管理。
- admin-dashboard.jpg：看板与推荐统计。
- admin-batches.jpg：四阶段正式批次。

API访问证据、baseline.json、final-database.json、pointer-checks.json及页面文本快照同目录。sha256.json记录证据文件哈希。

下一步：可录制上述限定主流程；若要求完整含视频的演示，应先另行授权处理视频资源与展示文案。当前验收阶段结束，不自动修改或进入开发。
