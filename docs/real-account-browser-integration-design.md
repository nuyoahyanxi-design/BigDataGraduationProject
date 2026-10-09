# 真实账号浏览器全流程联调方案

日期：2026-10-05。范围仅为已实现系统的验收，不新增业务功能。

## 目标与技术方案

使用 Computer 操作正式 Vue 页面 http://localhost:5173，用户手工输入 admin_demo 与 student_demo 既有密码。浏览器不读取凭据，不访问 tests 模拟页面。FastAPI 连接现有 MySQL。现有 Spark 任务依次执行 pipeline、user_profiles、recommendations、dashboard_metrics。

## 流程与数据模型

管理员通过正式界面查看用户，创建并发布一条自编演示资源。学习者按浏览、开始、收藏、取消收藏、再次收藏、完成顺序操作。核对 learning_events、learning_progress、favorites；暂停页面写入后抽取五表快照，形成 ODS/DWD，并发布画像、推荐和看板。最后回访正式推荐页与管理员页面。

## 验证方法与实现边界

页面状态、截图、服务 HTTP 状态日志、只读数据库证据和 Spark 批次元数据交叉验证。密码、JWT 和 Cookie 不进入任何报告或截图。所有新学习行为由正式界面和正式 API 产生，不直接写数据库，不修改既有账号密码或数据库结构。结果记录到 outputs/real-account-browser-integration-report.md；未完成步骤明确保留，不宣称通过。
