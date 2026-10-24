# 章节浏览与视频播放分析接入验收报告

日期：2026-10-24。状态：实施、正式批次发布和双端真实页面核验完成，等待人工验收。未提交Git。

## 实现范围
- 同连接一致性快照新增course_chapters（分析投影）、chapter_progress、chapter_events；原五表抽取保持。
- 章节事件单独ODS/DWD；验证UUID、用户/课程/章节关联、时间、类型、有效状态及播放位置数值，冲突UUID拒绝批次，过滤记录单独留存，校验数量守恒、文件摘要与Parquet往返。
- 画像新增chapter_activity：章节浏览次数、视频播放次数、浏览章节数、播放章节数、完成章节数。活跃日期取课程与章节行为的并集。
- 行为兴趣新增章节标签，去空、去重并规范小写；空章节标签回退课程标签。画像页面默认显示权重前10项，其余通过详情展开，不丢弃计算结果。
- 推荐保持兴趣60%/个人行为25%/热度15%；章节浏览0.5、播放1.0，按用户/章节/北京时间日期/类型去重，同课程每日最多3分，作为个人行为和资源热度补充。该权重为规则参数，不是效果实验结论。保留显式兴趣优先策略、既有候选过滤和课程完成过滤。
- chapter_complete单独统计，不再附加推荐分，避免与课程完成桥接重复计分。
- 看板保留原课程级行为指标，新增独立章节卡片及30日浏览/播放趋势。没有把播放位置当成累计观看时长，也没有新增观看时长采集。
- 接口新增可空字段；旧画像/看板缺少章节字段时保持兼容，不伪造历史章节统计为0。

## 实际批次
源批次：20261023T162443Z_dd5218db。
最终画像：20261023T162443Z_dd5218db_p1_a734aed7406c。
最终推荐：20261023T162443Z_dd5218db_r1_ad98a6112e148d2c2908。
最终看板：20261023T162443Z_dd5218db_d1_325c170ef130。

快照UTC为2026-10-23 16:24:44，页面显示按秒；北京时间为2026-10-24 00:24:44。Spark 3.5.7、local[2]，DWS仍为任务内逻辑聚合。

课程事件：140输入、1过滤、139输出。章节事件：269输入、0过滤、269输出，数量守恒通过。已只读核对章节事件976、977、978、979全部进入新DWD。

第一轮已完整执行四个任务；页面发现标签大小写拆分后，统一标签并在同一份源快照上重算画像、推荐、看板，最终三个任务退出码均0。第一轮ADS和原始源批次保留，未删除失败或中间证据。最终发布关联与MySQL读取核对通过。

## 双端真实页面
学生student_demo重新登录后访问个性化推荐：
- 章节浏览109次，视频播放156次。
- 浏览20个章节，播放9个章节，完成2个章节。
- 活跃8天，原课程浏览104次、收藏5次。
- 规范后的pyspark兴趣约4.8%，同名大小写不再拆成两个标签。
- 内容推荐PySpark/MySQL/HDFS，综合得分100%/40%/12.5%；这是规则综合分，绝非准确率、概率或效果提升。

管理员admin_demo实际访问平台看板：
- 原课程级有效学习者行为仍129条、画像4份。
- 新增章节浏览109次、视频播放156次、播放用户1位、浏览用户与章节组合20、播放组合9、完成组合2。
- 5张图表canvas均为非零尺寸；实际截图核对新增卡片与趋势布局。

上述109/156等包含历史演示操作，不能说是本轮新产生的次数。269是所有清洗通过的章节事件，面向活跃学习者展示的章节浏览/播放/完成合计267；两者统计人群口径不同，不混加。新增章节指标没有改写原129条课程级指标。

## 测试证据
- tests/test_chapter_analytics.py：3项通过；验证正常清洗、重复UUID去重、冲突拒绝、归属错误/未来时间过滤、每日信号去重上限、章节标签大小写合并、画像及推荐影响。全部使用内存fixture，不修改生产数据。
- tests/test_chapter_display.py：2项通过；旧字段兼容及新字段模型校验，无数据库写入。
- 前端最终构建及类型检查通过，171项测试通过、12项跳过；原有大包提示保留。
- git diff --check通过（存在既有换行转换提示，不是检查失败）。
- outputs/chapter-analytics-final/verification.json：真实MySQL读取、旧批次文件摘要校验、新DWD4条事件核查、批次关联。
- outputs/chapter-analytics-final/student.png、dashboard.png、dashboard-section.png：真实页面截图；student-page.txt、dashboard-page.txt为页面内容证据。
- outputs/chapter-analytics/：第一轮任务日志、发布结果；outputs/chapter-analytics-final/：最终任务日志、发布结果和验证。

## 保留与边界
旧四份latest原字节备份在outputs/chapter-analytics/pre-release/，对应哈希见before.json；旧ODS/DWD/ADS按原manifest校验通过。旧MySQL批次画像4行、推荐36行仍存在。最终重算前的第一轮指针另存outputs/chapter-analytics-final/pre-release/。

未执行表结构迁移；未修改原始学习事件、视频、章节绑定、课程内容、配置、OULAD任务或公开数据发布。只有现有画像/推荐发布流程写入新批次结果，latest切换到新结果。保留其他既有未提交修改。

已知原有RDD资源级completed与章节0%进度口径差异未在本任务修复，推荐仍沿用原过滤规则。新数据来自演示账号实际操作和历史验收数据，不代表真实学生学习效果。没有开展推荐准确率或性能评测。

## 本轮代码文件
- spark/utils/chapter_analytics.py（新增）；schemas.py、profiles.py、recommendations.py。
- spark/jobs/clean.py、quality.py、user_profiles.py、recommendations.py、dashboard_metrics.py。
- backend/app/schemas/recommendations.py、dashboard.py；backend/app/services/recommendations.py。
- frontend/src/types/recommendations.ts、dashboard.ts；frontend/src/views/RecommendationsView.vue、DashboardView.vue。
- tests/test_chapter_analytics.py、tests/test_chapter_display.py（新增）。
设计文件：docs/chapter-analytics-design.md。

