# 剩余改动最终提交清单

整理日期：2026-10-24。未暂存、未提交；当前基线 ca697535d3f6903785aa63838da5083346dacc97。

原48项加12份原阶段最终验收报告，以及.gitignore、本清单和本次整理报告，共63个待提交文件。
建议顺序：认证→美化→公开数据→辅助文档。登录页面含认证自身样式，HomeView同时依赖RecoverySettings和WorkspaceArt，美化应在认证之后。已提交的公开数据API、类型、组件不重复计入。
旧验收报告原文不变，数字只属于原阶段；原设计和答辩训练内容均保留为历史，下方新状态说明优先。原始数据与证据附件仍被忽略，源码提交不保证跨机器已有数据和运行环境。
迁移脚本只交付，不运行、不自动修改数据库。本次没有重跑构建、测试、Spark或浏览器验收，不把历史通过结果当作本轮新测试。

## 认证（21项）

- backend/app/api/users.py
- backend/app/core/security.py
- backend/app/models/__init__.py
- backend/app/schemas/users.py
- backend/app/services/users.py
- backend/tests/conftest.py
- backend/tests/test_foundation.py
- backend/app/models/auth_recovery.py
- backend/app/services/auth_challenges.py
- backend/tests/test_auth_experience.py
- backend/tools/apply_auth_recovery_migration.py
- database/migrations/008_create_auth_recovery_codes.sql
- frontend/src/api/auth.ts
- frontend/src/api/http.ts
- frontend/src/stores/auth.ts
- frontend/src/types/auth.ts
- frontend/src/views/LoginView.vue
- frontend/src/components/RecoverySettings.vue
- frontend/tests/auth-persistence.test.ts
- docs/login-experience-design.md
- outputs/login-experience-acceptance-report.md

## 美化（23项）

- frontend/src/components/AppShell.vue
- frontend/src/components/ChapterTeachingContent.vue
- frontend/src/styles/base.css
- frontend/src/views/AdminCourseEditView.vue
- frontend/src/views/AdminCoursesView.vue
- frontend/src/views/AdminView.vue
- frontend/src/views/AiAssistantView.vue
- frontend/src/views/HomeView.vue
- docs/course-learning-visual-refresh-design.md
- docs/dashboard-first-screen-design.md
- docs/defense-presentation-copy-design.md
- docs/platform-decoration-design.md
- docs/platform-visual-refresh-design.md
- docs/resource-cover-design.md
- docs/resource-detail-visual-design.md
- frontend/src/components/WorkspaceArt.vue
- outputs/course-learning-visual-refresh-acceptance-report.md
- outputs/dashboard-first-screen-acceptance-report.md
- outputs/defense-presentation-copy-acceptance-report.md
- outputs/platform-decoration-acceptance-report.md
- outputs/platform-visual-refresh-acceptance-report.md
- outputs/resource-cover-acceptance-report.md
- outputs/resource-detail-visual-acceptance-report.md

## 公开数据（9项）

- backend/tests/test_public_data_intake.py
- scripts/audit_oulad_source.py
- spark/jobs/oulad_analysis.py
- docs/oulad-analysis-design.md
- docs/oulad-data-source.md
- docs/public-education-data-design.md
- docs/real-data-and-defense-plan.md
- outputs/public-education-data-acceptance-report.md
- outputs/oulad-analysis-acceptance-report.md

## 辅助文档（10项）

- docs/defense-demo-script.md
- docs/defense-twenty-sentences.md
- docs/mock-defense-training.md
- docs/platform-activity-session-design.md
- docs/platform-spark-refresh-design.md
- outputs/platform-activity-session-acceptance-report.md
- outputs/platform-spark-refresh-acceptance-report.md
- .gitignore
- docs/remaining-changes-submit-manifest.md
- outputs/remaining-changes-organization-acceptance-report.md

## 保留与风险

- 账号密码文件继续精确忽略，未读取；不提交令牌、恢复码或环境凭据。
- 12份验收报告以文件级白名单放行，不放行其目录、日志、原始CSV/ZIP、运行批次或截图。
- 认证验证码/限流是单进程内存实现；恢复码表需目标环境显式迁移，既有账号需自行设置恢复码。
- OULAD是外部历史数据，不等于平台用户；本平台演示行为不是大规模学生效果实验。
- 历史标签保持不变，本轮工作区未形成新冻结标签。
- docs/final-analytics-submit-manifest.md及上轮整理验收报告已经随前次提交保存，继续作为历史记录，不追写。
- 全部业务源码与本次整理前摘要一致；视频按25个保护摘要核对。
