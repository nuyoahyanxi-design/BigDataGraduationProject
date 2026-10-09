# Spark批次重发布只读诊断

日期2026-10-06。本阶段仅定位故障，不修改代码、数据库、行为或既有批次，不运行publish_mysql、完整pipeline或发布测试。

## 流程架构

spark/jobs含extract、clean、quality、pipeline、user_profiles、recommendations、dashboard_metrics及实验任务；spark/utils提供Session、MySQL一致性快照、清洗、画像/推荐计算、文件校验；spark/configs维护配置，spark/tests维护计算与真实发布测试。当前配置local[2]、driver_memory1g、shuffle分区2，是真实本地Spark，不是已部署多机集群。

pipeline通过同一MySQL JDBC一致性只读快照读取五张核心表，生成UTC时间+随机8位源batch。ODS五表Parquet附批次/快照/来源；DWD清洗learning_events，另存拒绝记录；manifest保存来源时间、行数、schema和文件SHA256。质量通过才更新pipeline-latest。

user_profiles消费ODS用户/资源及DWD事件，Spark聚合后生成JSON画像。画像batch为源batch+p1+画像计算/任务代码摘要；generated_at复用既有manifest。输出ADS Parquet、内容摘要，事务发布MySQL user_profiles，成功后写completed manifest和latest。

recommendations验证completed画像及其源ODS/DWD、文件哈希、画像内容摘要和来源时间后计算推荐，生成版本参数关联批次，Parquet和MySQL发布。dashboard_metrics输出daily_metrics Parquet与dashboard-latest，关联推荐/画像批次。在线后端读取既有已发布结果；Spark不由每次学习操作同步触发。

## 根因

user_profiles.py第23行把MySQL JSON读回后canonical序列化，与原Spark JSON字符串精确比较。实际MySQL JSON转换使DOUBLE末位文本变化：0.37580645161290316变为0.3758064516129032；0.23076923076923078变为0.2307692307692308。仅SELECT CAST绑定JSON AS JSON就能复现，不需要任何INSERT/UPDATE，因此不是用户数据改变，也不是本轮Spark重新计算造成的差异。

两批逐字段比较中，唯二差异为用户134的interest_profile.weights.python和learning_preference.type_weights.course；绝对差分别5.551115123125783e-17与2.7755575615628914e-17。generated_at、activity_profile和metric_explanations一致，JSON对象键顺序已由canonical处理，不是此次原因。

## 连锁问题

run在第66行先把既有completed manifest重新写为prepared，再调用publish_mysql。MySQL比较拒绝后事务回滚，但文件状态不回滚，保留prepared。recommendations的published共享fixture加载该画像，load_inputs第89行拒绝非completed，于是五项用例setup失败。不是五个独立推荐算法缺陷。

测试test_profiles.test_real_publication_repeat使用pipeline-latest实际批次，连续调用真实run，不是只读测试，可能改变正式manifest。测试触发的是实际发布实现缺陷：日常重跑同一源快照也会遇到，而不只是测试断言错误。

## 最小修复建议（未实施）

1. 仅发布端JSON等价比较，对明确定义的浮点指标路径（兴趣weights、type_weights、completion_rate）采用小容差，例如abs/rel 1e-12并测试边界；键集合、类型、整数计数、用户/批次、日期及解释字段保持严格。不要对整个JSON所有数值模糊比较，不覆盖已有批次，不删不可变保护。
2. 已completed的重发布验证失败时保留原成功manifest与latest，单独记录本次attempt失败；新批次仍按prepared→completed。不要先降级已发布产物。
3. 发布测试隔离源快照/测试批次，不依赖正式latest；覆盖MySQL真实JSON回读、合法重试、真实语义冲突拒绝及失败前后manifest/DB完整性。
4. 代码摘要参与batch ID，后续修改会生成新画像版本，明确保留旧批次；不用手工修库或批量重写Parquet。

不建议改画像算法/推荐权重或全局canonical作为第一步。Spark浮点聚合和Python无序collect求和可能另有确定性边界，需未来独立测试，当前不是已证实根因。
