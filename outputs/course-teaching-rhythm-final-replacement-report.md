# 课程视频教学节奏优化最终替换报告

完成日期：2026-10-10T23:28:46.778075+08:00（北京时间）。

## 最终结论

正式替换完成24章：本批次20个候选，加此前人工确认的chapter_007–010四个节奏优化候选。chapter_006当前正式版本保持不变。用户已确认上述候选人工试听通过。
指定backend/tools/accept_course_videos.py已实际运行并通过，退出码0：视频25、缺失0、异常0、通过25、accepted=true。

## 替换范围与版本

| 正式课程目录 | 替换章节 | 候选来源 |
| --- | --- | --- |
| course_1068 | chapter_001–005 | outputs/course-teaching-rhythm-batch/candidates/ |
| course_1069 | chapter_007–010 | outputs/course-teaching-rhythm/candidates/（已确认节奏优化版） |
| course_1070 | chapter_059–063 | outputs/course-teaching-rhythm-batch/candidates/ |
| course_1071 | chapter_054–058 | outputs/course-teaching-rhythm-batch/candidates/ |
| course_1072 | chapter_011–015 | outputs/course-teaching-rhythm-batch/candidates/ |

007–010使用剪短静默的教学节奏版本，没有使用更早仅补充旁白且保留原时长的候选。第6章未替换；没有重新生成、剪辑或编码任何视频。

## 替换前备份

备份根目录：D:\BigDataGraduationProject\outputs\course-teaching-rhythm-final-replacement\originals\。包含5个课程子目录、25个chapter_<id>.original.mp4。
25份当前正式原片均在第一份正式替换发生前完成备份并核对SHA256。替换后再次校验25/25一致。历史originals、候选、音轨及字幕保留，不删除或覆盖旧备份。
备份清单：outputs/course-teaching-rhythm-final-replacement/backup-manifest.json。

## 新旧视频校验

- 24个正式成品SHA256与对应已验证候选完全一致；替换前SHA256与本阶段备份完全一致。
- chapter_006正式文件、替换前备份和旧SHA256一致。
- 所有候选在替换前重新核对哈希、完整解码通过记录、正常讲解PCM保护、保留帧像素一致、>8秒静默为0及字幕检查记录。用户人工试听确认与自动验证分别记录。
- 正式文件名和5个课程目录结构不变，24个节奏版本仍为1280×720、16:9。原片和候选未显式打印DAR时，以像素尺寸比及无矛盾宽高比声明验证；保留画面的逐帧像素验证已在候选阶段通过。
- 758个受保护后端、Spark、推荐、数据及发布指针相关文件哈希未变化；正式目录无残留.rhythm.part。

| 课程/章节 | 原时长→正式新时长（秒） | 原片备份校验 | 正式/候选校验 |
| --- | --- | --- | --- |
| 1068/chapter_001 | 259.00→229.00 | 通过 | 通过 |
| 1068/chapter_002 | 261.00→232.16 | 通过 | 通过 |
| 1068/chapter_003 | 261.00→237.04 | 通过 | 通过 |
| 1068/chapter_004 | 258.00→229.24 | 通过 | 通过 |
| 1068/chapter_005 | 253.00→228.16 | 通过 | 通过 |
| 1070/chapter_059 | 251.00→225.56 | 通过 | 通过 |
| 1070/chapter_060 | 257.00→228.80 | 通过 | 通过 |
| 1070/chapter_061 | 258.00→223.88 | 通过 | 通过 |
| 1070/chapter_062 | 258.00→227.24 | 通过 | 通过 |
| 1070/chapter_063 | 256.60→236.80 | 通过 | 通过 |
| 1071/chapter_054 | 259.56→229.92 | 通过 | 通过 |
| 1071/chapter_055 | 264.00→235.52 | 通过 | 通过 |
| 1071/chapter_056 | 254.00→231.12 | 通过 | 通过 |
| 1071/chapter_057 | 259.44→234.28 | 通过 | 通过 |
| 1071/chapter_058 | 258.00→227.00 | 通过 | 通过 |
| 1072/chapter_011 | 263.00→230.96 | 通过 | 通过 |
| 1072/chapter_012 | 257.00→222.68 | 通过 | 通过 |
| 1072/chapter_013 | 256.00→226.40 | 通过 | 通过 |
| 1072/chapter_014 | 253.00→230.24 | 通过 | 通过 |
| 1072/chapter_015 | 261.00→231.40 | 通过 | 通过 |
| 1069/chapter_007 | 260.16→232.44 | 通过 | 通过 |
| 1069/chapter_008 | 253.20→225.28 | 通过 | 通过 |
| 1069/chapter_009 | 256.00→221.96 | 通过 | 通过 |
| 1069/chapter_010 | 261.36→235.68 | 通过 | 通过 |

完整新旧SHA256及对应来源：replacement.json；当前25视频SHA256：videos-sha256.txt；最终核对：final-integrity.json，均位于本阶段证据目录。

## 视频验收结果

| 项目 | 实际结果 |
| --- | --- |
| 课程 | 5 |
| 视频 | 25 |
| 缺失 | 0 |
| 异常 | 0 |
| 通过 | 25 |
| accepted | true |
| 退出码 | 0 |

实际执行原验收脚本，检查正式目录、固定章节规则、映射、文件稳定性、时长范围及全片视频/音频解码。使用既有outputs/course-video-footer-fix/current-catalog.json目录快照，不连接数据库；这不代表本轮重新查询了数据库绑定。
首次默认Python环境因缺少Starlette而在导入时退出，未执行视频验收；随后通过work/accept-teaching-rhythm-final.py复用现有work/free-video-runtime依赖，未安装或修改环境、未编辑原验收脚本。最终实际验收退出码0，初次失败另存acceptance-first-attempt.json。

验收报告：outputs/course-teaching-rhythm-final-replacement/acceptance/acceptance-20261010T152724331653Z.md
验收数据：outputs/course-teaching-rhythm-final-replacement/acceptance/acceptance-20261010T152724331653Z.json
验收报告校验：outputs/course-teaching-rhythm-final-replacement/acceptance/acceptance-20261010T152724331653Z.sha256
执行记录：outputs/course-teaching-rhythm-final-replacement/acceptance-execution.json。

## 字幕与范围边界

新完整SRT及supplement.srt留在对应候选目录，已随候选时间轴验证。原烧录字幕仍在视频帧中；新增旁白字幕需外部SRT加载，当前网页播放器不会自动加载，本轮未修改播放器或往正式目录增加字幕文件。
未修改数据库、后端代码、Spark、推荐系统或章节绑定；未运行Spark、推荐发布、暂存或提交Git。未重新编码媒体。正式替换阶段已完成并停止，后续冻结/提交等待新的明确授权。
