# MySQL与HDFS正式课程章节补充设计

> 历史资料说明（2026-10-13补注）：下文设计、数量、失败与未验收结论属于原记录日期，不代表当前版本；保留原始证据，不将当时未执行的测试改写为通过。 当前技术栈、视频播放证据和各数据口径统一见[答辩当前状态说明](defense-current-state.md)；本次仅修订文档，没有重新验收或运行Spark。

## 目标与范围
仅向既有正式课程补充教学数据，MySQL数据库基础资源ID1071、Hadoop HDFS入门资源ID1070各5章。实际查询二者已发布、均为0章；已有Spark、PySpark、机器学习三课各5章。

用户所称chapter_title映射现有title字段，不新增字段。每章使用现有content（Markdown）、learning_objectives、knowledge_tags、example_code、exercises及视频字段；统一/demo/video.mp4，不生成视频、不修改播放器。

## 发布方案
新增独立种子JSON和初始化工具，严格白名单1070/1071及标题、已发布状态。通过现有管理员章节创建API（TestClient载入真实应用、真实MySQL）发布，不改路由或服务代码。使用只在工具进程内的测试签名密钥，授权身份来自已有active admin_demo；不使用/修改账号密码，不输出Token。

发布前校验全部10条ChapterWrite及课程现有章节。0章且无章节学习记录时允许创建；已有5章完全相同则跳过；部分种子完全相同且没有学习记录时可继续补齐，不匹配时拒绝覆盖。保留已有学习记录和其他课程。按原API每章事务，途中失败保留已创建章节并明确报告，不删除；重复运行可在无学习记录条件下继续。

Spark真实浏览器联调演示资源（实际ID406，标题含空格和日期）明确排除：种子不含它，工具仅操作白名单2课；核对演示资源仍为0章。不改资源发布/推荐状态，不改推荐算法或Spark。

## 迁移验证
本阶段不新增迁移、不执行DDL，核对已有005/006章节字段、JSON约束、主键、外键、索引和字符集。比较所有表SHOW CREATE TABLE摘要、既有章节及受保护业务表数据摘要前后，新增只允许10条course_chapters。用户数据摘要排除密码。

## 教学安排
MySQL五章：关系型数据库、表与字段、查询筛选、聚合连接、事务索引。示例为MySQL8 SQL，只用于独立练习会话/数据库，不自动执行教学SQL。
HDFS五章：架构、文件操作、数据块副本、读写权限、Spark接入。示例需要单独配置Hadoop/HDFS；本机不安装或启动HDFS，示例参数和路径明示为教学用法，避免宣称本机已有HDFS。

## 验收
执行后端pytest、前端npm test；新增种子范围/完整性/安全排除测试。只读核对10章完整字段和现有课程查询可见，复跑初始化确认0新增。全量API联调使用临时测试数据并精确清理，既有数据保持。

参考：
- https://dev.mysql.com/doc/refman/8.0/en/with.html
- https://dev.mysql.com/doc/refman/8.0/en/commit.html
- https://hadoop.apache.org/docs/r3.3.6/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html
- https://hadoop.apache.org/docs/r3.3.6/hadoop-project-dist/hadoop-common/FileSystemShell.html
