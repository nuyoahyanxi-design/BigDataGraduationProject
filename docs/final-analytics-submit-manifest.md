# 本轮最终提交清单

本文件仅整理提交边界；未暂存、未提交。代码、数据库与视频未修改。

## 分组与顺序

1. 核心：章节行为统计、统一进度、正式课程范围、测试、设计及三份验收报告。
2. 依赖：保留共享页面已经使用的课程封面与独立公开数据展示依赖；不把公开数据计入平台正式统计。
3. 页面接入：包含现有共享页面中的美化改动，按整文件保存，不声称已逐行剥离视觉改动。

分组补丁位于 work/git-submit-organization/（已忽略），为相对当前HEAD的审阅补丁，不能直接应用到已有同样改动的工作区。三组应配套审阅；单组不保证完整功能。

## 01-core（32个文件）

- .gitignore
- backend/app/core/resource_scope.py
- backend/app/schemas/dashboard.py
- backend/app/schemas/recommendations.py
- backend/app/schemas/resources.py
- backend/app/services/course_presentation.py
- backend/app/services/courses.py
- backend/app/services/dashboard.py
- backend/app/services/learning.py
- backend/app/services/recommendations.py
- backend/app/services/resources.py
- spark/jobs/clean.py
- spark/jobs/quality.py
- spark/jobs/user_profiles.py
- spark/jobs/recommendations.py
- spark/jobs/dashboard_metrics.py
- spark/utils/chapter_analytics.py
- spark/utils/progress.py
- spark/utils/resource_scope.py
- spark/utils/profiles.py
- spark/utils/recommendations.py
- spark/utils/schemas.py
- tests/test_chapter_analytics.py
- tests/test_chapter_display.py
- tests/test_unified_progress.py
- tests/test_formal_course_scope.py
- docs/chapter-analytics-design.md
- docs/unified-progress-design.md
- docs/formal-course-scope-design.md
- outputs/chapter-analytics-acceptance-report.md
- outputs/unified-progress-acceptance-report.md
- outputs/formal-course-scope-acceptance-report.md

## 02-existing-display-dependencies（14个文件）

- frontend/src/components/ResourceCover.vue
- frontend/public/images/course-covers/general.svg
- frontend/public/images/course-covers/hdfs.svg
- frontend/public/images/course-covers/machine-learning.svg
- frontend/public/images/course-covers/mysql.svg
- frontend/public/images/course-covers/pyspark.svg
- frontend/public/images/course-covers/rdd.svg
- frontend/src/components/PublicEducationDashboard.vue
- frontend/src/types/public-education.ts
- frontend/src/api/dashboard.ts
- backend/app/api/dashboard.py
- backend/app/schemas/public_education.py
- backend/app/services/public_education.py
- backend/tests/test_public_education.py

## 03-shared-pages（12个文件）

- frontend/src/types/courses.ts
- frontend/src/types/dashboard.ts
- frontend/src/types/recommendations.ts
- frontend/src/types/resources.ts
- frontend/src/views/CourseLearningView.vue
- frontend/src/views/RecommendationsView.vue
- frontend/src/views/DashboardView.vue
- frontend/src/views/ResourcesView.vue
- frontend/src/views/ResourceDetailView.vue
- frontend/src/services/dashboard-charts.ts
- frontend/tests/courses.test.ts
- frontend/tests/dashboard.test.ts

## 其他改动保留，未纳入

- backend/app/api/users.py
- backend/app/core/security.py
- backend/app/models/__init__.py
- backend/app/models/auth_recovery.py
- backend/app/schemas/users.py
- backend/app/services/auth_challenges.py
- backend/app/services/users.py
- backend/tests/conftest.py
- backend/tests/test_auth_experience.py
- backend/tests/test_foundation.py
- backend/tests/test_public_data_intake.py
- backend/tools/apply_auth_recovery_migration.py
- database/migrations/008_create_auth_recovery_codes.sql
- docs/course-learning-visual-refresh-design.md
- docs/dashboard-first-screen-design.md
- docs/defense-demo-script.md
- docs/defense-presentation-copy-design.md
- docs/defense-twenty-sentences.md
- docs/login-experience-design.md
- docs/mock-defense-training.md
- docs/oulad-analysis-design.md
- docs/oulad-data-source.md
- docs/platform-activity-session-design.md
- docs/platform-decoration-design.md
- docs/platform-spark-refresh-design.md
- docs/platform-visual-refresh-design.md
- docs/public-education-data-design.md
- docs/real-data-and-defense-plan.md
- docs/resource-cover-design.md
- docs/resource-detail-visual-design.md
- frontend/src/api/auth.ts
- frontend/src/api/http.ts
- frontend/src/components/AppShell.vue
- frontend/src/components/ChapterTeachingContent.vue
- frontend/src/components/RecoverySettings.vue
- frontend/src/components/WorkspaceArt.vue
- frontend/src/stores/auth.ts
- frontend/src/styles/base.css
- frontend/src/types/auth.ts
- frontend/src/views/AdminCourseEditView.vue
- frontend/src/views/AdminCoursesView.vue
- frontend/src/views/AdminView.vue
- frontend/src/views/AiAssistantView.vue
- frontend/src/views/HomeView.vue
- frontend/src/views/LoginView.vue
- frontend/tests/auth-persistence.test.ts
- scripts/audit_oulad_source.py
- spark/jobs/oulad_analysis.py

## 安全与验证

- 账号密码文件只加入精确忽略规则，未读取、未删除。
- 运行数据、候选视频、备份、缓存、日志和分组补丁继续留在忽略范围。
- 三份既有验收报告保留原文，未重跑Spark、测试或伪造新验收结果。
- 共享页面依赖已在第2组列全；认证、恢复码、其他视觉页面及答辩材料改动继续保留。
- staged=0；没有git add、commit或push。
- 未跟踪文件须由后续定向暂存纳入；本清单不代表已进入Git索引。
