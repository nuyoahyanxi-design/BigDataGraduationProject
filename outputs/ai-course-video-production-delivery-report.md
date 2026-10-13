# AI课程视频生产交付报告

> 历史方案/验收补注（2026-10-13）：下文未生成、未导入、未验收或远程生产限制属于原阶段/方案的真实记录，不能用来判断当前正式教学媒体是否可播放。当前视频及批次状态见[答辩当前状态](../docs/defense-current-state.md)。不将旧方案未完成改写为该方案成功。

## 结论

制作资料整理完成，公共教师配置已选定；真实视频生产受到当前HeyGen连接多场景能力限制，首批未生成，未导入，未通过验收。不能将本报告视为视频交付成功。

## 资料与首批列表

已完整程序读取25份章节计划、口播及提示词，提取教学目标、场景脚本、PPT页面结构、预算时长，保存ai-course-video-delivery/chapter-production-catalog.json。用户已确认采用原章节和原方案，避免本轮最初新标题与既有章节错配。

| 章节 | 标题 | 最终目标路径 | 预算时长（未实测） | 生成状态 |
| --- | --- | --- | --- | --- |
| 6 | DataFrame与Schema教学视频 | frontend/public/videos/course_1069/chapter_006.mp4 | 4:14 | 未创建 |
| 7 | 筛选与列转换教学视频 | frontend/public/videos/course_1069/chapter_007.mp4 | 4:20 | 未提交 |
| 8 | 聚合与Spark SQL教学视频 | frontend/public/videos/course_1069/chapter_008.mp4 | 4:13 | 未提交 |
| 9 | Parquet读写教学视频 | frontend/public/videos/course_1069/chapter_009.mp4 | 4:16 | 未提交 |
| 10 | 学习行为清洗实践教学视频 | frontend/public/videos/course_1069/chapter_010.mp4 | 4:20 | 未提交 |

## HeyGen实际调用与阻塞

公共Avatar图库与目录、look目录、中文声音目录和账号查询均成功，说明连接可调用。账号套餐free；额度返回null，不能推断为0、足够或付费权限被拒绝。

经用户授权代选：Kenji Office 1，Look ID 66500d4366974ae5816201d1f07debc9。详细配置见ai-course-video-delivery/ai-teacher-template.md；年龄与中文自然度尚未实测。

向Video Agent提交章节6的完整多场景任务，指定上述公共look与中文声音，返回409 INVALID_ARGUMENT、prerequisite_status=missing、requiredTool=open_avatar_creator。无session_id/video_id，任务未创建。返回说明公共look仅可通过create_video_from_avatar生成单场景口播，不适用于当前Video Agent制作。不是已证实额度不足或OAuth缺失，也不是视频生成途中失败。

用户要求公共教师且不要继续询问，因此未启动私人数字分身采集、未请求照片/录音/同意录制。没有自动去掉教师或替换形象，也没有为不满足课件要求的单场景片额外提交付费任务。

## 可直接复制的任务

ai-course-video-delivery/first-batch/chapter_006/heygen-task.md至chapter_010/heygen-task.md各含完整原文脚本、代码、架构、PPT结构与口播。教师配置使用已确认的ai-teacher-template.md。它们是HeyGen编辑器的制作任务文本，不是已经执行的API任务；编辑器是否具备多场景/素材上传和导出权限需实际核实。

使用顺序：在支持公共Avatar课件多场景制作的HeyGen编辑器选择同一look与中文声音 → 导入每章五页课件/原文代码与图示 → 逐场景使用原文口播 → 预览字幕和术语 → 导出1080p MP4至outputs暂存 → 完整解码及时长审核后按标准文件名导入。当前仅有课件结构，没有真实PPT文件或已上传素材，不能声称任务文本会自动可靠生成正确代码课件。

## 验收与浏览器结果

没有新MP4，未执行新视频浏览器播放或完成动作。用户明确采用隔离验收，不写正式学习进度或事件。上一阶段样本播放和24项验收工具回归不代表本轮AI成片通过。

本轮再次执行只读全量验收：课程5、章节25、视频0、缺失25、异常0、通过0，结论未通过。报告：course-video-acceptance/acceptance-20261010T074943315808Z.md及同名JSON/SHA256。

全量工具固定25章：首批5章合格后仍有20缺失，整体应继续未通过；不得为了首批通过改验收门禁。当前环境尚缺可用FFmpeg，真实全量解码需提供可执行文件后完成，不自动安装。

## 剩余20章计划

详见ai-course-video-delivery/remaining-20-plan.md，包含20章名称、ID、路径、预算时长与顺序：RDD5章 → MySQL5章 → Hadoop5章 → Python机器学习5章。仅首批完成并通过后再生产，不已提交25个任务。

## 边界与修改

本轮仅新增阶段设计文档、资料提取辅助脚本和制作包/报告。业务代码、数据库、正式MP4目录、Spark、推荐公式、发布指针未修改；Git未提交，HEAD保持19b4739598a86a2307f62b135c7d27de2b78af1e。没有生成任何真实MP4、音频或课件。阶段目标尚未达成，待制作渠道可满足公共教师多场景能力及导出/解码条件后继续。
