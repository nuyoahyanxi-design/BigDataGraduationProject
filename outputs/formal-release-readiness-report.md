# 正式批次发布准备检查报告

> 历史资料说明（2026-10-13补注）：下文设计、数量、失败与未验收结论属于原记录日期，不代表当前版本；保留原始证据，不将当时未执行的测试改写为通过。 当前技术栈、视频播放证据和各数据口径统一见[答辩当前状态说明](../docs/defense-current-state.md)；本次仅修订文档，没有重新验收或运行Spark。

日期：2026-10-10。检查时间：北京时间11:26:58起（JSON记录UTC03:26:58）；环境只读检查，无正式发布。

## 发布建议

**B：需要先处理风险后发布。** 技术基础通过；候选冻结、真实备份、静默窗口及分阶段指针回滚尚未落实。完整执行方案见docs/formal-release-preparation-design.md。

## 环境实查结果

| 检查 | 实际结果 |
|---|---|
| Git | main，HEAD955ef8b；5个已跟踪文件修改、2个新增设计/测试文件待跟踪（本准备文档另新增）；修复未提交 |
| 生产改动 | 仅cleaning.py；SHA256 d61148a4a37285f2358b3ae485061a8dd8b5b239195db12c0fedd4e4322c6be2 |
| Spark配置 | local[2]、driver1g、shuffle2、每源表50000行；TopN5、候选上限2000000、输出50000 |
| 依赖 | Java17.0.20.1、PySpark3.5.7、PyMySQL1.1.1、Hadoop client3.3.4 JAR存在 |
| JDBC | Connector/J8.0.33完整摘要匹配，Driver.class存在 |
| 磁盘 | 项目盘剩余310384898048字节（检查时） |
| MySQL | MySQL80 Running；8.0.45；127.0.0.1:3306；bigdata_graduation只读一致性连接通过；foreign_key_checks=1 |
| 运行进程/端口 | 无匹配的正式Spark任务；Windows/WSL均未发现8000、5173监听，未启动服务 |
| 临时测试残留 | uuidfix/ch/lt/sp已知前缀账号0；uuidfix课程0；20990101/rollback_test结果批次0；受保护9表与上轮摘要一致 |
| 保留样本 | 6个既有用户、13资源中含6条固定开发验收资源；不是本轮未清理临时夹具，不删除 |
| 源数据关联 | learning_events孤立用户/资源引用0 |
| 四latest | completed且同源20261005T102319Z_fdb1d523，ADS指针与manifest一致，文件哈希通过 |
| 服务读取契约 | 调用只读推荐/看板指针解析通过；不是真实HTTP/浏览器验证 |
| 旧发布结果 | MySQL当前画像批次4行、推荐批次36行，与元数据一致 |
| 历史保护 | 177个正式manifest/Parquet/latest与隔离验收后完全一致；changed=[] |

授权声明中存在INSERT，未试写也未调用发布函数；权限声明不等于本轮写入验收。当前历史manifest共52个completed、2个prepared，后者未被任何当前latest引用，保留现场。

## 数据边界

输入五表分析投影，当前行数users6/resources13/learning_progress11/favorites3/learning_events90。正式ODS截止UTC2026-10-05 10:23:19.173，旧事件27、DWD26。当前最后事件UTC2026-10-09 13:00:00.879；63条事件在旧ODS截止之后，必须新抽取，不复用旧快照。

当前无未来事件；4 active learner×12 published资源的候选上界48，远低于配置上限（实际候选还会过滤）。两秒采样无新增事件，五表/结果表摘要与此前一致，但未实施写入控制，不能保证未来无漂移。API时钟减MySQL读数约888ms，单点近似；发布前须等数据库时钟越过事件时间，不放宽清洗。

建议30分钟维护预算，提前60秒禁止业务/管理/测试/种子写入，连续两次间隔10秒核对稳定；一直保持到四阶段成功或回滚通过。当前没有后端服务，但不得因此假定未来静默已获保障。发布负责人为用户指定的本对话Codex，正式执行时间尚待确定，本轮未创建预约或自动化。

## 已完成与待完成

已完成：源码/配置审查、真实依赖/Java/JDBC/MySQL只读检查、当前指针链与文件哈希验证、残留及时间边界核对、回滚与执行方案。

待正式授权后完成：候选不可变归档、发布前文件备份与数据库安全投影/摘要、维护窗口落实、最终Go/No-Go；正式四任务、MySQL发布及真实服务结果验证均未执行。

回滚核心：成套恢复四latest原字节，保留新文件与已经提交的新batch数据库行；按旧batch恢复可见结果，不删除数据。若既有数据受损则中止，另行评估精确恢复，不用全库覆盖。

## 证据

- outputs/formal-release-readiness-evidence.json：当前代码摘要、配置、依赖、DB数量/时钟、指针、manifest、哈希和两秒采样。
- outputs/formal-release-readiness-extra-evidence.json：MySQL角色分布、固定开发样本及孤立事件核查，Windows监听端口、旧prepared路径。
- outputs/learning-behavior-stability/verification-summary.json：上一阶段96项通过及数据保护证据，本轮未重跑。
- docs/formal-release-preparation-design.md：快照清单、回滚对象/验证、四阶段操作与验证门禁。

本轮仅新增文档与去敏检查JSON。未修改代码、数据库、依赖、系统配置或发布指针，无正式Spark执行、数据删除、Git提交或服务启动。临时诊断通过内存代码执行，未创建/修改脚本或读取凭据值到输出。
