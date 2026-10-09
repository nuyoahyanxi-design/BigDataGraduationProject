# 数据库迁移与验证

AI P2增量迁移顺序001→002→003→004。仅新增`ai_qa_records`，不改原七表。
WSL激活现有环境后，从项目根执行`PYTHONPATH=backend python database/apply_ai_migration.py`。
脚本执行004前后比对原表结构摘要和行数，验证新表映射与约束；重复执行仅验证已存在表，不自动改表。
AI关闭时主系统不要求新表。回退先设`AI_ASSISTANT_ENABLED=false`；保留历史表，不自动DROP。
详细配置与接入验证边界见`docs/ai-assistant-implementation.md`。

目标数据库：`bigdata_graduation`；MySQL 8.0.45，InnoDB，utf8mb4_unicode_ci，应用以 UTC 写入时间。

## 执行方式与顺序

1. 阅读 docs/database-design.md 和 docs/database-implementation.md，备份已有数据库。
2. 连接现有 Windows MySQL 3306，使用毕设专用账号。密码由安全凭据存储提供，不放在 SQL 或命令参数中。
3. 在 MySQL 客户端执行 migrations/001_create_core_tables.sql（先 users，后 resources，再 learning_progress、favorites、learning_events）。迁移会创建不存在的数据库；若数据库已存在，先确认字符集和空表状态。
4. Windows 可使用已有 Python 管理运行时执行 `python database/verify_core_database.py --migrate`。脚本从 Windows 凭据管理器读取凭据，拒绝非空数据库，执行迁移并验证。
5. 使用 `python database/verify_core_database.py --seed` 写入少量测试样本并完成行为及约束测试；不带参数只检查结构。Python 需可导入现有 environments/mysql-admin-tools 内的 PyMySQL 和 keyring。

SQL 不包含业务数据。测试工具不会创建后端接口，不是生产迁移框架。不要重复执行迁移；重复执行应报表已存在，而不是掩盖结构差异。

## 回滚

用户画像阶段新增迁移 `migrations/002_create_user_profiles.sql`，在 001 后执行，仅增加 user_profiles 结果表。使用已有环境变量连接 bigdata_graduation，执行一次；MySQL DDL 隐式提交，重复执行应报已存在。核对 `SHOW CREATE TABLE user_profiles` 的七列、联合主键、批次索引及用户外键。经备份并取得删除授权后可单独移除该结果表；它不改变原五张业务表。

推荐阶段新增 `migrations/003_create_recommendation_results.sql`，顺序为 001→002→003，仅创建推荐结果表。使用已有 MYSQL_* 环境变量和 PyMySQL 连接后读取 SQL 执行；密码不能写入命令或 SQL。迁移无业务数据、不重复执行、不使用 IF NOT EXISTS 掩盖结构变化。核对七列、联合主键、同用户批次算法排名唯一索引、批次索引、两个 RESTRICT 外键及四个 CHECK。MySQL 为资源外键自动建立辅助索引。旧 verify_core_database.py 用于初始五表阶段；当前完整清单通过 backend 基础回归及 Spark 推荐测试核验。结果表回滚必须备份并获得删除授权后单独移除 recommendation_results，本阶段不执行回滚，不删除历史结果。

本阶段不自动执行破坏性回滚。MySQL DDL 隐式提交，失败后应核对已创建表。

确认备份及删除授权后，逆依赖顺序移除 learning_events、favorites、learning_progress、resources、users；不要直接删除整个数据库或关闭外键检查绕过依赖。存在业务数据时优先恢复备份或另行设计修复迁移。

测试数据清理由验收报告记录的样本 ID 精确定位，先事件、收藏、进度，再资源和用户；不按模糊匹配删除正常业务数据。本阶段样本保留供人工查看。

## 课程章节迁移005

005_create_course_learning.sql新增course_chapters、chapter_progress、chapter_events三表，不ALTER原表，不删除旧数据。MySQL8、InnoDB、utf8mb4，外键均限制删除，章节位置及事件UUID唯一。

执行顺序001→002→003→004→005。当前本机005已执行，不再重复CREATE。首次部署可在现有bigdata-graduation-env及数据库环境加载后，从backend执行：

```bash
PYTHONPATH=. python tools/apply_course_migration.py
PYTHONPATH=. python tools/seed_course_chapters.py
```

迁移工具拒绝已有目标表，避免覆盖；若失败需先检查已创建表，DDL不支持整体事务回滚，不直接DROP重跑。种子工具复用三个同名已发布资源，通过管理员正式章节API添加；相同内容重跑跳过，冲突拒绝。

回退优先恢复部署代码并保留新增表和学习记录。DROP会永久删除章节数据，不能在正式库自动执行；如确需撤销，应先备份并单独确认，不删除旧资源/事件。

## 章节教学内容迁移006

迁移006_add_chapter_teaching_content.sql在005之后执行，只向course_chapters增加learning_objectives（JSON，可空）、example_code（LONGTEXT，可空）、exercises（JSON，可空）；目标与练习JSON须为数组。复用已有content保存完整Markdown正文，不改用户/资源表，也不改进度/事件表。

本机本阶段已执行006。新部署在既有虚拟环境激活后从backend执行：

```bash
PYTHONPATH=. python tools/apply_chapter_teaching_content.py --migrate --seed
```

工具校验全部三个同名已发布课程、每课既有5章节及标题/排序/知识点。只更新content、learning_objectives、example_code、exercises、video_url，保留章节ID和所有学习记录；教学更新在同一事务中提交，更新前备份章节原内容到outputs/course-teaching-content-backup-时间.json。种子为database/seeds/course-teaching-content.json，旧course-chapters.json保留为005历史基线；已增强的库不要再执行旧种子工具，否则会因内容差异拒绝。

重复执行006工具会验证已有字段类型/约束并跳过DDL，内容一致时更新0章；发现部分字段、课程缺失或章节身份不符则停止。MySQL ALTER有隐式提交，不把DDL描述为可整体回滚。回退优先保留新增字段并在备份下恢复教学内容；不得删除章节或重置chapter_progress/chapter_events。

只读核对：不带参数执行同一工具。它不会生成视频文件，也不做数据库迁移。迁移/初始化后需用原安全方式重启FastAPI，Key不写文件。

## MySQL与HDFS正式课程章节种子

新增database/seeds/formal-course-chapters.json，只覆盖现有MySQL数据库基础（1071）和Hadoop HDFS入门（1070），各5章。本阶段无需结构迁移；种子工具只读核对005/006的字段、CHECK、主外键、索引、utf8mb4及全部表结构摘要，不执行DDL。

在既有环境激活后，从backend运行：

```bash
# 首次发布或安全续跑，通过现有管理员章节创建API
PYTHONPATH=. python tools/seed_formal_course_chapters.py --publish
# 只读验证数据、结构及学习者接口
PYTHONPATH=. python tools/seed_formal_course_chapters.py
# 从正式5173代理只读验证完整教学字段
PYTHONPATH=. python tools/verify_chapter_teaching_live.py --seed formal-course-chapters.json
```

工具使用已有admin_demo/student_demo身份及进程内临时测试签名配置调用真实应用，不改密码、不保存Token、不改运行后端的配置。只操作1070/1071白名单，标题/状态不符或已有内容冲突即停止。正常重复执行跳过相同章节，不覆盖已有章节；已有学习记录时遵守原课程大纲冻结规则。

发布采用现有每章节事务，若中途失败保留已成功写入章节；不自动删除。无学习记录且已有部分章节完全匹配时可继续补齐。Spark真实浏览器联调演示资源406保持无章节，不改变它原有发布或推荐状态。

用户描述的chapter_title使用现有title字段，所有章节video_url为/demo/video.mp4；不生成视频。HDFS教学命令需独立Hadoop客户端和授权集群，只做语法校验，未在本机执行或安装HDFS。MySQL练习SQL同样不会由种子工具执行。

本次发布结果和迁移核验见outputs/formal-course-chapters-publication.json，阶段报告见outputs/formal-course-chapters-acceptance-report.md。

## 007：课程AI引用快照

本迁移仅新增ai_course_contexts，与ai_qa_records一对一关联，不改已有表、课程或章节。用于保存提问时真实检索引用及context摘要，让历史查询和UUID重放可追溯；不存Key或章节全文。需先完成001及004，现有课程依赖005/006。

```bash
source /mnt/d/BigDataGraduationProject/environments/activate-bigdata.sh
cd /mnt/d/BigDataGraduationProject/backend
PYTHONPATH=. python tools/apply_course_ai_migration.py
```

工具只创建该表并检查主外键、JSON约束、字符集及原数据摘要；重复执行核验已存在表，不自动ALTER或覆盖数据。MySQL DDL会隐式提交，不能声称事务回滚能撤销建表。应用回退时先停用课程助手代码并保留新表和问答数据；不自动删除附属表。如果需要物理回滚，应另行确认该表记录及历史影响。

迁移结果：outputs/course-ai-migration-evidence.json。启动更新后的后端前先完成迁移。课程请求使用旧ai_qa_records的resource模式，附属表只标记真实课程上下文，不改原模式CHECK。
