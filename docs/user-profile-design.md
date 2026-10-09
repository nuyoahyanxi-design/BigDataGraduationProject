# 用户行为画像设计

本阶段只实现兴趣、活跃、学习偏好画像，不推断学习能力，不提供推荐或画像 API。

## 输入和架构

读取已完成且文件哈希校验通过的同批次 DWD learning_events、ODS users 和 resources。DWD 只有行为，主题标签与用户显式兴趣必须从冻结 ODS 获取，不读取变化中的在线元数据。仅为快照中 active learner 生成结果，包含无行为用户。使用 Spark DataFrame 聚合；最终每用户一条记录落 Parquet 并事务发布 MySQL。

## 指标与公式 v1

- 截止时间为 ODS snapshot_at，统计完整快照历史中截至该时间的有效行为；不使用本次运行墙钟作为统计边界。
- 行为次数：按五个 event_type 分别 count，DWD 已排除无效收据及重复 UUID。
- 活跃天数：occurred_at 从 UTC 转为 Asia/Shanghai 后取日期，countDistinct；收藏取消计入活跃行为。
- 完成情况：不同 learning_start 资源数 S；其中出现 learning_complete 的资源数 C；完成率 C/S，S=0 时为 null。仅代表观察到的流程完成情况，不代表能力。
- 兴趣证据：浏览按用户/资源/北京时间自然日去重，每次权重 1；开始权重 2；完成权重 3；每资源最新有效收藏事件若为 favorite_add，再加 2，取消后不加收藏分。按资源标签数均分证据。行为标签分数归一化，显式兴趣均分；两者同时存在时 0.7 行为 + 0.3 显式兴趣，只有一种时该种权重 1；都没有时空列表。
- 学习类型偏好：不同开始资源每个计 1、其中已完成的每个计 2，按资源 type 累加并归一化。无开始记录时为空，不根据浏览猜测学习偏好。
- 冷启动：无行为但有显式兴趣为 explicit_only；无任何证据为 no_evidence；有行为为 observed。所有用户输出零次数与零活跃天数，无分母完成率为空。

时间转换使用 Spark 的 [from_utc_timestamp](https://spark.apache.org/docs/3.5.7/api/python/reference/pyspark.sql/api/pyspark.sql.functions.from_utc_timestamp.html)。现有资源快照没有历史标签版本，指标代表该批次元数据下的偏好；全历史不加衰减，避免无依据的参数复杂度。

## user_profiles 最小结果模型

需要新增 002 迁移，只有此表；业务五表不增加字段。

|字段|类型|用途|
|---|---|---|
|user_id|BIGINT UNSIGNED 非空|用户 FK，RESTRICT|
|batch_id|VARCHAR(64) ascii_bin 非空|源批次与规则内容哈希构成，联合主键|
|generated_at|DATETIME(3) 非空|第一次生成 UTC 时间，重跑保持|
|interest_profile|JSON 非空|主题权重及冷启动来源|
|activity_profile|JSON 非空|行为次数、活跃天数|
|learning_preference|JSON 非空|开始/完成资源数、完成率、类型权重|
|metric_explanations|JSON 非空|源批次、截止时间、规则版本、指标解释|

主键(user_id,batch_id)，索引(batch_id)，生成时间索引不增加。JSON 使用对象，必填无默认。无需 analysis_batches、推荐结果表或后端 ORM/API。

## 发布与幂等

计算规则固定在计算代码 v1 中，计算与发布代码的 SHA256 前 12 位进入画像 batch_id。同一输入、代码、规则只有一个身份。第一次记录实际生成时间；重跑复用该时间并核对结果，不覆盖不同结果。结果存 data/ads/user_profiles/batch_id=...，包含上述七字段；JSON 列和生成时间在 Parquet 中为字符串，MySQL 生成时间为 DATETIME(3)。

先保存与读回验证 Parquet，再单事务写全部 MySQL 记录；已存在主键必须逐字段相同，否则拒绝发布，不更新历史结果。MySQL 提交后标记 manifest 完成并更新最新指针；文件和数据库不是分布式事务，指针只表示全部步骤成功，可重跑恢复未完成发布。

## 验证计划及限制

使用合成 Spark 数据验证不同用户、零行为、显式兴趣冷启动、无证据冷启动、取消收藏、自然日去重、完成率分母与重复计算。真实运行验证冻结 DWD 到 Parquet、MySQL 及重跑一致。样本规模很小，验证工程正确性，不证明画像有效性。完成本阶段后停止，后续推荐需另行授权。

## 执行方式和运行边界

在 WSL 项目根目录激活已有 bigdata-graduation-env 后，执行 `python -m spark.jobs.user_profiles`，默认读取 outputs/spark-data-pipeline-latest.json；可用 `--source-batch` 指定冻结批次。验证命令 `python -m pytest spark/tests/test_profiles.py -q`。数据库参数复用 MYSQL_* 环境变量，密码不写入 SQL 或任务文件。

v1 采用多次 Spark 聚合及少量聚合结果 collect，延续此前每源表 50000 行的本机链路约束，不是分布式大规模画像服务。任务串行运行，尚未实现多进程发布锁；数据库主键保护不产生重复行，但并发文件写入未验收。浮点分数未做跨 Spark 版本位级一致性保证；同环境同批次验收覆盖重复运行。若进程在 Parquet 写完而 manifest 尚未保存时强制终止，留下孤立文件需人工核对并保留现场后修复；不会静默覆盖。当前快照的全部行为为空时所有学习者也能输出零画像，但本次测试直接覆盖的是多个无行为用户，而非零行事件文件整批发布。

原后端基础测试的数据库表清单调整为五张 ORM 业务表加 user_profiles，ORM 映射和业务接口保持原有范围；这一修改用于防止已授权结果表使旧清单断言错误失败。
