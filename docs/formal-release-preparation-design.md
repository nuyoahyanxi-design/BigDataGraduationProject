# 正式批次发布准备与执行方案

日期：2026-10-10。状态：准备检查与方案完成；未执行发布。适用于学习行为UUID兼容修复后的首个新正式批次。

## 1. 授权边界与发布对象

本轮只读检查环境、代码、MySQL、现有产物与风险，生成方案。不修改业务源码/数据库，不运行Spark正式任务、不删除数据、不提交Git、不更新latest、不创建真正的发布备份或回滚演练。文档与只读检查JSON是本轮唯一新增交付物。

发布候选为HEAD 955ef8b（main）加已验收工作区修改，唯一生产变更spark/utils/cleaning.py。其当前SHA256为d61148a4a37285f2358b3ae485061a8dd8b5b239195db12c0fedd4e4322c6be2；完整Spark源码/配置摘要见outputs/formal-release-readiness-evidence.json。Git HEAD不包含此修复，不能只记录提交号作为发布版本。正式执行前必须冻结“HEAD+已审查差异+源码/配置哈希”；可另行授权提交，也可建立不可变候选副本，不要求本轮擅自提交。执行时逐项复核哈希，修改即中止。

## 2. 已确认环境与现有链路

- WSL Ubuntu-22.04-Recovered，Java17.0.20.1，PySpark3.5.7，PyMySQL1.1.1，FastAPI0.115.12，SQLAlchemy2.0.40。
- Spark local[2]、driver1g、shuffle2；每源表最多50000行，候选最多2000000对，输出最多50000条，TopN=5，时区UTC/Asia-Shanghai按既有规则。
- Hadoop client API/runtime3.3.4等JAR存在；本链路使用本地文件，不要求部署独立HDFS/YARN。当前检查未启动Spark；实际运行依据本阶段已验收测试，不能称本轮重新执行成功。
- Connector/J8.0.33存在，Driver.class存在，SHA256与项目基线一致；项目盘可用空间约310384898048字节（检查时值）。
- MySQL80运行，127.0.0.1:3306/bigdata_graduation只读一致性事务连接成功，8.0.45，外键检查开启。授权声明包含INSERT；没有执行试写，不能将其当作发布事务成功证据。
- 当前未发现Spark正式任务进程；Windows和WSL未发现8000/5173监听，未启动或停止任何对外服务。
- 四指针completed、同源20261005T102319Z_fdb1d523；ODS/DWD/ADS文件哈希、ADS指针与manifest内容、后端推荐/看板指针解析均通过。旧批次MySQL画像4行、推荐36行与manifest相符。

## 3. 正式输入范围与时间边界

正式输入仅为bigdata_graduation的五表分析白名单投影：users、resources、learning_progress、favorites、learning_events。沿用一个JDBC一致性只读快照，不导入outputs下隔离验证工作区，不导入模拟实验批次，不增加chapter_events/AI表。章节开始/全部完成通过原learning_events桥接进入。

当前数据库：users6（4 active learner、2 active admin）、resources13、learning_progress11、favorites3、learning_events90；course_chapters26、chapter_progress17、chapter_events65为受保护业务表，不直接作为Spark输入。六条既有开发验收资源保留在源库，推荐按现有候选规则排除；不将其误判为本轮测试残留并删除。所有分析结果仍须注明开发/验收数据性质。

当前正式ODS截止UTC 2026-10-05 10:23:19.173（北京时间18:23:19.173），事件接收水位UTC09:52:31.387；五表快照6/12/6/2/27，DWD26。当前最新事件occurred_at为UTC2026-10-09 13:00:00.879，received_at为13:00:00.870；63条事件晚于旧ODS截止。应创建全新源批次，不能复用旧ODS证明兼容修复生效。

检查时没有未来事件、学习事件孤立引用为0；已验收历史4条UUIDv5全部匹配章节派生关系。若数据在正式执行前保持不变，预期新清洗90输入、89有效、1条no_state_change；这是已有隔离证据下的条件性预期，实际以新冻结快照报告为准，不把它作为盲目的固定数量断言。

两次相隔2秒的只读事件数量/最大ID/最大时间稳定，且受保护表摘要与上轮验收一致；这只说明短时观察无变化，不证明未来不会有写入。检查观测API进程时钟比MySQL读数约快888ms（单点近似，不是精确时钟校准）。不能放宽future_authoritative_time规则。

## 4. 静默窗口与发布前门禁

推荐预留30分钟维护窗口，属于操作预算，不是实测发布耗时或保证。实际T0由用户确定，本轮不预约、不建自动化。

- T0前60秒起禁止新学习、收藏、章节操作、注册/兴趣修改、管理员课程/资源编辑以及所有测试/种子/其他批处理。
- 最稳妥方式是在当前未运行后端的状态下保持后端停止，并协调直接MySQL写入工具；不重配数据库、不改权限、不引入维护模式代码。只关闭页面不足以保证无后台请求。
- 发布前等待既有事务结束，连续两次间隔10秒只读核对五表内容摘要及事件数量/最大时间稳定，且MySQL UTC时间不早于已接收事件最大occurred_at/received_at；任一不满足则继续等待或中止。
- 从抽取至四阶段校验或回滚完成始终禁止写入和并行发布；超过30分钟延长维护，不能按时间自动恢复。
- 最终API只读验证可恢复原服务，但在检查结束前仍禁止业务写操作；角色页面检查不点击学习按钮，因为可能产生事件。

必须先满足：候选哈希冻结并一致；只读DB/依赖再次通过；无本轮临时数据及并行任务；发布前快照完整并可校验；旧四指针同源完整；静默/时钟条件满足；用户明确授权正式发布。发布负责人已由用户指定为本对话Codex，未来执行和回滚同由该负责人记录；具体执行窗口尚待确定。缺门禁项不得开始。

## 5. 发布前快照清单（计划，尚未创建）

建议发布授权后创建outputs/formal-release/<release_id>/pre-release/，release_id由实际时间及唯一标识生成，不预填将来的batch_id。

1. 代码：HEAD、git status、经过审查的差异、新增测试/设计、Spark jobs/utils/configs哈希，依赖版本及JDBC摘要。不得包含.env.local、密码、Key、JWT、Cookie、安全凭据。
2. 原字节备份四文件：outputs/spark-data-pipeline-latest.json、user-profile-latest.json、recommendation-latest.json、dashboard-latest.json，记录SHA256，不能经JSON重序列化代替原文件备份。
3. 当前源ODS/DWD的manifest及Parquet；当前画像/推荐/daily_metrics ADS的manifest及Parquet；配套quality-report.json/md、outputs/recommendations/<旧推荐批次>/results.json。保留目录结构和哈希。只复制当前发布链；其他历史批次保留原地并保存完整文件哈希清单。
4. 数据库保护证据：12表结构（排除自增当前值单独记录）、五表分析投影、课程章节/章节进度/章节事件数量及内容摘要、旧画像/推荐精确batch_id的行数/内容摘要。仅保存允许字段及哈希，不复制用户密码哈希或问答正文；这不是全库灾备备份。
5. 元数据：两次静默采样、数据库UTC与事件最大时间、校验通过记录、备份实际路径、执行人/回滚人、四旧批次编号。

保护全部12表：五表输入、course_chapters/chapter_progress/chapter_events、user_profiles/recommendation_results、ai_qa_records/ai_course_contexts。正常发布仅允许user_profiles与recommendation_results追加本次新批次；其他10表不写，已有结果行不改。AI两表只核对结构/数量等最小摘要，不导出私人内容。

## 6. 失败回滚方案

已有任务不是跨文件/跨任务分布式事务：pipeline成功先切换管道latest；画像/推荐分别MySQL提交后切换各自latest；看板最后切换。单个文件采用write_json的临时文件+replace，但四指针没有组原子性。

发生失败：保持维护窗口，停止后续阶段；确认没有发布进程仍在运行，记录退出码、失败阶段及新batch_id。不要自动连续重试、覆盖新目录或恢复业务写入。

恢复对象：本次实际改变的四latest成套恢复为发布前旧链。使用备份原字节在各目标同一目录写临时文件，再逐文件os.replace；这仅是人工执行方案，不在本轮运行或创建脚本。替换前复核备份哈希和当前指针确属本次发布，发现另一发布者修改则停止。维护窗口期间完成成套恢复，不能把逐文件原子性称为全链原子性。

旧ODS/DWD/ADS/manifest和旧MySQL结果若保护摘要一致无需恢复；新生成的Parquet、prepared/failed目录、日志及已经提交的新批次MySQL画像/推荐行保留，恢复旧指针即恢复旧服务结果，不DELETE、不DROP、不截断。若DB提交成功但指针失败，不自动再次插入，也不把残留称为成功发布；留作后续按精确batch_id核对。

若发现既有数据或历史文件被改，普通指针回滚不够：保持服务不可写，保留现场，按受影响精确对象评估专门恢复并另行授权，不能用分析投影冒充全库备份或覆盖生产库。

回滚验收：四latest原字节哈希等于备份；四旧batch/source/profile关联一致；旧manifest/Parquet全哈希通过；MySQL旧批次行数/摘要一致，受保护业务表不变；后端解析及推荐/看板只读查询返回旧批次，空/错误状态不增加；无未结束Spark进程。所有条件满足后才恢复写入。新结果行可增加，不能用整张结果表总数必须回到旧值作为回滚条件。

旧prepared现场两个批次20261005T092916Z_9856eb5f_r1_b097ad694270fe8f5e13、20261005T101822Z_56fede2b_p1_338342c9c5d6均未被当前latest引用，原样保留，不作为新输入/回滚目标，不需要为本次发布删除。

## 7. 正式发布步骤（仅方案）

### 阶段1：准备
- 操作：获得正式发布授权；冻结候选；建立并核验上述快照；实施静默窗口；复查依赖、连接、无残留、无并行任务、时钟/数据稳定。使用既有激活脚本和安全凭据机制，不安装依赖或输出环境变量。
- 验证：源码/配置哈希与候选一致，备份四指针同源且可解析，快照哈希完整，数据静默成立，MySQL UTC>=事件最大时间，无阻断。

### 阶段2：执行Spark正式批处理
- 操作：未来授权后执行python -m spark.jobs.pipeline，生成新ODS/DWD并完成质量报告；成功后记录实际source_batch_id。该命令会切换管道latest，不是dry-run。失败停止并评估回滚。
- 验证：退出0，五表一致性快照completed，Parquet读回/哈希通过，数量守恒，无异常future/UUID排除；逐条核对既有4条v5桥接及当前新增桥接按语义进入DWD；no_state_change仍正常排除；不覆盖旧批次。

### 阶段3：ADS发布
- 操作：依次执行python -m spark.jobs.user_profiles --source-batch <实际新源批次>；成功后记录真实profile_batch_id；执行python -m spark.jobs.recommendations --profile-batch <实际新画像批次>；成功核对推荐latest指向本次新批次，再执行python -m spark.jobs.dashboard_metrics。每步完成校验才运行下一步，任何错误立即停止。占位编号不是可直接执行值。
- 验证：画像/推荐任务内已完成Parquet校验、MySQL事务、读回与latest切换，不能在完成后再假装另有独立commit步骤。检查源截止一致、active learner覆盖、开始/完成计数与DWD可核算、评分公式未变、完成/下架过滤、理由真实、排名唯一；两表仅追加新批次且旧结果摘要不变。看板绑定同源推荐/画像，30日指标与质量报告一致。

### 阶段4：发布完成检查
- 操作：比对发布前后记录、正式历史文件及旧结果；恢复原后端/前端仅做只读结果核验（此时仍不允许业务写入）；保存本次批次、耗时、日志、产物、MySQL证据与回滚材料；全部通过后解除静默。
- 验证：四latest completed且同源；推荐配套profile正确；ODS/DWD/ADS哈希、MySQL行数/摘要对应；业务10表不变；既有历史文件除四latest外不变；正式查询可读、时间/来源清楚，旧失败目录没有被冒充成功。失败保持窗口并按第6节回滚。

## 8. 发布决策

选择B：需要先处理风险后发布。环境/连接/现有发布链通过，未发现本轮临时数据或并行Spark任务；96项测试为上一阶段真实证据，本轮未重跑测试或试写。

尚未落实候选冻结、实际发布前备份和静默窗口；最新正式ODS比当前数据落后63事件；API/MySQL时间有近似0.9秒差；四指针分阶段切换而非组原子。本轮无正式发布授权。上述操作门禁落实后可再给执行前Go/No-Go，不需要为此重构架构或数据库。
