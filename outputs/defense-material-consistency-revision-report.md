# 答辩材料一致性修订报告

修订日期：2026-10-13。项目：D:\BigDataGraduationProject。代码基线b8474f2；本次文档修订尚未提交，HEAD保持不变。

## 结论

完成README、当前概览/架构、启动与答辩说明、论文相关材料及存在旧现状描述的验收报告修订。当前描述统一为真实教学视频、12表、已实现学生学习/管理员统计/AI问答/Spark处理链路；历史批次与失败记录保留原日期及结果，新增明确历史说明。

本次依据已确认事实、前轮验收证据、现有源码/依赖声明和发布元数据，不重新运行功能验收。没有连接或修改数据库，没有运行Spark、安装依赖、修改业务代码或提交Git。

## 主要修订

| 类别 | 原问题 | 修订后 |
|---|---|---|
| 视频 | README与最终指南仍称没有视频/继续使用早期示例地址 | 当前正式媒体25个MP4，10月13日第2章chapter_007.mp4实际播放约63秒；不推导25章全片播放通过 |
| 视频元数据 | 将数据库早期/demo地址误作当前播放来源 | 区分历史字段与学生接口的标准目录媒体发现，示例改为/videos/course_1069/chapter_007.mp4 |
| 系统能力 | 旧概览称仅初始化、AI延期，并规划未落地表与任务接口 | 改为实际学生/管理员/AI/离线处理能力；注明没有自动任务提交API、生产调度或未实现表 |
| 架构 | 旧最终架构仍写七表和纯余弦 | 更新12表、迁移001—007，融合60%标签余弦/25%行为/15%热度，无历史热度回退 |
| 当前批次 | 材料混用10月5日/10月10日证据和现场结果 | 统一当前源批次20261013T052412Z_1fc73f17；旧批次保留历史标签，不直接替换原测试结果 |
| 数据规模 | 快照/累计/筛选口径易混淆 | 当前ODS123→DWD122/过滤1，画像4/推荐36/日指标30；累计38/472；演示后业务事件125是另一时间快照 |
| 启动 | 旧说明包含旧发行版、localhost与写入型演示 | 新启动说明使用Ubuntu-22.04-Recovered、127.0.0.1与现有服务脚本；复用服务，不默认执行建课/完成/重算 |
| 论文 | 七章和大纲缺少最新补充证据 | 增加统一状态入口；测试章新增10月13日真实演示和批次数据，保留10月10日历史表格 |
| 截图 | 旧截图推荐分数和看板规模已过时 | 保留真实图片，说明原采集日期及旧数字；归档新演示证据作为可用引用，不编辑截图像素 |
| 历史验收 | 旧“未提供/未播放/未生成”容易被当现状 | 首部注明原阶段边界；视频失败描述限定为当时情况，不把未完成的HeyGen方案改写为成功 |

## 统一数据与技术口径

当前源批次：`20261013T052412Z_1fc73f17`。画像、推荐、看板均同源且completed；统计截止2026-10-13 05:24:11.782 UTC（北京时间13:24:11.782）。

| 指标 | 10月10日历史 | 10月13日当前批次/对应快照 |
|---|---:|---:|
| ODS五表users/resources/progress/favorites/events | 6/13/11/3/90 | 6/13/11/3/123 |
| 清洗有效/过滤 | 89/1 | 122/1 |
| 画像/物理推荐 | 4/36 | 4/36 |
| 累计画像/推荐（发布后） | 34/436 | 38/472 |
| 日指标自然日行数 | 30 | 30 |

6账号包含4学习者和2管理员；物理推荐36与看板可见30、单个学生单算法3张卡不同。数据库13资源、学生列表11、看板12/已发布11、管理课程6（5正式+1隐藏）、数据库26章与正式25章/视频不同。现有DWD122与看板active learner119不同。演示后学习事件125、章节事件261、AI记录51是历史验收快照，本次未重新查询实时数据。

技术栈：Windows/WSL2 Ubuntu-22.04-Recovered，Python3.11.17、Java17.0.20.1、MySQL8.0.45、Spark3.5.7 local[2]、Parquet/JDBC；FastAPI0.115.12、SQLAlchemy2.0.40、PyMySQL1.1.1；Vue3.5.43、TypeScript5.9.3、Vite7.3.6、Node22.22.2/npm10.9.7。详细固定依赖及出处见docs/defense-current-state.md。

## 真实性与保留边界

1. 真实媒体存在及单章播放，不等于所有视频浏览器全片、全部设备或音画质量通过。
2. 10月13日一次通用Agnes问答成功，不等于全部课程AI、远程服务稳定或答案专业正确性通过；通用回答里的集群/训练不是本项目证据。
3. 系统实际local[2]，DWS为任务内聚合，没有HDFS集群、ALS、向量检索、实时训练或真实教学效果证明。
4. 管理员用户只读查看；维护接口存在不等于本轮管理写操作通过。没有独立学习历史前端页，课程状态及事件API是实际展示。
5. 旧失败报告、初期设计、旧来源/日期/测试次数和明确模拟实验数据保留，不用当前结果回填过去。
6. 论文仍是Markdown草稿，PPT是大纲；学校格式、参考文献及正式成品排版尚未验收。

## 文件范围

本轮修订/新增 53 个正文材料文件（不含本报告），其中包含新增统一事实说明和启动说明。完整清单见下一节。另将前轮既有演示证据归档至outputs/defense-demo-acceptance-20261013，共29个文件，未复制数据库逐行摘要文件，不重新产生测试证据；归档报告增加来源说明，原件不改。

关键入口：

- README.md：当前批次/视频/功能/证据及过时章节说明。
- docs/defense-current-state.md：统一技术栈、数据、视频与真实性边界。
- docs/defense-startup-guide.md：当前启动与只读优先演示。
- docs/project-overview.md、docs/system-final-architecture.md：实际能力、12表、融合评分。
- docs/final-project-acceptance-guide.md：当前视频结论及历史写入方案限制。
- docs/defense-demo-script.md、docs/defense-ppt-outline.md、docs/thesis-outline.md、docs/thesis-draft七章：历史基线与当前补充。
- outputs历史报告：状态补注和历史视频措辞，不改变原测试结论。

## 静态验证

- 307个Git跟踪非Markdown文件在主要修订前后原始SHA256相同；最终Git差异仅Markdown。
- 所有本轮材料本地Markdown链接存在，没有新增或遗留缺失链接。
- git diff --check通过；暂存区没有变更，HEAD仍b8474f2；没有提交或推送。
- 四个latest元数据SHA256与前轮验收结果相同。
- 全程仅使用文件读取/编辑及Git只读检查，没有数据库连接、Spark调用或依赖安装。
- 原有未跟踪论文文档和账号文件保留；账号文件未读取或提交。

修订前材料副本位于当前聊天work/defense-document-revision-20261013。验证清单和本报告副本位于当前聊天outputs/defense-document-revision。未修改代码，无需运行代码测试。

## 完整修订文件清单

- README.md
- docs/agnes-startup-configuration-design.md
- docs/ai-course-video-access-design.md
- docs/ai-teaching-video-design.md
- docs/architecture.md
- docs/course-ai-final-browser-acceptance-design.md
- docs/course-learning-design.md
- docs/defense-current-state.md
- docs/defense-demo-script.md
- docs/defense-ppt-outline.md
- docs/defense-startup-guide.md
- docs/development-plan.md
- docs/environment-recovery-design.md
- docs/environment.md
- docs/final-project-acceptance-guide.md
- docs/formal-course-chapters-design.md
- docs/formal-release-preparation-design.md
- docs/project-overview.md
- docs/system-final-architecture.md
- docs/thesis-consistency-fix-report.md
- docs/thesis-consistency-review.md
- docs/thesis-draft/chapter-01-introduction.md
- docs/thesis-draft/chapter-02-related-technologies.md
- docs/thesis-draft/chapter-03-requirement-analysis.md
- docs/thesis-draft/chapter-04-system-design.md
- docs/thesis-draft/chapter-05-system-implementation.md
- docs/thesis-draft/chapter-06-system-testing.md
- docs/thesis-draft/chapter-07-summary.md
- docs/thesis-outline.md
- docs/windows-one-click-start-design.md
- outputs/ai-course-video-auto-import-report.md
- outputs/ai-course-video-implementation-report.md
- outputs/ai-course-video-production-delivery-report.md
- outputs/ai-teaching-video-design-acceptance-report.md
- outputs/course-ai-final-browser-acceptance-report.md
- outputs/course-learning-acceptance-report.md
- outputs/course-learning-ui-acceptance-report.md
- outputs/course-teaching-content-acceptance-report.md
- outputs/defense-demo-optimization-report.md
- outputs/final-system-acceptance-report.md
- outputs/formal-course-chapters-acceptance-report.md
- outputs/formal-release-preparation-execution-report.md
- outputs/formal-release-readiness-report.md
- outputs/formal-release-result-report.md
- outputs/graduation-defense-demo-script.md
- outputs/graduation-final-freeze-check-report.md
- outputs/graduation-final-status-report.md
- outputs/heygen-avatar-iii-compatibility-report.md
- outputs/post-release-browser-acceptance-report.md
- outputs/project-freeze-acceptance-report.md
- outputs/spark-batch-republication-diagnostic-report.md
- outputs/spark-publication-stability-acceptance-report.md
- screenshots/README.md

## 后续使用建议

答辩内容优先引用统一状态说明与当前启动说明；引用历史批次时明确日期。需要学校正式排版、引用文献校核或PPT成品时单独授权，不把本次材料一致性修订称为完成这些工作。文档当前处于未提交状态，是否提交留待用户后续指令。
