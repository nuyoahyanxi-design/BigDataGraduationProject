# Spark批次发布稳定性阶段验收报告

> 历史资料说明（2026-10-13补注）：下文设计、数量、失败与未验收结论属于原记录日期，不代表当前版本；保留原始证据，不将当时未执行的测试改写为通过。 当前技术栈、视频播放证据和各数据口径统一见[答辩当前状态说明](../docs/defense-current-state.md)；本次仅修订文档，没有重新验收或运行Spark。

日期：2026-10-06。结论：本阶段验收通过，原有1项失败和5项初始化错误已在隔离全量回归中消除。未将测试结果发布为正式latest。

## 修改文件与原因

1. spark/jobs/user_profiles.py：新增same_profile_json，仅interest_profile.weights.<tag>、learning_preference.type_weights.<type>、learning_preference.completion_rate允许有限数值的1e-12绝对/相对容差。键集合、非指标数值类型、计数、文字、用户ID/批次类型、generated_at仍严格；NaN与布尔值不作为可容差浮点指标。全局canonical、画像公式和Spark聚合不变。

发布existing completed批次时不再先写prepared；MySQL事务校验失败，原manifest和latest均保留。首次发布失败将本次产物标为failed并只记录错误类别，latest不更新。成功后仍原子写completed manifest和latest。

2. spark/jobs/recommendations.py：仅发布状态保护，completed重试不先降级，初次发布失败标failed，允许经完整内容/文件校验后的failed批次重试。推荐公式、排序、过滤、score和数据库不可变比较不变。score为DECIMAL(24,12)，已有12位规范化足以精确往返，不增加不必要容差。

3. spark/tests/conftest.py：新增临时工作区，配置/代码用符号链接供读取，ODS/DWD用副本，所有测试outputs在临时目录。真实发布fixture使用独立随机20990101T000000Z命名空间并在副本内更新批次元数据，仍调用实际MySQL事务；这是测试批次标识，不代表业务时间。结束时仅按临时目录记录的精确batch_id清理该fixture画像/推荐行，禁止使用SQL通配符清理。既有临时用户/资源测试继续finally清理，只删除自身测试记录。

4. spark/tests/test_profiles.py：独立发布fixture，新增精度合法重试、浮点范围外路径/计数/键/时间拒绝、NaN/布尔拒绝、真实MySQL回读重试不更新记录、completed失败原字节不变、新失败批次不成为latest及随后重试恢复。

5. spark/tests/test_recommendations.py：共享published fixture改为独立批次；新增completed发布失败保护和初次失败→重试完成，验证manifest/latest保持规则。

6. docs/spark-publication-stability-design.md：实施依据与验收范围。
7. 本报告、测试日志/JUnit和一致性摘要为输出。

## 测试结果

最终Spark全量：68 passed，0失败/初始化错误，119.96秒。其中管道8、画像25、推荐18、看板统计2、推荐实验9、实验数据准备6。第一轮67项通过后补充失败恢复重试测试，最终以68项结果为准，不累计重复运行次数。

后端服务回归：22 passed，2.25秒；推荐查询14项、Dashboard8项。有一条既有Starlette/AnyIO弃用警告，无失败。

共90项本阶段验证通过；不是整个后端/前端全部测试数量，也不把以前验收次数加进来。此次未改前端或AI，不重新开展浏览器AI测试。

证据：outputs/spark-publication-stability-tests.txt及.xml；outputs/spark-publication-serving-regression.txt及.xml。

## 数据一致性

spark-publication-consistency.json记录测试前后摘要：177个正式manifest/Parquet/latest文件哈希完全一致，changed_formal_files=[]；9表持久行数量与摘要完全一致，changed_tables=[]。

最终持久行数量：users6、resources13、learning_progress11、favorites2、learning_events87、chapter_progress16、chapter_events59、user_profiles30、recommendation_results400。测试临时画像/推荐批次已清理；没有修改既有学习行为、章节进度、正式画像/推荐值或字段结构。MySQL测试中的临时插入可能自然推进AUTO_INCREMENT，但既有持久行均未改变；没有重置自增序列。

正式画像latest继续指向20261005T102319Z_fdb1d523_p1_338342c9c5d6，原completed产物保持。历史101822失败产物不在本阶段擅自改写；它属于此前失败记录，不能把新失败保护理解为已清理所有历史状态。生产未新增正式分析结果，答辩仍需如实展示原快照时间。

## 验收标准

合法浮点JSON往返不误拒绝；真正计数/键/时间/数值冲突仍拒绝；completed失败不降级且latest字节不变；新失败批次标failed而非错误prepared、重试可成功；真实发布测试不污染正式产物；推荐与看板回归通过。以上本阶段标准均达到。

画像和推荐算法文件未修改，Agnes、AI、用户画像计算公式、学习进度及数据库结构未修改。任务代码摘要参与batch ID，后续正式执行会产生新的发布代码版本，保留原历史结果，不对已有批次做迁移。

阶段完成后停止，等待用户确认。不自动启动生产新批次或继续其他功能开发。
