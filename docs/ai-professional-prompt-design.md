# AI专业教学提示词优化设计

2026-10-05。本轮仅修改agnes.py的SYSTEM_PROMPT内容，不改调用参数、解析、安全检查、API、数据库或前端。保留原普通教学、400–600字符、15行代码及完整性要求；仅对Spark/Hadoop/大数据问题应用专业约束。

专业约束：优先稳定概念，不捏造版本默认值；配置数字标注示例参数及版本差异。区分RDD、DataFrame、Scala/Java Dataset及Python API支持。Shuffle描述依赖分区与执行计划，不把所有join等操作绝对描述为必然Shuffle，不宣称始终只用内存/磁盘。区分HDFS存储、YARN资源管理和MapReduce计算。普通问题不强加大数据术语。

依据Spark3.5.7官方SQL指南与RDD指南：
https://spark.apache.org/docs/3.5.7/sql-programming-guide.html
https://spark.apache.org/docs/3.5.7/rdd-programming-guide.html

验收为当前完整后端回归；不把模拟响应测试当作真实模型语义质量评价。用户已报告此前真实RDD/WordCount/Shuffle测试通过，本轮不追加收费调用。
