# 平台Spark更新与页面验收报告

日期：2026-10-24（北京时间）。本轮用户授权运行现有平台Spark处理并更新画像、推荐、看板；未修改业务代码、配置、视频，未提交Git。

## 执行与保护
先原字节备份四个旧latest至outputs/platform-spark-refresh/pre-release/，哈希及旧批次见before.json；旧批次目录保留。按顺序执行既有pipeline、user_profiles、recommendations、dashboard_metrics，退出码均0。画像显式绑定新source，推荐显式绑定新profile，看板关联同源画像/推荐。没有运行OULAD任务，没有重发公开数据结果。

运行环境：既有WSL环境，Spark 3.5.7、local[2]。DWS仍为任务内逻辑聚合职责。

## 本次发布
- 源批次：20261023T160803Z_02936af4。
- 画像：20261023T160803Z_02936af4_p1_5f4a3dd7c998。
- 推荐：20261023T160803Z_02936af4_r1_0552d4f0ad2320e95d63。
- 看板：20261023T160803Z_02936af4_d1_c50c01030a5b。
- 截止：2026-10-23 16:08:03.481 UTC，即北京时间2026-10-24 00:08:03.481。

清洗输入140、过滤1、输出139；无效0、重复0，过滤原因no_state_change，数量守恒通过。画像4行、推荐36行，Parquet往返及MySQL发布均通过。看板Parquet往返通过。

## 新行为纳入核验
只读读取新DWD Parquet确认事件2783、2784、2785均存在，分别是PySpark浏览、PySpark收藏、RDD浏览。章节事件976—979保留于业务库；现有分析投影仅抽取users/resources/learning_progress/favorites/learning_events，不包含chapter_events，所以4条章节浏览/播放不直接计入当前画像与看板；没有为凑数量修改现有流程。

## 学生页面实际检查
以student_demo打开个性化推荐，显示：活跃8天；浏览104、开始9、完成5、收藏5、取消收藏1；当前画像和推荐批次均为本次新批次。内容推荐显示PySpark、MySQL、HDFS，综合得分96%、36%、16%，分数不代表预测概率或效果提升。

对照旧画像：活跃6→8天，浏览95→104，收藏4→5；其余上述事件次数不变。增量包含旧2026-10-13批次以来其他操作，不把全部变化归因于上一轮7条事件。PySpark兴趣权重约2.37%→3.23%，仅为现有计算结果变化，不代表学习效果验证。

## 管理员页面实际检查
用户手动登录admin_demo后，真实打开平台数据看板：用户6（活跃学习者4、管理员2），当前资源12（已发布11），有效学习者行为129，配套画像4。四张图表canvas均有非零尺寸，批次详情显示本次同源批次。

139为DWD总输出；129为看板筛选后的有效学习者行为口径，不能混为同一指标。推荐发布36行，而页面统计content_v1与popular_v1各15行，是现有展示过滤联调资源后的口径；未改变结果行数或可见性规则。

页面仍明确标注演示样本/开发验收样本；本次真实浏览器操作并不会把所有历史样本转为真实学生研究数据。

## 证据与限制
- execution.json、四份任务.log：真实执行状态。
- published.json：本次四份发布结果。
- verification.json：批次关联、MySQL画像与推荐、新DWD事件、源码哈希核验。
- student-page.txt、dashboard-page.txt：真实页面内容。
- student.png、dashboard.png：真实页面截图（浏览器沿用当前窄屏尺寸）。

运行前后spark/jobs、spark/utils、spark/configs、backend/app、frontend/src既有文件哈希一致。未执行git add/commit/push。没有修复先前发现的RDD旧资源级completed与章节0%口径差异；本次计算仍遵循现有规则。未做性能/推荐准确率测试。

本阶段完成，停止运行，等待人工验收。
