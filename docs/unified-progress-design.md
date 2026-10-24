# 统一课程进度设计

用户已确认实施。有章节课程仅依据chapter_progress：没有章节记录为not_started，任一章节开始而未全部完成为in_progress，全部完成为completed；完成率为完成章数/总章数。无章节资源继续使用learning_progress。旧completed及learning_complete保留为历史操作，不再作为章节课程当前完成状态或完成加分依据。

后端统一派生状态、首次开始/完成时间；章节响应新增started，前端停止只看completed重算。正常章节完成仍手动确认，禁止旧完成状态绕过章节验证。历史旧回执保持幂等和审计含义，不篡改历史记录。

Spark新快照下生成独立DWD effective_progress，校验用户/章节关联与开始完成时间，八表同一快照；画像学习统计、推荐完成过滤及开始/完成贡献、看板学习统计复用该结果。历史操作次数保留，单独标明不等于当前完成资源数。旧DWD缺少新派生结果时按旧规则读取，不覆写旧批次；新批次明示progress_rule和代码摘要。

不更新历史learning_progress、不补造chapter_progress或事件，不修改视频、课程章节绑定、配置。保留旧ODS/DWD/ADS及latest原字节备份。先内存/隔离测试，再运行新pipeline→画像→推荐→看板。只读对照RDD0/5学习中、画像与看板学习分母/完成数、推荐是否具备候选资格；不强制RDD必须排入TopN。输出outputs/unified-progress-acceptance-report.md，不提交Git。

实施补充：前端使用新增started与completed执行同一规则，并对课程查询的冲突旧状态作一致派生；新操作回执按服务端当前结果同步。已完成后端/前端及Spark接入、隔离验证、正式新批次、真实双端页面验收。详见outputs/unified-progress-acceptance-report.md。
