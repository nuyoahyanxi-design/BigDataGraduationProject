# Spark数据处理第一阶段设计 V1.0

日期：2026-10-04。目标：MySQL五表→一致性ODS快照→Spark清洗DWD事件→质量报告；不实施画像、推荐、AI或前端。

## 1. 数据流程与一致性

使用已有WSL Python3.11、Java17、PySpark3.5.7，通过PySpark的JVM网关运行MySQL Connector/J 8.0.33。在一个JDBC连接、REPEATABLE READ、只读一致性事务内抽取五表，再按显式schema创建Spark DataFrame；不以五个独立spark.read.jdbc连接冒充跨表一致快照。

这是有限规模单连接JDBC适配器，使用PySpark驱动端暂存，非分布式JDBC并行抽取。默认每表最多50000行，超限失败，不截断。所有五表拉取完成后关闭事务；Spark落盘不会重新查询变化中的数据库。迟提交的小ID数据由下次全量快照纳入，不用最大ID做增量水位。

ODS为允许字段的未清洗原值快照：users仅id/role/status/interest_tags/created_at/updated_at（不读取或输出password_hash/username/nickname）；resources除content/content_url外15字段；其余表完整字段。JSON保持字符串，业务DATETIME保持原始UTC文本，DWD转Timestamp。合计46个源字段，这是分析投影，不是全库备份；不改数据库。

数据库连接只读MYSQL_HOST/PORT/DATABASE/USER/PASSWORD/CHARSET环境变量；复用激活脚本，密码不进代码/URL/日志/manifest。JDBC driver单独放spark/lib，下载来源和SHA256记录；不修改环境保护目录。

## 2. 工程与分层

spark/jobs/extract.py：五表抽取与ODS manifest；clean.py：事件清洗与DWD/隔离；quality.py：数量守恒、文件校验与质量JSON/Markdown；pipeline.py：完整编排。

spark/utils：配置、Spark会话、schema、JDBC快照、清洗与文件manifest工具；spark/configs/pipeline.json：非敏感本地运行参数。spark/tests：真实链路及独立损坏数据验收。

data/ods/batch_id=<UTC时间_UUID>/表名/存Parquet，每行加_batch_id、_snapshot_at、_source_database、_source_table；根manifest含批次、源版本、投影、行数/schema、事件接收最大时间、文件摘要、完成状态。data/dwd/batch_id=<同批次>/learning_events及learning_events_rejected。outputs/spark-data-pipeline/<batch>/存质量报告。

新批次不覆盖旧批次。ODS先完成manifest，DWD/质量完成后才更新outputs/spark-data-pipeline-latest.json；失败标记或缺完成状态的批次不得当成可消费结果。重跑清洗同批次不覆盖已有DWD，重新执行全链路产生新批次。

## 3. 清洗与质量口径

SparkSession、Python任务进程及执行器timezone=UTC（不修改系统时区）、ANSI=false、严格现代日期解析。空或非正user_id/resource_id过滤；无关联用户/资源隔离；五种合法数据库小写event_type，其余隔离。UUID规范小写UUIDv4，非法隔离；三时间列解析UTC（客户端时间可空），权威时间缺失/非法、occurred<received或权威时间超过快照截止隔离。

同时校验版本、来源、有效性0/1、五事件合法状态组合和SHA256指纹。对通过基础校验的同UUID，如果不可变事件内容（除内部id和批次元数据）冲突，整组隔离；完全相同重复按received_at/occurred_at/id/行摘要确定保留1条，其余记duplicate_event_uuid。不把冲突随意选一条当正常。

合法唯一0回执保留在ODS，在DWD分析事实排除，理由no_state_change，属于正常业务排除而非坏数据。DWD仅有效事实；原始多次真实浏览保留，不在本阶段实现热度日去重或行为权重。

报告包括输入、异常过滤、重复移除、正常无变化排除、输出、主原因统计（互斥）与多原因命中（可重叠）。必须满足input=filtered+output；所有排除行以quality_reason/quality_reasons/quality_class保存隔离Parquet，可追溯。数据损坏测试与真实MySQL批次明确分开，不能混入生产ODS。

## 4. 验收与边界

真实启动SparkSession、读取五表DataFrame、Spark SQL聚合、ODS/DWD Parquet往返读取、行数/内容校验、manifest SHA256；空favorites仍保存显式schema。BIGINT UNSIGNED超Spark有符号64位范围失败，version_no等INT UNSIGNED使用Spark Long。

在独立内存/临时Parquet构造少量空ID、非法类型、重复、UUID冲突和坏时间，证明实际过滤分支；不污染MySQL。验证一致性事务期间外部提交变更对当前快照不可见、下一快照可见，临时验收账号精确清理。

当前MySQL只保留环境/数据库验收样本，报告标明非真实用户数据，不能宣称具有推荐评估价值。尚无CDC、调度、集群、大规模吞吐、任意历史元数据回放；已保存本批元数据/兴趣快照。文件数量及内存上限适合本科MVP，超规模需另行设计。

参考：[Spark3.5.7 JDBC](https://spark.apache.org/docs/3.5.7/sql-data-sources-jdbc.html)、[Spark Parquet](https://spark.apache.org/docs/3.5.7/sql-data-sources-parquet.html)、[MySQL一致性读](https://dev.mysql.com/doc/refman/8.0/en/innodb-consistent-read.html)。
