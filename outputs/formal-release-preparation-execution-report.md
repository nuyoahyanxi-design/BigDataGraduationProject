# 正式发布准备执行报告

> 历史资料说明（2026-10-13补注）：下文设计、数量、失败与未验收结论属于原记录日期，不代表当前版本；保留原始证据，不将当时未执行的测试改写为通过。 当前技术栈、视频播放证据和各数据口径统一见[答辩当前状态说明](../docs/defense-current-state.md)；本次仅修订文档，没有重新验收或运行Spark。

日期：2026-10-10。快照创建UTC2026-10-10 05:57:20起，北京时间13:57:20起。状态：准备通过，正式批次未执行。

## 发布准备状态

| 项目 | 状态 | 实际证据 |
|---|---|---|
| 代码冻结 | 通过 | main提交19b4739598a86a2307f62b135c7d27de2b78af1e；提交后工作区干净 |
| 备份 | 通过 | 121个payload文件逐一SHA256与长度校验，独立Windows复核0差异，备份源文件0差异 |
| 环境 | 通过 | MySQL80运行且只读连接成功；Java/JDBC/依赖复查；独立pgrep检查无Spark任务，8000/5173未监听 |
| 数据边界 | 通过 | 两次间隔10秒MySQL只读快照稳定，12表结构及受保护内容/元信息摘要相同，未来事件0，数据库时间覆盖最大事件时间 |

下一步建议：**A. 可以授权正式发布。** 本报告不是发布授权或发布成功记录。授权执行时应按已设计的30分钟维护预算保持写入静默，并在T0重新核对候选哈希、指针和数据；若出现新写入，重新采样并评估快照有效性，不盲用本报告。

## 候选提交

- 完整commit：19b4739598a86a2307f62b135c7d27de2b78af1e。
- 提交说明：fix: accept server course bridge UUIDv5 in Spark cleaning。
- 8个文件：cleaning.py一个生产修复，backend/tests/test_courses.py、spark/tests/test_pipeline.py、spark/tests/test_course_behavior_pipeline.py三个配套测试；四个课程/Spark/稳定化/发布准备设计文档。
- 已逐项审查差异，数据库、backend业务事件生成、推荐计算公式及前端无改动；暂存内容凭据模式检查无命中。
- 无依赖变更、Git推送、正式批处理或数据库写入。本轮不重跑含写入测试；使用上一阶段96项通过证据。

## 备份位置与内容

根目录：D:\BigDataGraduationProject\outputs\formal-release\20261010T055720Z-6b9d6c42。

pre-release目录保存：

1. 四latest发布指针的原字节副本。
2. data/下全部54份ODS/DWD/ADS manifest，包括旧prepared现场。
3. 当前发布链ODS/DWD/ADS Parquet及配套manifest、成功标记和质量报告。
4. 当前推荐results.json、MySQL当前画像/推荐精确批次的结果摘要与逻辑SHA256（画像4行、推荐36行）。
5. 候选源码Git archive ZIP、commit/分支/干净状态、Spark与backend源码SHA256、Spark配置及依赖清单。
6. 实际Python包、Java、Hadoop JAR、JDBC校验、磁盘空间等依赖信息。
7. 12表DDL、逐表DDL/结构SHA256（结构摘要排除AUTO_INCREMENT当前值）。
8. 12表受保护记录摘要：账号凭据/用户名不读取进摘要，AI两表只取安全元信息，不导出问题/回答；其他业务/结果表对允许数据计算内容摘要。
9. 177个正式manifest/Parquet/latest哈希清单、复制源哈希清单、两次数据库采样和最终边界检查。

这是发布回滚包，不是包含凭据和所有私人数据的全库灾备备份。原历史批次未修改或删除。

## 完整性

- backup-inventory.json登记121个备份payload文件的路径、长度、SHA256。
- backup-inventory.sha256核验清单自身；清单SHA256：4ef4b54c26705d2ebbf452016f0b068e211012355edc834fd9d26dfb16980af7。
- backup-verification.json记录验证通过、0差异；随后使用Windows Get-FileHash逐项再次检查，121项全部通过，清单自身校验通过。
- 所有复制源文件仍与备份哈希一致；177个正式文件与备份前清单一致；工作区仍干净。

## 发布前最终检查

正式输入确定为bigdata_graduation五表分析投影：users6、resources13、learning_progress11、favorites3、learning_events90。不把隔离验证/合成实验文件混入正式输入，不直接抽取chapter_events或AI记录。

正式旧源批次20261005T102319Z_fdb1d523；ODS截止UTC2026-10-05 10:23:19.173。当前事件最大occurred_at为UTC2026-10-09 13:00:00.879，最大received_at为13:00:00.870；63条在旧ODS截止之后，需新正式源批次。现有UUIDv5四条，未来事件0，MySQL时间覆盖事件边界。

两次相隔10秒的只读一致性快照中，数据摘要、表结构和最大事件边界均一致。uuidfix/ch/lt/sp相关临时账号0、uuidfix课程0、20990101/rollback_test结果行0。六条固定开发验收资源保留，不属于本轮夹具残留。

独立Spark进程检查使用spark[.]jobs[.]与SparkSubmit匹配，没有返回PID；Windows目前仅项目MySQL端口3306监听，8000/5173未监听。没有启动、停止、重配服务。

数据稳定是本轮观察结果，不是持续写入锁。正式发布仍需保持业务/管理/测试/直接SQL写入静默直到成功或回滚验收。若后续启动服务或操作业务，需再次核对静默和快照边界。

## 执行边界

已执行：本轮指定候选提交、备份复制/归档、SHA256完整性验证、只读MySQL采样和环境检查、报告生成。

未执行：正式Spark任务、任何MySQL写入、latest切换、历史数据删除、回滚操作、付费AI或依赖安装。所有SQL检查均为只读一致性事务，结束rollback并关闭连接；回滚这里仅结束只读事务，不是恢复生产数据。
