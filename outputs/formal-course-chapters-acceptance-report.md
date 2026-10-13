# 正式课程章节补充阶段验收报告

> 历史资料说明（2026-10-13补注）：下文设计、数量、失败与未验收结论属于原记录日期，不代表当前版本；保留原始证据，不将当时未执行的测试改写为通过。 当前技术栈、视频播放证据和各数据口径统一见[答辩当前状态说明](../docs/defense-current-state.md)；本次仅修订文档，没有重新验收或运行Spark。

验收日期：2026-10-05。项目：基于Spark学习行为分析和AI辅助的个性化学习平台。

## 1. 本阶段目标与实际完成内容

仅补充正式教学资源的章节数据，不修改现有课程页面、业务接口、数据库结构、学习进度与事件处理逻辑、推荐算法、Spark任务或AI助手。

| 课程 | resource_id | 新增章节数 | 章节ID |
| --- | --- | --- | --- |
| MySQL数据库基础 | 1071 | 5 | 54、55、56、57、58 |
| Hadoop HDFS入门 | 1070 | 5 | 59、60、61、62、63 |

MySQL章节依次为：MySQL与关系型数据库基础、数据表/字段/约束设计、SELECT查询/条件筛选/排序、聚合查询与表连接、事务/回滚/索引基础。

HDFS章节依次为：HDFS架构与核心概念、目录与文件操作、数据块与副本机制、读写流程与权限、HDFS与Spark数据分析衔接。

每章均包含标题、教学目标、知识点标签、Markdown详细讲解、案例理解、示例代码、章节练习与视频地址。需求中的chapter_title映射为已有title字段，没有新增字段。视频地址统一为/demo/video.mp4，没有生成视频文件。

已有三个正式课程各5章保留，五门正式课程合计25章。系统演示资源406（Spark真实浏览器联调演示资源）仍为0章。

## 2. 发布方式与数据保护

先生成受控JSON种子文件，验证课程ID、标题、状态、章节顺序、必填内容及当时使用的媒体示例地址；随后通过现有管理员章节创建API发布到真实MySQL。发布工具使用FastAPI TestClient及现有管理员身份的内存令牌，不绕过章节业务服务，不读取或修改账号密码，不输出凭据。

每章使用现有接口事务提交，并非十章整体事务。工具遇到冲突会停止，不覆盖已有内容；重复执行只接受完全一致的章节，缺失章节的续建仍遵守已有学习进度限制。本次首次发布新增10章，再次发布新增0章，ID与内容保持一致。

初次发布前后的已有章节快照一致。users（不含密码哈希）、resources、learning_progress、favorites、learning_events、chapter_progress、chapter_events、user_profiles、recommendation_results的受保护数据快照一致；测试结束后的只读核验也与初次发布后的快照一致。未删除资源或行为记录。

## 3. 数据库迁移验证

现有005/006迁移已支持全部教学字段，本轮没有新增结构迁移，也没有执行DDL。通过只读检查验证：章节字段与已有模型对应；JSON字段、检查约束、主键、资源外键、章节顺序唯一索引与utf8mb4字符集符合预期。

发布前后及测试后的全库SHOW CREATE TABLE结构摘要一致。比较时仅排除AUTO_INCREMENT当前计数值，因为插入数据会改变计数，该值不属于字段或约束结构。

证据：formal-course-chapters-initial-publication.json、formal-course-chapters-publication.json、formal-course-chapters-verification.json。

## 4. 测试与正式接口验证

| 验证项 | 实际结果 |
| --- | --- |
| 后端pytest全量 | 280 passed；1条既有Starlette弃用警告 |
| 本阶段新增后端测试 | 17项：10章完整性、正式课程范围、非法种子拒绝、代码语法及现有迁移结构核验 |
| 前端npm test | 16个测试文件，88 passed，无跳过 |
| 正式5173代理学习者只读查询 | 两门新增课程均返回5章及完整教学字段，2/2通过 |
| 已有三门课程正式接口回归 | 3/3通过 |
| 重复发布 | 新增0条，章节ID不变 |
| 演示资源排除 | 406仍为0章 |
| 结构及受保护数据快照 | 一致，通过 |

后端执行：python -m pytest tests -q --junitxml=../outputs/formal-course-backend-tests.xml。
前端执行：npm test，并启用指向本机8000/api的实际接口集成测试配置。

测试日志保存在formal-course-backend-tests.log、formal-course-backend-tests.xml、formal-course-frontend-tests.log。正式API结果保存于formal-course-live-api-verification.json。未将API查询验证描述为浏览器完整学习流程验证。

## 5. 修改文件清单

新增：

- scripts/prepare-formal-course-seed.py：生成教学种子数据，不执行教学示例。
- database/seeds/formal-course-chapters.json：两门课程10章完整内容。
- backend/tools/seed_formal_course_chapters.py：受控发布、只读验证及数据保护检查工具。
- backend/tests/test_formal_course_seed.py：17项新增测试。
- docs/formal-course-chapters-design.md：范围、方案与验证依据。
- outputs/formal-course-chapters-acceptance-report.md：本报告。

修改：

- backend/tools/verify_chapter_teaching_live.py：只读验证工具增加种子文件选择参数，保留原默认行为；不修改业务API。
- database/README.md：发布方法、迁移核验与安全限制说明。
- README.md：正式课程覆盖情况与该阶段尚无真实媒体的说明。

另生成本报告前述JSON证据与测试日志。未修改backend/app业务文件、frontend页面或组件、数据库结构及Spark代码。

## 6. 如何启动与查看

使用已有start-project.bat启动方案，按现有安全方式提供Agnes配置（如需要）；登录学习者账号后，访问/resources/1071/learn或/resources/1070/learn查看课程目录和教学内容。当前运行中的正式接口已经验证能够返回新章节。

如需重复核验，在WSL中激活既有bigdata-graduation-env，然后进入backend目录：

```bash
PYTHONPATH=. python tools/seed_formal_course_chapters.py
PYTHONPATH=. python tools/verify_chapter_teaching_live.py --seed formal-course-chapters.json
```

只有需要受控补齐时才使用发布工具的--publish参数；本次数据已发布，无需再次执行。

## 7. 当前限制与阶段结论

该阶段/demo/video.mp4仅为媒体示例地址，未验证真实视频播放；当前正式媒体通过学生目录发现规则提供。HDFS命令做了bash语法检查，PySpark示例做了Python语法检查；未安装或运行HDFS集群。MySQL教学SQL未在平台数据库执行，练习应使用独立实验环境。此次未进行浏览器逐章完成操作，以避免额外学习行为写入。

本阶段范围内验收通过：新增正式教学章节已写入且实际接口可读取，测试通过，既有结构、数据与业务链路保留。后续真实视频素材或HDFS实验环境需单独授权，本阶段完成后停止。
