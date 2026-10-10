# 视频提示文字清理最终报告

完成日期：2026-10-10（北京时间）。

## 最终结论

已将 candidates 中24个已验证候选视频替换到正式目录 frontend/public/videos。chapter_006 未处理，25份 originals 原视频备份全部保留且 SHA256 与备份清单一致。

指定脚本 backend/tools/accept_course_videos.py 验收通过，退出码0：

| 验收项 | 结果 |
| --- | --- |
| 课程 | 5 |
| 章节 | 25 |
| 视频 | 25 |
| 缺失 | 0 |
| 异常 | 0 |
| 通过 | 25 |
| accepted | true |

## 替换范围

| 课程目录 | 已替换章节 |
| --- | --- |
| course_1068 | chapter_001–005 |
| course_1069 | chapter_007–010 |
| course_1070 | chapter_059–063 |
| course_1071 | chapter_054–058 |
| course_1072 | chapter_011–015 |

本轮仅复制候选成品到原正式路径，没有重新编码。正式视频24/24的 SHA256 与候选验证记录一致，chapter_006 的 SHA256 与原始清单一致。

## 验证证据与边界

- 替换前：25份原片备份、24个唯一候选视频哈希核对通过；候选范围不含 chapter_006。
- 既有候选全片验证记录：音轨一致、修改区域外解码像素与帧时序一致、完整解码通过、提示文字区域逐帧检查通过；候选哈希已在本轮重新核对。
- 用户已确认 chapter_001、chapter_010、chapter_015 人工抽查通过。chapter_010 底部代码裁切属于原视频已有问题，本次未新增，未修复。
- 替换后：25份备份完整，24个正式成品与候选一致，chapter_006 未变；758个受保护文件的哈希保持一致。
- 本轮实际运行指定验收脚本，对正式目录25个视频执行完整解码、时长、目录与章节路径映射检查。使用已有 current-catalog.json 快照，不连接或修改数据库；结果不代表本轮重新查询了数据库绑定。
- 全部25个视频自动完整解码通过；人工播放器抽查范围为用户确认的3个候选，不声称25个视频均经人工逐秒观看。

## 输出位置

- 备份：outputs/course-video-footer-fix/originals/
- 备份清单：outputs/course-video-footer-fix/backup-manifest.json
- 候选：outputs/course-video-footer-fix/candidates/
- 候选验证汇总：outputs/course-video-footer-fix/completed-results.json
- 提示文字区域验证：outputs/course-video-footer-fix/roi-verification.json
- 替换记录：outputs/course-video-footer-fix/replacement.json
- 正式视频哈希：outputs/course-video-footer-fix/videos-sha256.txt
- 指定脚本验收报告：outputs/course-video-footer-fix/acceptance/acceptance-20261010T133443402501Z.md
- 指定脚本验收数据：outputs/course-video-footer-fix/acceptance/acceptance-20261010T133443402501Z.json
- 验收报告哈希：outputs/course-video-footer-fix/acceptance/acceptance-20261010T133443402501Z.sha256
- 验收执行记录：outputs/course-video-footer-fix/acceptance-execution.json

## 范围遵守与后续状态

未修改数据库、后端代码、Spark或推荐系统；未执行Git操作或提交；未删除备份。本任务已完成并停止，不自动进入其他阶段。
