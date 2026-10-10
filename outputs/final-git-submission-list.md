# 最终Git提交清单

检查日期：2026-10-10T23:39:55（本机时间）。

## 结论

整理完成，当前拟提交变更文件 **105个**（已跟踪修改15个，未跟踪90个）；正式MP4 **25个**。本轮未执行git add或git commit，25个视频仍未跟踪，只是已放行且列入提交候选。

提交候选文件当前大小合计 **147,525,614字节**（147.53 MB / 140.69 MiB），其中视频147,176,353字节。此为变更候选完整文件大小，包含本清单，不是Git对象压缩后大小、增量上传大小或仓库全量大小。

未跟踪分组：backend 7、frontend 32、docs 23、outputs 28。暂存0；HEAD 19b4739598a86a2307f62b135c7d27de2b78af1e。

## 保留报告列表

- outputs/chapter-006-edge-tts-quality-report.md
- outputs/chapter-006-video-quality-report.md
- outputs/course-teaching-rhythm-final-replacement-report.md
- outputs/course-video-footer-fix-report.md
- outputs/defense-demo-flow-and-screenshot-list.md
- outputs/defense-demo-optimization-report.md
- outputs/defense-final-acceptance-report.md
- outputs/defense-risk-list.md
- outputs/demo-account-setup-report.md
- outputs/final-git-submission-list.md
- outputs/final-system-acceptance-report.md
- outputs/formal-course-chapters-acceptance-report.md
- outputs/formal-release-readiness-report.md
- outputs/formal-release-result-report.md
- outputs/graduation-defense-demo-script.md
- outputs/graduation-final-freeze-check-report.md
- outputs/graduation-final-status-report.md
- outputs/post-release-browser-acceptance-report.md
- outputs/real-account-browser-integration-report.md
- outputs/windows-one-click-start-acceptance-report.md

保留的旧阶段报告是历史证据，日期与旧视频时长/哈希不代表当前；当前视频以course-teaching-rhythm-final-replacement-report.md及最新acceptance为准。演示与发布报告保留其原验收边界，不视为本轮重新运行结果。

## 最新视频证据

- outputs/course-teaching-rhythm-final-replacement/acceptance/：当前3个文件全部放行（JSON、Markdown、SHA256）；目录未设置额外日志扩展名放行限制。
- 同目录上级保留：backup-manifest.json、replacement.json、final-integrity.json、acceptance-execution.json、videos-sha256.txt。
- 原片备份及候选不提交；备份清单含本机路径，备份文件仍在本机。
- 旧course-video-footer-fix/及git-final-freeze/过程证据改为忽略，仅保留有最终价值的根目录报告。

## 正式视频列表

- frontend/public/videos/course_1068/chapter_001.mp4
- frontend/public/videos/course_1068/chapter_002.mp4
- frontend/public/videos/course_1068/chapter_003.mp4
- frontend/public/videos/course_1068/chapter_004.mp4
- frontend/public/videos/course_1068/chapter_005.mp4
- frontend/public/videos/course_1069/chapter_006.mp4
- frontend/public/videos/course_1069/chapter_007.mp4
- frontend/public/videos/course_1069/chapter_008.mp4
- frontend/public/videos/course_1069/chapter_009.mp4
- frontend/public/videos/course_1069/chapter_010.mp4
- frontend/public/videos/course_1070/chapter_059.mp4
- frontend/public/videos/course_1070/chapter_060.mp4
- frontend/public/videos/course_1070/chapter_061.mp4
- frontend/public/videos/course_1070/chapter_062.mp4
- frontend/public/videos/course_1070/chapter_063.mp4
- frontend/public/videos/course_1071/chapter_054.mp4
- frontend/public/videos/course_1071/chapter_055.mp4
- frontend/public/videos/course_1071/chapter_056.mp4
- frontend/public/videos/course_1071/chapter_057.mp4
- frontend/public/videos/course_1071/chapter_058.mp4
- frontend/public/videos/course_1072/chapter_011.mp4
- frontend/public/videos/course_1072/chapter_012.mp4
- frontend/public/videos/course_1072/chapter_013.mp4
- frontend/public/videos/course_1072/chapter_014.mp4
- frontend/public/videos/course_1072/chapter_015.mp4

## 忽略目录列表

- work/
- data/
- wsl/
- spark-experiments/
- environments/mysql-admin-tools/
- outputs/course-teaching-rhythm-batch/candidates/
- outputs/course-teaching-rhythm-batch/originals/
- outputs/course-teaching-rhythm/candidates/
- outputs/course-teaching-rhythm/originals/
- outputs/course-teaching-rhythm-final-replacement/originals/
- outputs/course-video-footer-fix/
- outputs/course-narration-coverage/
- outputs/all-course-edge-tts/
- outputs/git-final-freeze/
- backend/.pytest_cache/

- 其他未白名单的outputs生成目录，以及node_modules、dist、build、__pycache__等继续按已有规则忽略。
- 临时TTS/FFmpeg产物、*.part、*.tmp、*.temp、日志及pytest缓存不纳入。
- 不删除任何报告、备份或中间文件。

## 本轮未纳入的根目录报告

- outputs/admin-course-list-correction-acceptance-report.md
- outputs/admin-course-management-acceptance-report.md
- outputs/admin-course-multipage-acceptance-report.md
- outputs/admin-module-acceptance-report.md
- outputs/agnes-adapter-diagnostic-report.md
- outputs/agnes-compatibility-acceptance-report.md
- outputs/agnes-key-loading-diagnostic-report.md
- outputs/agnes-runtime-diagnostic-acceptance-report.md
- outputs/agnes-startup-configuration-acceptance-report.md
- outputs/agnes-timeout-diagnostic-report.md
- outputs/ai-429-fix-acceptance-report.md
- outputs/ai-answer-completeness-acceptance-report.md
- outputs/ai-answer-length-acceptance-report.md
- outputs/ai-assistant-acceptance-report.md
- outputs/ai-assistant-design-report.md
- outputs/ai-course-video-access-acceptance-report.md
- outputs/ai-course-video-auto-import-report.md
- outputs/ai-course-video-final-acceptance-report.md
- outputs/ai-course-video-implementation-report.md
- outputs/ai-course-video-production-acceptance-report.md
- outputs/ai-course-video-production-delivery-report.md
- outputs/ai-course-video-production-plan.md
- outputs/ai-professional-prompt-acceptance-report.md
- outputs/ai-real-model-acceptance-report.md
- outputs/ai-teaching-video-design-acceptance-report.md
- outputs/ai-timeout-diagnostic-report.md
- outputs/ai-timeout-ux-acceptance-report.md
- outputs/all-course-voice-quality-report.md
- outputs/backend-foundation-acceptance-report.md
- outputs/course-ai-assistant-v1-acceptance-report.md
- outputs/course-ai-assistant-v1-design-report.md
- outputs/course-ai-final-browser-acceptance-report.md
- outputs/course-ai-fixed-input-acceptance-report.md
- outputs/course-ai-layout-permissions-acceptance-report.md
- outputs/course-ai-overview-acceptance-report.md
- outputs/course-ai-relevance-filter-acceptance-report.md
- outputs/course-ai-workspace-acceptance-report.md
- outputs/course-flow-optimization-acceptance-report.md
- outputs/course-learning-acceptance-report.md
- outputs/course-learning-ui-acceptance-report.md
- outputs/course-narration-coverage-test-report.md
- outputs/course-navigation-fix-acceptance-report.md
- outputs/course-teaching-content-acceptance-report.md
- outputs/course-teaching-rhythm-batch-optimization-report.md
- outputs/course-teaching-rhythm-optimization-report.md
- outputs/dashboard-acceptance-report.md
- outputs/database-design-acceptance-report.md
- outputs/database-implementation-acceptance-report.md
- outputs/demo-account-password-source-check.md
- outputs/environment-recovery-acceptance-report.md
- outputs/experiment-data-preparation-acceptance-report.md
- outputs/final-system-acceptance-report.previous-20261009.md
- outputs/formal-release-preparation-execution-report.md
- outputs/free-course-video-alternative-report.md
- outputs/free-course-video-production-report.md
- outputs/frontend-auth-acceptance-report.md
- outputs/frontend-foundation-acceptance-report.md
- outputs/frontend-login-proxy-fix-acceptance-report.md
- outputs/frontend-resource-module-acceptance-report.md
- outputs/git-baseline-acceptance-report.md
- outputs/git-final-freeze-report.md
- outputs/heygen-720p-compatibility-report.md
- outputs/heygen-avatar-iii-compatibility-report.md
- outputs/heygen-standard-course-acceptance-report.md
- outputs/home-null-safety-acceptance-report.md
- outputs/learning-behavior-stability-acceptance-report.md
- outputs/learning-event-module-acceptance-report.md
- outputs/local-development-environment-acceptance-report.md
- outputs/project-freeze-acceptance-report.md
- outputs/project-initialization-report.md
- outputs/real-browser-precheck-report.md
- outputs/recommendation-copy-acceptance-report.md
- outputs/recommendation-display-acceptance-report.md
- outputs/recommendation-experiment-acceptance-report.md
- outputs/recommendation-ranking-optimization-acceptance-report.md
- outputs/recommendation-system-acceptance-report.md
- outputs/resource-module-acceptance-report.md
- outputs/spark-batch-republication-diagnostic-report.md
- outputs/spark-data-pipeline-acceptance-report.md
- outputs/spark-publication-stability-acceptance-report.md
- outputs/user-module-acceptance-report.md
- outputs/user-profile-acceptance-report.md
- outputs/windows-local-config-acceptance-report.md
- outputs/wsl-proxy-startup-acceptance-report.md

## 最大候选文件

| 文件 | 字节 |
|---|---:|
| frontend/public/videos/course_1070/chapter_063.mp4 | 6,528,620 |
| frontend/public/videos/course_1069/chapter_010.mp4 | 6,486,960 |
| frontend/public/videos/course_1068/chapter_002.mp4 | 6,244,437 |
| frontend/public/videos/course_1071/chapter_054.mp4 | 6,244,316 |
| frontend/public/videos/course_1071/chapter_056.mp4 | 6,218,856 |

## 验证结果与边界

- 25个正式MP4白名单全部通过，无视频被忽略；未跟踪25，已跟踪0。
- 25个当前MP4 SHA256与最新已通过25/0/0/25验收记录一致；本轮未重复解码或重编码。
- 3个最新验收文件均可加入Git；候选、备份、缓存目录忽略核验通过。
- 758个既有受保护源码、数据及发布指针哈希一致；git diff --check通过。
- 候选文本未发现所检查的私钥、典型令牌及含密码数据库URL模式；属于静态启发式检查。
- .gitignore及文档变更以外未改业务代码、数据库、视频、Spark或推荐系统；未运行Spark、未暂存、未提交。
- 两个原先已跟踪的outputs/start-*.py启动工具继续随仓库保留；忽略规则不会将已跟踪文件自动移出。

## 完整拟提交变更清单

```text
 M .gitignore
 M backend/app/main.py
 M backend/app/services/courses.py
 M frontend/public/videos/README.md
 M frontend/src/components/LearningVideo.vue
 M frontend/src/services/dashboard-charts.ts
 M frontend/src/types/recommendations.ts
 M frontend/src/views/CourseLearningView.vue
 M frontend/src/views/DashboardView.vue
 M frontend/src/views/RecommendationsView.vue
 M frontend/tests/course-flow-components.test.ts
 M frontend/tests/courses.test.ts
 M frontend/tests/dashboard.test.ts
 M frontend/tests/recommendations.test.ts
 M frontend/vite.config.ts
?? backend/app/core/media.py
?? backend/app/core/video_catalog.py
?? backend/tests/test_video_assets.py
?? backend/tests/test_video_auto_import.py
?? backend/tests/test_video_final_acceptance.py
?? backend/tools/accept_course_videos.py
?? backend/tools/scan_course_videos.py
?? docs/ai-course-video-access-design.md
?? docs/ai-course-video-auto-import-design.md
?? docs/ai-course-video-delivery-design.md
?? docs/ai-course-video-final-acceptance-design.md
?? docs/ai-course-video-production-design.md
?? docs/all-course-edge-tts-design.md
?? docs/chapter-006-edge-tts-design.md
?? docs/chapter-006-video-quality-design.md
?? docs/course-narration-coverage-design.md
?? docs/course-teaching-rhythm-batch-design.md
?? docs/course-teaching-rhythm-design.md
?? docs/course-teaching-rhythm-final-replacement-design.md
?? docs/course-video-footer-fix-design.md
?? docs/defense-demo-optimization-design.md
?? docs/defense-readiness-review-design.md
?? docs/final-freeze-check-design.md
?? docs/final-git-submission-design.md
?? docs/free-course-video-alternative-design.md
?? docs/free-course-video-production-design.md
?? docs/git-final-freeze-design.md
?? docs/heygen-720p-compatibility-design.md
?? docs/heygen-avatar-iii-compatibility-design.md
?? docs/heygen-standard-course-design.md
?? frontend/public/videos/course_1068/.gitkeep
?? frontend/public/videos/course_1068/chapter_001.mp4
?? frontend/public/videos/course_1068/chapter_002.mp4
?? frontend/public/videos/course_1068/chapter_003.mp4
?? frontend/public/videos/course_1068/chapter_004.mp4
?? frontend/public/videos/course_1068/chapter_005.mp4
?? frontend/public/videos/course_1069/.gitkeep
?? frontend/public/videos/course_1069/chapter_006.mp4
?? frontend/public/videos/course_1069/chapter_007.mp4
?? frontend/public/videos/course_1069/chapter_008.mp4
?? frontend/public/videos/course_1069/chapter_009.mp4
?? frontend/public/videos/course_1069/chapter_010.mp4
?? frontend/public/videos/course_1070/.gitkeep
?? frontend/public/videos/course_1070/chapter_059.mp4
?? frontend/public/videos/course_1070/chapter_060.mp4
?? frontend/public/videos/course_1070/chapter_061.mp4
?? frontend/public/videos/course_1070/chapter_062.mp4
?? frontend/public/videos/course_1070/chapter_063.mp4
?? frontend/public/videos/course_1071/.gitkeep
?? frontend/public/videos/course_1071/chapter_054.mp4
?? frontend/public/videos/course_1071/chapter_055.mp4
?? frontend/public/videos/course_1071/chapter_056.mp4
?? frontend/public/videos/course_1071/chapter_057.mp4
?? frontend/public/videos/course_1071/chapter_058.mp4
?? frontend/public/videos/course_1072/.gitkeep
?? frontend/public/videos/course_1072/chapter_011.mp4
?? frontend/public/videos/course_1072/chapter_012.mp4
?? frontend/public/videos/course_1072/chapter_013.mp4
?? frontend/public/videos/course_1072/chapter_014.mp4
?? frontend/public/videos/course_1072/chapter_015.mp4
?? frontend/tests/video-import-ui.ts
?? frontend/tests/video-player-components.test.ts
?? outputs/chapter-006-edge-tts-quality-report.md
?? outputs/chapter-006-video-quality-report.md
?? outputs/course-teaching-rhythm-final-replacement-report.md
?? outputs/course-teaching-rhythm-final-replacement/acceptance-execution.json
?? outputs/course-teaching-rhythm-final-replacement/acceptance/acceptance-20261010T152724331653Z.json
?? outputs/course-teaching-rhythm-final-replacement/acceptance/acceptance-20261010T152724331653Z.md
?? outputs/course-teaching-rhythm-final-replacement/acceptance/acceptance-20261010T152724331653Z.sha256
?? outputs/course-teaching-rhythm-final-replacement/backup-manifest.json
?? outputs/course-teaching-rhythm-final-replacement/final-integrity.json
?? outputs/course-teaching-rhythm-final-replacement/replacement.json
?? outputs/course-teaching-rhythm-final-replacement/videos-sha256.txt
?? outputs/course-video-footer-fix-report.md
?? outputs/defense-demo-flow-and-screenshot-list.md
?? outputs/defense-demo-optimization-report.md
?? outputs/defense-final-acceptance-report.md
?? outputs/defense-risk-list.md
?? outputs/demo-account-setup-report.md
?? outputs/final-git-submission-list.md
?? outputs/final-system-acceptance-report.md
?? outputs/formal-course-chapters-acceptance-report.md
?? outputs/formal-release-readiness-report.md
?? outputs/formal-release-result-report.md
?? outputs/graduation-defense-demo-script.md
?? outputs/graduation-final-freeze-check-report.md
?? outputs/graduation-final-status-report.md
?? outputs/post-release-browser-acceptance-report.md
?? outputs/real-account-browser-integration-report.md
?? outputs/windows-one-click-start-acceptance-report.md
```

本清单为工作区候选清单，尚非Git暂存清单。整理完成后停止，后续暂存/提交需按用户新的明确指令执行。
