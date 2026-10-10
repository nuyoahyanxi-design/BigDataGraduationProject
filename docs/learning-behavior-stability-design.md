# 学习行为数据链路稳定化设计

日期：2026-10-10。状态：用户已确认最小兼容方案；生产清洗规则与测试已实施，运行验收结果见对应阶段报告。

## 1. 目标与授权边界

本阶段只修复章节学习产生的课程级事件进入既有 Spark 分层、画像及推荐的兼容问题。不改变整体架构、不重构数据库、不新增业务表、接口、事件类型或推荐公式。用户已授权源码、单元与隔离数据验证，禁止正式发布及修改既有生产记录。

既有链路：章节 API → courses.act/bridge → learning_events 与进度同事务 → MySQL 五表一致性快照 → ODS → clean_events → DWD → 用户画像/推荐 ADS → 既有发布机制。

## 2. 问题定位与证据

1. backend/app/services/courses.py:52 使用 uuid5(NAMESPACE_URL, 'course:{source_uuid}:{kind}') 生成 learning_start/learning_complete。章节客户端请求仍由 ChapterAction.event_uuid: UUID4 校验；桥接 UUIDv5 是服务器内部派生身份。
2. database/migrations/001_create_core_tables.sql 的 event_uuid 为 CHAR(36)，唯一索引及事件语义约束没有限制 UUID 版本，因此合法桥接事件能保存到 MySQL。
3. spark/utils/schemas.py 和 mysql_snapshot.py 抽取 learning_events 全部分析字段；extract.py 不过滤 UUID，ODS 保存原值。chapter_events 不直接进入五表分析投影，这是既有设计，不扩展抽取范围。
4. spark/utils/cleaning.py:4 的 UUID_PATTERN 只接受版本位为 4 的 UUID；第31行将 UUIDv5 事件归类 invalid_event_uuid，写入 rejected 而不进入有效 DWD。
5. 本轮对当前源码正则作格式复核：合成 UUIDv4 形状通过，UUIDv5 形状拒绝。这只是正则静态复核，不是 Spark 运行验收。
6. 历史 outputs/final-acceptance-20261009/spark-readonly.json 记录90输入、85输出、4条 invalid_event_uuid、1条 no_state_change。尚未逐条核对这4条异常与章节源UUID的派生关系，不将其全部归因于桥接事件。
7. 正式最新源批次20261005T102319Z_fdb1d523仅27输入、26输出、1条 no_state_change；它早于最新章节数据，不能用该旧快照证明当前桥接链路正确。

现有后端 test_full_chapter_flow_and_legacy_bridge 只核对两条桥接事件保存与状态；Spark 清洗测试使用独立构造的 UUIDv4。缺少真实章节 API 事件接入清洗/画像/推荐的跨模块测试。

## 3. 下游影响

| 层/功能 | 当前影响 |
|---|---|
| MySQL/ODS | 桥接事件仍保存，未在入口丢失 |
| DWD | UUIDv5桥接开始/完成被拒绝；rejected保留其异常记录 |
| ADS画像 | 开始/完成次数、开始/完成资源数、完成率、类型偏好、兴趣权重及活跃证据可能不完整 |
| ADS推荐 | 热门开始/完成贡献、个人行为归一化、是否有历史行为判断可能变化；无显式兴趣用户的兴趣匹配也可能变化 |
| 完成过滤 | 可从ODS learning_progress.completed排除资源，故过滤成功不能证明DWD完整 |

画像同时使用行为和显式兴趣；推荐优先使用显式兴趣，未设置时使用画像权重。修复不保证每个用户排序都变化，需通过受控数据核验计算影响。无状态变化事件仍排除，不算数据丢失。video_play/章节细粒度事件仍只留在章节表，不加入本阶段分析。

## 4. 推荐修改方案

保留后端UUIDv5生成、命名空间、派生串、指纹、锁顺序及事务语义；不改历史事件身份。最小修改位于Spark清洗边界。

清洗UUID规则：

- event_uuid为标准UUIDv4时，按原规则继续校验。
- 标准UUIDv5仅允许 event_source=server 且 event_type为learning_start或learning_complete。
- UUID variant仍限制8/9/a/b；其他版本、空值、错误格式继续拒绝。
- session_id继续严格UUIDv4，客户端/API输入继续严格UUIDv4。
- 来源、状态转换、指纹、用户/资源关联、时间、版本、有效性、去重及冲突检查全部保留。UUIDv5只通过格式门槛，不绕过其他检查。

这个兼容规则不单凭UUID字符串证明其一定来自章节桥接；实际来源在只读诊断/验收中利用既有chapter_events和派生公式核对，不新增生产联表或字段。

不建议把后端改为随机UUIDv4：它不能修复历史UUIDv5兼容性，还会改变确定性派生身份。也不把UUIDv5改写成带版本4外观的伪UUIDv4。

历史MySQL事件、已完成ODS/DWD/ADS与latest均不直接改写。确认实施后先在隔离输出中用旧ODS和当前只读快照验证恢复影响；正式数据修复需要既有pipeline生成新源批次并依次重算。正式发布不包含在当前设计确认中，验收证明就绪后再确定执行窗口。

## 5. 影响文件列表

| 文件 | 计划动作 |
|---|---|
| spark/utils/cleaning.py | 拆分事件UUID兼容判断与严格session UUIDv4判断；保留其他校验 |
| spark/tests/test_pipeline.py | 增补v4/v5正反例、来源/事件限制、UUID冲突、重复、状态/时间/指纹等回归 |
| backend/tests/test_courses.py | 补桥接UUID确定性、类型区分、同请求重放及并发只生成一次的断言 |
| spark/tests/test_course_behavior_pipeline.py（新增） | 真实章节API→一致性快照→隔离ODS/DWD→画像/推荐ADS跨模块验收；保留正式批次 |
| docs/course-learning-design.md | 追加服务端桥接UUIDv5契约与本阶段设计入口 |
| docs/spark-data-pipeline-design.md | 追加清洗兼容契约，不抹去历史阶段描述 |
| docs/learning-behavior-stability-design.md | 本设计；确认后补实际实施决策 |
| outputs/learning-behavior-stability-acceptance-report.md | 分别记录定位、实施、测试和未验证内容 |
| outputs/learning-behavior-stability/ | 实施后保存JUnit、日志、影响对比和数据/文件保护摘要 |

仅1个生产源码文件计划改动。backend/app/services/courses.py、画像/推荐计算与发布源码只检查不修改；数据库DDL、前端、AI、environments、wsl、spark-experiments不修改。测试若需额外隔离支持，先在新增测试内实现，不扩大生产改动。

## 6. 实施后的测试与证据计划

1. 真实当前数据只读审计：仅查询UUID、类型、来源、必要关联及数量，核对每条v5事件是否可由chapter_events按现有公式派生；不读账号凭据/问答正文，不回填历史数据。
2. 清洗边界：v4五类事件保留；合法server v5开始/完成保留；v5浏览/收藏、client v5、v5 session、其他版本及坏variant拒绝；格式合法但坏状态/时间/指纹/关联仍拒绝；重复保留一次、冲突整组拒绝；无变化回执仍排除；数量守恒及Parquet读回通过。
3. 后端回归：首次访问只生成一次开始、全部章节完成只生成一次完成，UUID为稳定v5且类型不同；重放、并发、失败回滚、权限保持。
4. 跨模块实际计算：隔离临时账号/课程，通过真实FastAPI接口产生章节学习事件；冻结开始、部分完成和全部完成快照，核对事件进入ODS/DWD。真实Spark计算画像和推荐，保存/读回隔离ADS，核对开始与完成次数、兴趣贡献、热门原始权重及完成过滤。对仍未完成候选检验行为分数，对已完成资源检验其面向其他用户的热度；不以被过滤后的结果声称个人分数提升。
5. 按最新授权，本轮不调用画像或推荐MySQL发布函数（包括隔离发布测试）；只在隔离目录生成ADS与读回核对。临时账号/课程通过正式业务API产生数据，结束只清理自己创建的精确ID，不删除既有数据。记录持久数据及正式manifest/Parquet/latest前后摘要。数据库自增计数可能自然推进，结构对比排除AUTO_INCREMENT当前值，但字段/键/约束仍严格比较。
6. 执行与风险相称的后端章节/行为和Spark清洗/画像/推荐计算回归，不运行会调用发布函数的用例；前端未改无需构建。记录真实通过/失败/未选择数量，不引用历史计数冒充本轮。

验收最低门槛：章节桥接两类事件完整进入有效DWD；画像/热度可手算核对；合法幂等和无效过滤不退化；正式数据/产物受保护；提供实际日志、JUnit和机器可读对比。测试中的临时数据与隔离ADS不等于正式线上批次已更新，浏览器验收另行注明。

## 7. 本轮结论

根因已静态确认。生产改动仅spark/utils/cleaning.py；backend桥接UUIDv5逻辑、数据库DDL及画像/推荐公式不变。测试使用真实API（TestClient）、MySQL、JDBC抽取和Spark计算，隔离目录保存ODS/DWD/ADS，不调用正式pipeline编排或发布函数、不改正式latest。实际测试结果和验证证据见outputs/learning-behavior-stability-acceptance-report.md。

实施验收补充：后端60项、Spark选定回归35项、跨模块1项最终通过，共96个不同用例；首轮UUID兼容用例在35项中再次覆盖，不重复计数。历史只读核对4条v5均匹配既有章节派生关系。177个正式文件及受保护持久数据一致，12表结构一致。隔离ADS为计算结果投影，不代表正式发布成功。第一次测试因时钟/截止边界失败的日志保留，仅调整测试等待数据库时钟的前置条件，生产时间规则不变。正式发布需新授权。
