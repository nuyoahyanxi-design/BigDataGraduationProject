# 毕设扩容后最终功能与环境验收报告

日期：2026-10-13（北京时间）。项目：D:\BigDataGraduationProject。

结论：本轮要求的系统功能链路与一次完整 Spark 批次验收通过；未修改业务代码、重构、安装依赖或执行修复。不代表全部业务接口、并发性能、真实学习效果或 AI 远端能力已验收。

## 阶段1：系统功能

- MySQL80 Running，MySQL 8.0.45；12张表可访问。
- 复用原启动脚本启动 Backend FastAPI（8000）及 Frontend Vue/Vite（5173）；后端完成 startup，前端 ready。
- 真实浏览器以 student_demo 登录，跳转个人账户页，显示 learner 和兴趣标签；前端代理登录及用户接口成功。
- 课程列表显示11项，包括5门正式教学课程与历史验收资源；PySpark课程的章节、正文、代码、练习和视频控件成功加载。未进行视频播放与音画质量验收。
- API新增一次有效浏览事件，id=2768；同UUID重复提交返回同一id，数据库精确计数1。浏览器进入章节新增 chapter_view，最新id=969；页面显示学习行为已记录。未点击完成章节、不修改既有完成状态。
- content_v1与popular_v1推荐接口HTTP200；真实推荐页面显示画像、推荐理由与资源卡片，观察期间控制台无错误或警告。

## 阶段2：完整Spark流程

实际依次执行 spark.jobs.pipeline、spark.jobs.user_profiles、spark.jobs.recommendations、spark.jobs.dashboard_metrics，全部退出码0。画像和推荐是ADS产物，逻辑顺序为MySQL→ODS→DWD→画像ADS→推荐ADS，并补充看板ADS。

ODS源批次：20261013T052412Z_1fc73f17

| 数据 | 行数 |
|---|---:|
| ODS users | 6 |
| ODS resources | 13 |
| ODS learning_progress | 11 |
| ODS favorites | 3 |
| ODS learning_events | 123 |
| DWD有效学习事件 | 122 |
| DWD排除记录 | 1 |
| 新画像批次 | 4 |
| 新推荐批次（两算法合计） | 36 |

过滤原因为no_state_change=1；无非法记录、无重复记录，123=122+1守恒通过。此过滤属于现有清洗规则，不是运行失败，未修正历史记录。

ODS与DWD的manifest均completed；四个latest均completed且同源。10个Parquet文件实际存在、大小与SHA256匹配，各数据目录_SUCCESS存在。任务内真实Parquet写入与读回校验通过。MySQL按本次batch_id查询得到画像4行、推荐36行，与发布元数据一致。

画像批次：20261013T052412Z_1fc73f17_p1_5f4a3dd7c998
推荐批次：20261013T052412Z_1fc73f17_r1_587c243a0d860c24e7f0
看板批次：20261013T052412Z_1fc73f17_d1_6848cd21cf6f

发布后推荐API返回新批次、3张学生推荐卡片；真实浏览器刷新后显示相同新批次、画像和新评分，完成计算→发布→页面读取闭环。36行是全体用户及两算法产物，3张卡片是当前学生单算法可见结果，口径不同。

## 数据变化

| 表 | 验收前 | 验收后 | 变化 |
|---|---:|---:|---:|
| learning_events | 122 | 123 | +1有效浏览 |
| chapter_events | 258 | 259 | +1章节浏览 |
| user_profiles | 34 | 38 | +4新批次 |
| recommendation_results | 436 | 472 | +36新批次 |

其他8张表行数不变。未删除历史批次、没有数据清理、迁移或重置。以上是行数对照，不是所有数据库字段逐字节审计。数据仍含开发验收样本，不代表真实用户研究。

## 阶段3：版本与交付

验收前代码基线为main / 9dbbb9d911b194108f4e404457677ba013f196fb。验收后已跟踪业务文件无差异、无删除；本轮仅将此报告和去除凭据的结构化证据纳入验收提交。原有未跟踪论文文档与账号密码文件保留、不纳入本轮提交；不使用git add -A，不提交数据、日志、截图、VHDX、环境配置或凭据。

项目outputs默认被忽略，因此只对本轮精确报告与证据文件使用git add -f，不修改.gitignore。提交结果由交付目录commit-receipt.json记录。未推送远端。

前后端保持运行供用户查看；WSL保持运行以支持服务。本轮不执行自动关机。

## 验证边界

没有运行全量带写入的回归测试、管理员CRUD、AI外部请求、安全/并发/压力测试、课程视频播放或跨设备验收。未发现本轮指定链路的失败；不得把本结论扩大为上述未测范围通过。

交付证据：stage1.json、stage2.json、四份Spark日志及登录/课程/推荐前后截图，位于当前聊天outputs/final-acceptance目录。报告与stage2.json另存项目outputs，用于本轮Git提交。
