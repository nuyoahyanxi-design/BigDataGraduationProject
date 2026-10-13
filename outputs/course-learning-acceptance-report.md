# 课程章节与视频学习模块验收报告

> 历史资料说明（2026-10-13补注）：下文设计、数量、失败与未验收结论属于原记录日期，不代表当前版本；保留原始证据，不将当时未执行的测试改写为通过。 当前技术栈、视频播放证据和各数据口径统一见[答辩当前状态说明](../docs/defense-current-state.md)；本次仅修订文档，没有重新验收或运行Spark。

日期：2026-10-05。实现、迁移和种子初始化完成；正式8000服务尚未重启加载新路由，真实浏览器课程操作未验收。真实视频未提供。不要将此报告理解为正式环境已完成视频播放验收。

## 1. 本阶段实际完成

新增章节学习页面/resources/:id/learn、章节目录、HTML5视频播放器与安全Markdown内容展示。资源详情开始学习改为导航，不直接更新状态；章节访问产生学习开始，全部章完成自动完成课程。收藏入口和原事件历史保留。

三个已有已发布资源复用：1068 Spark RDD基础教程、1069 PySpark数据处理实践、1072 Python机器学习基础；各5章，共15章，包含标题、排序、教学文本、知识标签和该阶段的媒体示例地址。没有删除、改写旧资源正文、账号密码或已有行为数据。

视频统一/videos/demo.mp4，未生成视频文件。播放器支持原生播放/暂停、当前时间、ended检测和加载失败提示。实际视频不存在时可阅读并手动完成，不将其宣称为真实观看；元数据时长未知为null。章节完成不代表学习能力。

## 2. 数据库迁移结果

005_create_course_learning.sql实际执行成功，新表course_chapters、chapter_progress、chapter_events。InnoDB、utf8mb4_unicode_ci，主外键和索引已通过反射记录，复合章节/资源外键阻止错误关联，UUID唯一，章节顺序唯一。原五表字段未改。

迁移前后核心数量相同：users6、resources12、learning_events27、learning_progress6、favorites2。最终审计仍为上述数量；新增章节15、章节进度0、章节事件0。正式学习者还没有通过新接口产生章节行为；自动测试事件已按独立测试账号清理。

首个迁移工具执行因SQL注释内分号被拆分而失败，在首个CREATE前未建表。修正工具过滤整行SQL注释后执行成功，无删表重跑。DDL无法整体事务回滚，工具拒绝已存在目标表，当前不要重复执行CREATE。

种子通过现有active admin_demo与隔离TestClient认证的正式章节路由创建，不直接INSERT，不修改生产JWT或密码。重跑工具返回同15个章节ID，没有重复添加。迁移与回退说明已补充database/README.md；不自动DROP含记录的表。

## 3. API与权限

|接口|用途|权限|
|---|---|---|
|GET /api/resources/{id}/course|课程、章节、视频、自己的章节完成状态|登录；学习者只读已发布|
|POST /api/resources/{id}/chapters|追加章节|管理员；已有人开始章节学习则冻结目录|
|POST /api/resources/{id}/chapters/{chapter_id}/events|chapter_view/video_play/chapter_complete|登录、已发布、当前用户|
|GET /api/users/me/chapter-events|分页个人章节事件|登录，不接受他人身份|

事件请求包含event_uuid(UUID4)、event_type、可选playback_seconds（仅video_play）。UUID与语义指纹保证重复返回原回执，冲突409；完成重复操作is_effective=0。

状态更新、章节事件、原课程级start/complete桥接同一事务，用户锁串行保证并发最后章节只触发一次课程完成。桥接仍使用原learning_start/learning_complete，不改旧表CHECK或Spark事件白名单。

唯一必要的旧学习逻辑增量：原complete接口对拥有章节、尚未完成的课程检查全部章节完成，防绕过。无章节资源保持原逻辑，旧已完成状态和UUID回执不降级、不清除。页面分别展示历史课程状态与新章节完成比例。

## 4. 自动验证

|检查|结果|证据|
|---|---|---|
|后端全量|236通过、1弃用警告；原222项+新14项|course-learning-backend-tests.log/xml|
|前端完整测试|68全部通过，11文件通过，无跳过|course-learning-frontend-tests.log|
|类型检查|通过|course-learning-typecheck.log；build也再次包含vue-tsc|
|生产构建|通过，原看板大包警告仍在|course-learning-build.log|
|隔离真实Uvicorn|新路由加载，前端12项集成测试实际请求通过|18765临时测试服务，已关闭|
|种子重复执行|仍为3课程/15章|course-learning-seed-report.json、final-data-verification.json|
|事务失败|开始桥接或最终完成桥接写入失败后整体回滚|新后端测试|
|权限/完整性|匿名401、普通用户新增403、错误章节关联404、下架拒绝、非法路径422|新后端测试|
|幂等/并发|UUID重放原回执、语义冲突409、最后章节并发仅一次课程完成|新后端测试|
|视频与Markdown|时间/结束状态、安全本地地址、文本转义、控件、空视频回退、章节导航|7项新前端测试|

首轮前端运行56通过/12跳过，后续设置AUTH_API_TARGET至隔离新后端后68全部通过。旧资源集成测试选择无章节资源以验证兼容路径；有章节的完成规则由新后端测试覆盖，不绕过课程门禁。

首轮旧后端启动测试因固定路由集合缺4个新增路径而失败，更新准确期望清单后通过，没有放宽断言或跳过测试。前端一条SSR代码标签断言改为允许Vue scoped属性，保持正文与安全验证。

测试临时账号只在内存生成密码；清理限定测试账号及其行，没有清理既有演示账号/行为。course-learning-test-cleanup.json记录前后相同；最终只读审计证明旧核心数量保留。

## 5. Spark兼容验证与既有问题

未修改spark/任何任务或算法。首次附加Spark回归43通过、5错误：旧快照推荐包含当前已完成资源，被既有过期保护拒绝。这说明源快照需更新，不删除保护。

重新冻结后原四段任务首次发布成功；同批次重复测试又发现已有画像精确JSON比较问题：MySQL权重0.3758064516129032，Parquet0.37580645161290316；另有0.2307692307692308/0.23076923076923078。差异接近浮点末位，但被原immutable检查拒绝。第二次附加Spark回归42通过、1失败、5错误。不能报告全部Spark测试通过。

证据course-learning-profile-conflict-diagnosis.json、course-learning-spark-tests.log/xml与stale-snapshot.log。该问题不在本次授权修复范围，未改变Spark精度、比较规则或旧画像记录。

重复测试把该尝试批次manifest停在prepared；随后重新冻结并发布完整新批次，恢复最新可用四段结果，不手工修改失败manifest。

最终发布成功：

- source：20261005T102319Z_fdb1d523。
- profiles：20261005T102319Z_fdb1d523_p1_338342c9c5d6。
- recommendations：20261005T102319Z_fdb1d523_r1_8c9946c778bddce8435d。
- dashboard：20261005T102319Z_fdb1d523_d1_9cc625c451c0。

4学习者、6合格候选、36条推荐。发布证据course-learning-publication.json/log。业务课程级事件仍可被原Spark读取；章节细粒度事件尚不纳入当前分析。未来可基于chapter_events和chapter_progress计算播放次数、章节完成率；当前playback_seconds是媒体位置，不是可信学习时长，需要未来独立设计时长采集。

## 6. 修改文件清单

数据库：
- database/migrations/005_create_course_learning.sql
- database/seeds/course-chapters.json
- database/README.md

后端：
- backend/app/models/courses.py（新增）
- backend/app/models/__init__.py（注册模型）
- backend/app/schemas/courses.py（新增）
- backend/app/services/courses.py（新增）
- backend/app/api/courses.py（新增）
- backend/app/main.py（注册路由）
- backend/app/services/learning.py（必要章节完成门禁）
- backend/tools/apply_course_migration.py、seed_course_chapters.py（新增）
- backend/tests/test_courses.py（新增）、test_foundation.py（准确路由清单）

前端：
- frontend/src/types/courses.ts、api/courses.ts（新增）
- frontend/src/services/markdown-learning.ts、video-learning.ts（新增）
- frontend/src/components/ChapterNavigation.vue、LearningVideo.vue、LearningMarkdown.vue（新增）
- frontend/src/views/CourseLearningView.vue（新增）
- frontend/src/views/ResourceDetailView.vue（学习导航）
- frontend/src/router/index.ts（新增认证路由）
- frontend/tests/courses.test.ts（新增）、resources.integration.test.ts（旧资源兼容测试选取）
- frontend/public/videos/README.md（无视频文件）

设计与验收：docs/course-learning-design.md、本报告。outputs内另有种子准备、只读核对、隔离测试启动、既有任务发布及冲突诊断辅助脚本和日志，不属于新增业务模块。

## 7. 如何启动验证

当前8000运行的是旧进程，OpenAPI尚无新/course路由。已请求用户在原安全终端重启，未收到完成消息；未终止或读取其Agnes Key。隔离18765测试进程已关闭，不替代正式服务。

在WSL使用原虚拟环境：

```bash
source /mnt/d/BigDataGraduationProject/environments/activate-bigdata.sh
cd /mnt/d/BigDataGraduationProject/backend
PYTHONPATH=. python ../outputs/start-ai-real-model-secure.py
```

先在原后端终端Ctrl+C退出旧8000，再执行原安全启动命令；环境变量缺少时手动输入，不写文件。若原启动方式不同，以原已验证方式为准。无需重复迁移005。前端现有Vite可热更新；另起时：

```bash
cd /mnt/d/BigDataGraduationProject/frontend
API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev -- --host 0.0.0.0
```

访问正式http://localhost:5173，登录后打开/resources/1068/learn（1069、1072同样支持），核对5章、正文、缺视频提示、章节完成。旧已完成账号保持原课程完成；测试自动完成桥接须选择未完成此课程的学习者，可通过现有注册API创建并手动保存密码。

真实播放须自行将有权使用的MP4放frontend/public/videos/demo.mp4；本轮未生成、下载或伪造视频。所有章完成后核对旧learning_events及新chapter-events，再运行原四段任务进行分析；不要把同批次画像重发通过视为已解决。

## 8. 当前限制和阶段结论

实现与数据库初始化完成，要求的后端/前端/类型/构建验证通过。正式服务待安全重启，真实浏览器课程流程与实际视频播放待验证。没有实现AI自动视频生成、管理员章节编辑页面、强制观看、可信时长或新推荐算法。

Spark正常新批次发布成功，但附加回归暴露旧画像同批次浮点比较问题，未擅自修复。建议独立授权修复该问题；课程模块当前先以独立测试证据验收。完成后停止，不自动新增后续功能。
