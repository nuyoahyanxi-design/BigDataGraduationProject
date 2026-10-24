# 平台实际操作数据采集验收报告

## 完成情况
使用已由用户登录的student_demo，在平台真实页面操作：浏览PySpark数据处理实践并收藏，进入筛选与列转换章节播放视频；浏览Spark RDD基础教程，进入什么是RDD章节播放视频。两次播放均已暂停；未点击完成章节。

## 已核验结果
数据库只读查询确认新增7条有效记录：
- learning_events 2783：PySpark资源浏览。
- learning_events 2784：PySpark收藏。
- learning_events 2785：RDD资源浏览。
- chapter_events 976、978：两门课程的章节浏览。
- chapter_events 977、979：两门课程的视频播放。

事件时间UTC为2026-10-23 15:58:20.918至16:00:25.763，对应北京时间2026-10-23 23:58:20.918至2026-10-24 00:00:25.763。本次跨午夜操作，报告保留数据库原始UTC时间。

页面实际观测PySpark播放进度42秒、RDD暂停后40秒；属于播放器当时位置，不作为持久化累计观看时长证据。数据库playback_seconds分别为0.000和0.002，因为现有实现于播放动作发生时上报位置；没有持续时长上报，不能据此计算真实观看时间。

## 证据
- platform-activity-session/database-evidence.json：只读数据库核查，含事件编号、类型、资源、时间与有效性；未包含凭据。
- platform-activity-session/rdd-learning.png：真实RDD课程页面，暂停于40秒。
- 实现依据：frontend/src/views/ResourceDetailView.vue、CourseLearningView.vue；frontend/src/components/LearningVideo.vue；backend/app/services/courses.py。

## 边界与现有问题
- 属于演示账号经助手操作产生的数据，不是独立学生使用研究，也没有增加平台用户人数。
- 无直接数据库写入；持久化来自平台正常业务接口。
- 本轮没有运行Spark，未更新离线画像、推荐和管理看板发布批次。新数据入业务库不意味着旧批次立即变化。
- 发现RDD资源级旧learning_progress.status为completed，而课程章节完成率0%；为现有两套进度口径差异，本轮未修改旧状态或代码。
- 只播放部分视频，未声称学完或完成章节。
- 保留所有既有未提交修改；没有提交Git。

本轮完成，等待用户确认是否进入平台新批次处理阶段。
