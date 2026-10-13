# Spark批次重发布只读诊断验收报告

> 历史资料说明（2026-10-13补注）：下文设计、数量、失败与未验收结论属于原记录日期，不代表当前版本；保留原始证据，不将当时未执行的测试改写为通过。 当前技术栈、视频播放证据和各数据口径统一见[答辩当前状态说明](../docs/defense-current-state.md)；本次仅修订文档，没有重新验收或运行Spark。

日期2026-10-06。结论：根因确认，未修复；既有批次展示可用，同批次重发布仍有风险。

## 执行范围

只读查看任务、配置、测试、JUnit、manifest、历史报告；启动一次SparkSession只读取既有Parquet并核对SHA256；通过数据库连接SELECT读取user_profiles，另用SELECT CAST常量JSON复现浮点文本变化。没有INSERT/UPDATE/DELETE/迁移，没有运行任务run或publish_mysql，没有跑会产生数据/manifest写入的Spark全套测试。仅新增本诊断文档与报告，未改业务代码和既有产物。

## 已验证证据

历史project-freeze-spark-tests.xml：48项，1失败、5错误，即42通过。直接失败test_profiles.test_real_publication_repeat，错误Existing profile differs; immutable batch publication rejected。五个推荐测试共同published fixture报Incomplete profile batch。历史defense-final-spark-tests.xml有48通过，但不是今天全量回归证据，不能抵消后续失败。

实际只读对比两个画像批次：20261005T101822Z_56fede2b_p1_338342c9c5d6（prepared）和20261005T102319Z_fdb1d523_p1_338342c9c5d6（completed）。每批Parquet4行，MySQL相应4行均存在；generated_at逐行一致；原Parquet行内容摘要与manifest content_sha256一致；画像Parquet及源ODS users/resources和DWD事件文件哈希均通过。每批只有用户134两处数值差：

interest_profile.weights.python：MySQL0.3758064516129032，Parquet0.37580645161290316，差5.551115123125783e-17。
learning_preference.type_weights.course：MySQL0.2307692307692308，Parquet0.23076923076923078，差2.7755575615628914e-17。

没有发现activity_profile、metric_explanations或非数值结构差异。SELECT CAST两组常量JSON返回上述MySQL数值，直接复现转换，无写入操作。由此确认是MySQL JSON DOUBLE回读表示末位精度差，被精确字符串比较误判，而非行为数据/时间戳变化。验证未重新计算profiles，不能借此声称任意数据分区下浮点聚合都确定。

## manifest现状与连锁原因

原失败会先覆盖prepared再在数据库冲突处退出，文件没有随数据库rollback恢复。旧101822批次目前仍prepared；当前latest指向102319批次，其实际manifest是completed，latest内容SHA256/generated_at与manifest一致。历史project-freeze报告明确记录此前将该成功发布元数据从既有completed latest恢复，并备份失败manifest；本轮未进行恢复。

推荐latest为20261005T102319Z_fdb1d523_r1_8c9946c778bddce8435d，completed，关联上述当前画像；dashboard-latest同源，数据截止2026-10-05 10:23:19.173 UTC。当前完成状态不代表重发布缺陷已修复。

## 是否影响答辩

已发布MySQL画像/推荐和看板文件可供当前页面读取，微小误差不会造成肉眼可见的画像或推荐差异。但演示“同批次重复运行”会触发拒绝，并可能让manifest回到prepared，进而阻断下游新推荐执行，因此不能宣布Spark幂等/故障恢复验收通过。新源batch通常走首次插入，历史报告有首次发布成功，但本轮不跑新批次，不承诺现场必然成功。

建议答辩前经授权最小修复并验证重发布；未修复前不对正式latest运行当前全套发布测试。已发布展示应说明快照时间，近期新增行为不自动进入旧数据批次。当前AI链路与此发布比较问题无关。

## 最小修复建议与下一阶段

具体方案见docs/spark-batch-republication-diagnosis.md：限定浮点指标的语义比较容差，严格保留其他不可变检查；成功manifest不因重试失败降级；隔离真实发布测试，不用正式latest。无需改数据库结构、推荐算法或学习行为。新增测试应覆盖实际MySQLJSON往返、同批次重试、较大数值/计数/键变化拒绝、manifest与DB失败恢复。

本阶段只读诊断完成。没有进行修复、重发布或复跑Spark测试；等待明确确认。
