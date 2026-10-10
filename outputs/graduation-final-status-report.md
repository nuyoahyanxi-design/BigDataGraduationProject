# 毕业设计最终状态检查报告

检查日期：2026-10-10，北京时间16:26起。结论：核心只读完整性检查通过，可进入人工彩排；本轮没有重新完成登录、视频试听与章节写入的浏览器端到端验收。

## 当前检查与证据

| 项目 | 结果 | 验证方式与边界 |
|---|---|---|
| 后端 | 通过 | 8000端口OpenAPI HTTP 200；未启动或重启服务；不存在专用/health路由，404不能视为服务异常 |
| 前端 | 通过 | 5173首页及/src/main.ts HTTP 200；代理GET /api/resources返回401，说明访问到受保护API；HEAD为405属方法不支持 |
| MySQL | 通过 | READ ONLY一致性事务，SELECT 1成功，12张表读取成功 |
| 演示账号 | 状态通过 | student_demo为active learner，admin_demo为active admin；本轮未验证密码或重新登录 |
| 推荐 | 通过 | 原业务只读服务返回content_v1与popular_v1，各3条，正式推荐批次一致 |
| 用户画像 | 通过 | 学生推荐响应携带画像；位于推荐页面，不是独立画像路由 |
| 管理看板 | 通过 | 原overview业务服务available=true；本轮非管理员页面渲染验收 |
| 视频 | 完整性通过 | 25个MP4重新计算SHA256，25/25与完整解码验收记录一致；本轮未重复完整解码或人工观看 |
| 发布来源 | 通过 | 四latest均completed，画像/推荐/看板来源均为20261010T060537Z_fb2d2acb |

视频覆盖5门课程的25个目标章节；数据库共有26个章节，两者统计范围不同，不应误判缺失。目录分组：1068/1–5，1069/6–10，1070/59–63，1071/54–58，1072/11–15。既有完整验收：outputs/course-video-acceptance/acceptance-20261010T082020900949Z.md，25通过、0缺失、0异常。视频H264/AAC、1280×720，约4分11秒至4分24秒，总计约107.39分钟。

本轮只读证据目录：outputs/final-defense-audit/，包含current-state.json、两种推荐响应、课程响应、dashboard.json、HTTP记录、git-status.txt。数据库计数为：

- ai_course_contexts：25
- ai_qa_records：50
- chapter_events：84
- chapter_progress：18
- course_chapters：26
- favorites：3
- learning_events：94
- learning_progress：11
- recommendation_results：436
- resources：13
- user_profiles：34
- users：6

## 展示口径

学生当前推荐为1069、1071、1070；PySpark第1章实际为“DataFrame与Schema”，已经完成，第2章“筛选与列转换”尚未完成。不要沿用“Spark大数据计算框架简介”的错配标题。

正式分析截止时间为2026-10-10 06:05:36.910 UTC，即北京时间14:05:36.910。当前MySQL中的学习行为可能晚于此时，画像与推荐评分不会自动更新。整门课程完成后的在线过滤可立即排除课程，单章完成不保证推荐变化。看板行为统计使用批次快照，资源总量与类别等部分信息读取当前数据库，不应声称所有指标实时或全部冻结。

## 版本及限制

HEAD为19b4739598a86a2307f62b135c7d27de2b78af1e。当前工作区含此前视频接入与展示优化的未提交改动（15个跟踪文件及未跟踪产物），该commit不能单独代表当前交付系统。本轮只新增设计、验收报告和work下只读检查脚本，未修改业务代码、数据库、Spark或发布指针，未提交Git。

历史浏览器基础验收见outputs/post-release-browser-acceptance-report.md；其中“缺视频”的旧结论已由本次资源检查更新，但旧截图仍是旧画面。本轮未新增截图。数据为开发验收样本，不能宣称真实学生教学效果、推荐准确率或大规模生产性能。可以开始彩排，正式录制前完成风险清单中的人工确认。
