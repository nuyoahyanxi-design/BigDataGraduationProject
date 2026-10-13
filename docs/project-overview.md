# 项目概览与当前实现

更新日期：2026-10-13。题目：基于Spark的学习行为分析与个性化资源推荐系统设计与实现。代码基线b8474f2，当前数据与技术栈统一见[答辩当前状态](defense-current-state.md)。早期MVP规划不作为未完成业务或已实现额外表的依据。

已实现学生登录、兴趣、资源检索/详情、课程章节/教学正文/真实视频、学习行为和手动进度；已实现管理员用户只读、课程/资源维护、批次和统计展示；已实现通用/课程AI适配与历史。接口存在与本轮验收通过分开：10月13日覆盖学生/管理只读展示、单章视频与一次通用AI，不包括所有管理写操作或所有AI模式。

Vue3→FastAPI→MySQL；人工顺序执行pipeline→user_profiles→recommendations→dashboard_metrics。结果经过校验写入Parquet/结果表，成功批次发布latest；网页刷新只读取结果。不存在自动任务提交API、定时调度或分布式调度验收。

实际12表，迁移001—007：users、resources、learning_progress、favorites、learning_events、user_profiles、recommendation_results、course_chapters、chapter_progress、chapter_events、ai_qa_records、ai_course_contexts。daily_metrics是文件，未实现analysis_batches或serving_versions表。

真实物理层ODS/DWD/ADS，DWS任务内聚合；Spark3.5.7 local[2]。popular_v1热度基线；content_v1融合60%标签余弦、25%个人行为、15%热度，无历史热度回退。最新批次123→122、画像4、推荐36，都是开发验收样本；累计结果和业务实时快照见统一口径。

没有ALS、向量检索、HDFS集群、可信观看时长、自动练习评分、大模型训练、实时推荐重算、线上A/B或真实学习收益结论。离线实验工具及明确模拟数据不等于真实学生效果研究。

5门正式课程25章/25视频，另1隐藏课1章；10月13日实际播放证据不覆盖25章全片。文档、PPT大纲和论文草稿不等于学校格式成品。启动和答辩顺序见[当前启动说明](defense-startup-guide.md)。
