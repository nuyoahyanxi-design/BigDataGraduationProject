# 答辩当前状态与统一口径

更新日期：2026-10-13。代码基线：`b8474f2eab789bf3d16463a41f1bfa27cf7dc432`。本次只修订文档，不改业务代码、数据库或运行产物，不运行Spark、不提交Git。

## 已实现与已验证范围

系统支持学生登录、课程列表/详情、章节教学内容、真实视频播放、学习行为与进度、画像及推荐展示；支持管理员用户只读查看、课程/资源信息和发布批次、统计看板；支持AI通用及课程问答实现。管理员资源/课程维护接口存在，但本次演示验收不覆盖管理写操作。

5门正式课程、每门5章，共25章及25个正式MP4；另有1门隐藏课程1章，数据库章节总数26。2026-10-10媒体文件验收25/缺失0/异常0/通过25；2026-10-13浏览器实际播放PySpark第2章`course_1069/chapter_007.mp4`，时长232.44秒、时间推进约63秒、无媒体错误。真实播放已证实，不能再把当前正式课程视频描述为未提供；不能推导25章浏览器全片或全部音画质量均已验收。视频由`frontend/public/videos`及后端`/videos`服务提供，学生接口按标准目录发现媒体；数据库旧`/demo/video.mp4`值的历史存在不等于当前播放器没有真实媒体。

本轮演示一次通用AI调用成功：agnes-3.0-flash、status=succeeded、error_code=null，记录创建至完成约4.353秒；不承诺远程服务持续稳定、答案每句正确或课程检索全部通过。AI通用回答提到的集群/模型训练不是本项目实现依据。

## 技术栈

| 层 | 当前版本/方式 | 来源 |
|---|---|---|
| 平台 | Windows + WSL2 Ubuntu-22.04-Recovered | 10月13日环境及演示验收 |
| Python/Java | Python3.11.17 / OpenJDK17.0.20.1 | 同上 |
| 后端 | FastAPI0.115.12、Uvicorn0.34.2、SQLAlchemy2.0.40、PyMySQL1.1.1、PyJWT2.10.1、httpx0.28.1 | backend/requirements.txt及已有运行验证 |
| 数据库 | MySQL8.0.45，12张表，SQL迁移001—007 | 已有实际访问与database/migrations |
| 前端 | Vue3.5.43、TypeScript5.9.3、Vite7.3.6、Node22.22.2/npm10.9.7 | frontend/package.json及已有运行验证 |
| 展示依赖 | Element Plus2.14.7、Pinia3.0.4、Vue Router4.6.4、Axios1.20.0、ECharts6.1.0 | frontend/package.json |
| 分析 | Spark/PySpark3.5.7、Java17、local[2]、Spark SQL、Parquet、Connector/J8.0.33 | spark/configs/pipeline.json及已有运行验证 |

物理层为ODS/DWD/ADS；DWS是任务内聚合，无独立落盘。没有HDFS集群、ALS、向量库、实时训练、大模型推荐训练或线上A/B效果验收。content_v1融合评分为60%标签余弦、25%个人行为、15%热度；无历史热度回退。评分百分比不是准确率。AI是增强功能，不替代Spark。

## 当前批次与历史批次

| 口径 | 10月10日历史证据 | 10月13日当前发布批次 |
|---|---|---|
| 源批次 | 20261010T060537Z_fb2d2acb | 20261013T052412Z_1fc73f17 |
| ODS五表users/resources/progress/favorites/events | 6/13/11/3/90 | 6/13/11/3/123 |
| 清洗输入/有效/过滤 | 90/89/1 | 123/122/1 |
| 新批次画像/推荐 | 4/36 | 4/36 |
| 趋势自然日行数 | 30 | 30 |
| 历史累计结果表（发布后快照） | 34/436 | 38/472 |

当前配套画像：`20261013T052412Z_1fc73f17_p1_5f4a3dd7c998`。推荐：`20261013T052412Z_1fc73f17_r1_587c243a0d860c24e7f0`。看板：`20261013T052412Z_1fc73f17_d1_6848cd21cf6f`。四阶段completed且同源，10个Parquet实际读回与SHA256/_SUCCESS通过。快照截止2026-10-13 05:24:11.782 UTC（北京时间13:24:11.782）。过滤1条no_state_change，不是程序失败。

当前批次DWD122行，看板active learner全快照行为119行；物理推荐36行，看板排除联调资源406后两算法各15行、合计30；student_demo单算法当前3张卡（86.7%/35.6%/17.8%）。6账号为4学习者+2管理员；4画像不是全体账号数。数据库resources13，学生列表11，看板当前资源12/已发布11；管理员课程6（5正式+1隐藏）。这些数的筛选范围不同。

10月13日答辩演示后业务快照：learning_events125、chapter_events261、ai_qa_records51；画像38、推荐472。它们是最近验收时的数据库累计行数，不是本次文档修订重新查询的实时数。新增2浏览、2章节/播放事件、1问答；已有行未修改/删除，latest前后不变。新演示事件尚未进入123条ODS快照，不得称推荐实时更新。

## 证据与材料范围

- [扩容后功能与完整Spark流程报告](../outputs/post-expansion-final-acceptance-report.md)：10月13日完整重算/发布。
- [答辩演示验收报告](../outputs/defense-demo-acceptance-20261013/defense-demo-acceptance-report.md)：真实学生/管理员演示、单视频播放、一次远程AI、只读Parquet、既有记录保护。
- [当前架构](architecture.md)、[演示脚本](defense-demo-script.md)、[当前启动说明](defense-startup-guide.md)。

10月11日旧截图与论文/PPT大纲保留为历史材料，不能把旧批次数字当当前值。当前功能验证不证明推荐效果提升、真实教学收益、生产安全或分布式性能。论文为Markdown草稿，PPT为大纲，正式学校格式/文献/成品排版尚未验收。
