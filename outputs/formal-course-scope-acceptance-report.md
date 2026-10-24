# 正式课程统计范围与推荐名额统一验收报告

日期：2026-10-24。状态：实施、正式新批次与双端页面检查完成，等待人工验收。未提交Git。

## 统一规则与改动
正式课程定义为已发布、含章节、非验收且未隐藏的资源；不依赖旧resource_type，不硬编码1068—1072为永久白名单。验收标记沿用source_name=本项目测试且license_note=仅供开发验收；隐藏ID406沿用既有政策。backend/app/core/resource_scope.py保存共享常量，spark/utils/resource_scope.py提供快照筛选，在线SQL与Spark范围通过隔离测试核对。

- 原始MySQL、ODS/DWD和历史批次完整保留，仅在新画像、推荐、看板计算入口筛选正式课程。历史学习进度不回填、不删除。
- 画像兴趣、行为次数、章节统计、开始/完成数量均限于正式课程。正式课程完成率=已完成正式课程/已开始正式课程；未开始时为暂无，而非强制0。章节进度仍采用上阶段统一规则。
- 推荐在生成TopN之前筛选正式课程；个人行为和资源热度也使用同一范围。发布前复核，在线展示再检查当前可见性。隐藏资源不再占用名额，不是事后伪造排名补齐。
- 新看板批次的课程总数、分类、行为与学习统计使用同一冻结快照，不再用当前MySQL目录覆盖其中部分字段。旧批次缺少范围标签时保持兼容，完成率名称使用学习资源完成率，不冒充正式课程。
- 学习者资源列表排除验收和隐藏记录，下架资源仍不公开；管理员保留查看历史资源的能力。
- 新增只读display_type：有章节的资源显示课程；分析中的正式课程类型也派生为course。原数据库resource_type=document保留，未改库。客户端只用display_type展示，不变更提交字段。

## 实际发布
源：20261024T054843Z_de437452。
画像：20261024T054843Z_de437452_p1_e32123e2e3b5。
推荐：20261024T054843Z_de437452_r1_4642b031b06ca5956652。
看板：20261024T054843Z_de437452_d1_c0d6ae476905。

Spark 3.5.7、local[2]；DWS仍为任务内逻辑聚合。四个任务退出码均0，画像/推荐MySQL发布、Parquet往返与关联批次核对通过。批次带正式范围版本标记。

源快照约北京时间2026-10-24 13:48:44（页面显示秒）。全量课程事件141输入、1过滤、140输出；99为后续按正式课程与有效学习者筛选后的行为数，两者不能作为同一口径直接比较。

## 实际结果与页面
正式课程ID为1068、1069、1070、1071、1072，5门、25章。

student_demo：
- 学习资源列表共5项，均展示课程标签，不再出现数据库验收资源或隐藏406。
- 已开始正式课程5门，已完成0门，正式课程完成率0.0%。当前五门均未全部完成章节，0不是删除数据导致。
- 正式课程行为：浏览89、开始5、历史完成操作2、收藏3、取消收藏0。历史完成操作次数与当前完整课程完成数仍分开。
- 正式课程章节浏览108次、视频播放156次，浏览19个章节、播放9个章节、手动完成2个章节。章节完成2不等于课程完成2。

管理员看板：
- 正式课程总数5、已发布5。
- 正式课程有效学习行为99。
- 全部学习者的已开始正式课程学习记录5条、完成0条、完成率0%；与全部4份画像汇总一致。该分母按用户与课程组合计算，不是所有用户共用的课程目录数量。
- 资源总数/分类不再混入实时目录、下架2253、验收记录及隐藏406。

推荐：
- 正式候选5门，4位学习者；content_v1、popular_v1各20行，共40行。
- 对每一位学习者、每一种算法核对均有5条，排名连续1—5，资源ID均为正式课程集合。
- 四位学习者均未完成五门正式课程，故当前都有5项可推荐；未来完成过滤或下架导致不足5项时应如实返回，不承诺始终满额。
- 本次没有隐藏资源事后过滤造成名额损失。

双端真实页面已核对；全页截图尝试失败后改为普通视口截图，没有生成或拼造图片。证据：outputs/formal-course-scope/student.png、dashboard.png、catalog.png及对应.txt。完整接口核查结果见verification.json。

## 测试
- 隔离Python回归12项通过，包含范围SQL/Spark一致、无章节/下架/验收/隐藏排除、历史输入保留、统计范围及Top5不占位。
- 派生课程类型补充后，正式范围3项重新通过。测试为内存Spark/SQLite夹具，不写生产数据库。
- 前端类型检查及构建通过；原有大包提示保留。
- 首次并行前端回归171项通过、1项路由加载超时、12项跳过；单独复核路由9项通过，未修改超时配置。最终按文件顺序执行完整回归：172项通过、12项跳过，22个测试文件通过、3个跳过；见serial-frontend-tests.log。
- git diff --check通过；存在既有换行转换提示。

## 历史与保护
保护结果见protection-verification.json：learning_progress12、chapter_progress22、course_chapters26、learning_events141、chapter_events270，数量与内容摘要均保持；25个MP4逐文件SHA256一致，章节绑定含在course_chapters完整摘要中。没有补造完成记录。

旧四份latest原字节备份在outputs/formal-course-scope/pre-release/；旧ODS/DWD/ADS文件按原manifest校验通过，旧MySQL画像4行、推荐40行仍保留。证据见old-batches-verification.json。正式发布算法源码与运行前摘要一致。

不执行迁移、不修改视频/章节绑定、不更新原始资源类型、未重算OULAD公开数据。只有既有画像/推荐发布向结果表新增批次，并更新发布指针。没有git add/commit/push，保留其他既有修改。

## 本轮主要文件
- backend/app/core/resource_scope.py（新增）。
- backend/app/services/course_presentation.py、courses.py、resources.py、recommendations.py、dashboard.py。
- backend/app/schemas/resources.py、recommendations.py、dashboard.py。
- spark/utils/resource_scope.py（新增）、recommendations.py；spark/jobs/user_profiles.py、recommendations.py、dashboard_metrics.py。
- frontend/src/types/resources.ts、recommendations.ts、dashboard.ts；frontend/src/views/ResourcesView.vue、ResourceDetailView.vue、RecommendationsView.vue、DashboardView.vue。
- tests/test_formal_course_scope.py（新增）。
- docs/formal-course-scope-design.md（设计）。

后续新增验收资源应沿用明确的验收元数据标记，不能只靠标题文字识别。旧批次保持原有统计语义，不把新范围追写到旧批次。

