"""Generate authored teaching content only; no database access or video creation."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def lesson(goals, explanation, case, caution, code, result, exercises):
    return dict(learning_objectives=goals, content_parts=(explanation, case, caution, result),
                example_code=code.strip(), exercises=exercises)

LESSONS = [
    [
        lesson(
            ['说明RDD的分区、不可变和血缘三个特征', '区分转换操作与行动操作', '解释RDD与DataFrame各自适用的场景'],
            'RDD是Spark提供的弹性分布式数据集。它把数据划分为分区，由任务处理各个分区。RDD的不可变指已有RDD不被原地修改；map等转换会描述一个新的RDD。弹性主要来自血缘：Spark记录数据如何经过转换生成，在需要时可重算丢失分区，而不是保证任何外部故障都能自动恢复。',
            '把学习事件中的秒数加倍，可以形成一个新RDD；在count、take等行动执行之前，转换链通常只描述待执行的计算。RDD适合需要直接控制元素处理的场景；DataFrame包含列名与Schema，便于结构化查询和优化。在Python中使用DataFrame，没有Scala/Java那样的强类型Dataset API。',
            'RDD不等于“全部数据永远在内存中”。缓存需要显式请求，实际存储还受存储级别和资源约束影响。local模式只是本机演示，不是集群部署证据。',
            '''sc = spark.sparkContext
original = sc.parallelize([1, 2, 3], 2)
doubled = original.map(lambda value: value * 2)
print(original.take(3))
print(doubled.take(3))
print(doubled.count())''',
            '原集合样本为[1, 2, 3]，转换后的样本为[2, 4, 6]，条数为3。示例分区数2是教学参数；不同部署应根据数据量与计算资源测量。',
            ['指出示例中哪一行创建血缘，哪几行触发行动。', '将乘2改为平方，说明原RDD为什么仍保持原值。']),
        lesson(
            ['使用parallelize构造教学RDD', '理解从外部文件创建RDD的方式', '避免把大规模数据先集中到Driver'],
            'RDD常见来源包括并行化已有小集合和读取外部数据。parallelize先接收Driver已有的数据，因此适合本课程的小型样本；真实大数据通常从支持的文件系统或数据源读取。文本文件可以由SparkContext.textFile读取，每条记录一般对应一行文本，后续再解析字段。',
            '示例把四条资源主题放入两个分区，查看条数和少量样本。数据来源、编码、输入路径与Schema解析规则应随实验一起记录；创建RDD不代表数据质量已经通过验证。本平台真实业务由已有MySQL到Parquet链路承担，示例不会读写业务数据库。',
            '不要为了调用parallelize而先使用Python读取整份大文件。也不要把本机路径误认为各集群节点都能访问的共享路径。SparkSession已存在时复用spark.sparkContext，避免重复创建活动上下文。',
            '''sc = spark.sparkContext
topics = ["spark", "python", "spark", "mysql"]
rdd = sc.parallelize(topics, 2)
print(rdd.getNumPartitions())
print(rdd.count())
print(rdd.take(3))''',
            '分区数为2、记录数为4。take仅返回有限样本，不代替全量检查。文本输入实践可在自己的临时目录准备文件，再用sc.textFile读取；本示例无需额外数据文件。',
            ['添加一个hadoop主题，重新核对条数与样本。', '说明parallelize与textFile在输入来源上的差异。']),
        lesson(
            ['区分map、filter和flatMap', '组合转换构建处理链', '认识依赖关系与Shuffle的联系'],
            'map对每个元素应用函数，filter保留满足条件的元素，flatMap把一个输入展开为零个或多个输出。这些算子返回新RDD，通常采用惰性求值。按顺序组合算子可把原始记录转换为分析需要的结构，转换函数应清晰且尽量避免依赖外部可变状态。',
            '将两行主题字符串分词，再只保留spark，可以把行级输入变为词级统计输入。示例中的flatMap和filter通常形成窄依赖，任务可处理对应分区；按键聚合等操作则可能需要重新分配数据。是否发生Shuffle应结合具体算子、已有分区器和执行计划判断，不能把所有转换都称为Shuffle。',
            '转换函数在执行器任务中运行。不要通过修改Driver端列表来收集任务结果，也不要把外部数据库写入放入可能重试的简单map教学函数中。',
            '''sc = spark.sparkContext
lines = sc.parallelize(["spark python", "spark sql"], 2)
words = lines.flatMap(lambda line: line.split())
matched = words.filter(lambda word: word == "spark")
upper = matched.map(lambda word: word.upper())
print(upper.collect())''',
            '在这个只有两行的小样本中，输出包含两个SPARK。这里collect仅用于极小教学样本；真实数据优先有限取样或写出结果。',
            ['把筛选词改为python，预测并验证输出。', '用整数小样本实现map平方后filter保留大于4的数。']),
        lesson(
            ['用count、take与reduce取得结果', '理解行动触发计算', '识别collect对Driver内存的风险'],
            '行动操作请求具体计算结果或数据写出，会触发相关转换链执行。count返回记录数，take返回有限样本，reduce通过可组合的函数聚合元素。聚合函数应满足合理的结合规则，分区执行顺序通常不应成为业务正确性的前提。',
            '对四个分数先平方再求数量、样本与总和，可以观察多个行动如何使用同一转换链。若相同RDD要反复复用，可评估cache或persist；缓存是否值得取决于计算成本、复用次数和可用存储，不能默认缓存一切。',
            'collect把全部结果送到Driver，大数据场景可能耗尽内存。take也只用于观察而不是证明整份数据的正确性。对空RDD调用reduce没有聚合初值，需事先考虑空输入；示例刻意使用非空小集合。',
            '''sc = spark.sparkContext
values = sc.parallelize([1, 2, 3, 4], 2)
squares = values.map(lambda value: value * value)
print(squares.count())
print(squares.take(2))
print(squares.reduce(lambda left, right: left + right))''',
            'count为4，take(2)为[1, 4]，平方和为30。输出次序不能推广为所有RDD操作的全局排序保证；需要有序结果时应显式排序。',
            ['把输入改为[2, 4]，先手算平方和再运行。', '说明为什么统计大数据条数应该使用count而不是len(collect())。']),
        lesson(
            ['完成分词、映射和按键计数', '解释reduceByKey的聚合过程', '理解WordCount与学习主题统计的联系'],
            'WordCount将文本行展开为词，将每个词映射为(word, 1)，再按word求和。这是键值RDD的典型处理链。reduceByKey可以在局部先合并，再按需要交换数据完成聚合；实际Shuffle与已有分区布局有关。不要用“所有步骤都发生Shuffle”概括整个程序。',
            '示例统计三行小文本，得到spark、python、sql的出现次数。学习主题统计也可采用类似思路，但真实学习事件必须先清洗、去重并明确权重，不能把文本出现次数直接解释为用户学习能力。排序只为了便于观察小结果。',
            '大小写、标点和空词的处理会影响计数口径。本例只处理已规范的小写词并按空白分词，不宣称通用中文分词能力。聚合函数应无副作用。',
            '''sc = spark.sparkContext
lines = sc.parallelize(["spark python", "spark sql", "python"], 2)
words = lines.flatMap(lambda line: line.split())
pairs = words.map(lambda word: (word, 1))
counts = pairs.reduceByKey(lambda left, right: left + right)
print(counts.sortByKey().collect())''',
            '排序结果为python=2、spark=2、sql=1。这里只收集三个键的小结果。实验报告应记录输入样本、规范化规则及计算方法。',
            ['添加一行spark spark，验证spark计数增加2。', '加入Spark与spark两种写法，使用lower统一后比较统计结果。']),
    ],
    [
        lesson(
            ['识别DataFrame的列名与Schema', '使用显式类型创建小样本', '区分结构化数据与无Schema元素集合'],
            'DataFrame以命名列组织数据，Schema规定每列的数据类型和可空性。Spark可以根据这些结构信息分析并优化查询。Python中的DataFrame不提供Scala/Java强类型Dataset那样的编译期元素类型保证；输入类型和空值仍需主动校验。',
            '示例用用户编号、主题与学习分钟构造三行数据，显式指定long和string类型。将学习分钟保留为数值而非文本，可减少后续聚合前的转换。生产输入通常需检查Schema与预期版本一致，并处理缺失列和脏值。',
            'printSchema只说明当前列结构，不代表业务值均有效。分钟为负数、主题为空等问题仍需要清洗规则。示例不是直接读取线上users表，也不写业务库。',
            '''rows = [(1, "spark", 12), (2, "python", 8), (1, "spark", 5)]
df = spark.createDataFrame(rows, "user_id long, topic string, minutes long")
df.printSchema()
df.show(truncate=False)
print(df.count())''',
            '输出三列user_id、topic、minutes以及3条记录。示例字段仅用于教学，正式系统继续使用已有字段与数据抽取方案。',
            ['添加一个合法样本并验证Schema与条数。', '说明Schema校验和“分钟非负”的业务校验分别解决什么问题。']),
        lesson(
            ['用filter筛选学习记录', '用withColumn派生新列', '显式处理null值而不覆盖原字段'],
            '筛选与列转换是结构化清洗的基础。filter或where接收布尔条件，select选择输出列，withColumn添加或替换派生列。DataFrame转换返回新的查询结果描述，不要求先把整份数据收集到Python。',
            '示例保留topic为spark的记录，把分钟转换为秒。源分钟为空时用coalesce给教学计算提供0，但真实系统应根据业务含义决定保留、过滤还是填补缺失值，不能把所有未知值一律当成0。原minutes列保留便于解释新列来源。',
            'SQL的null不是普通空字符串；比较表达式可能产生未知值，需使用isNull或isNotNull等明确处理。浮点换算和单位必须在报告中说明，避免把分钟当成秒。',
            '''from pyspark.sql import functions as F
rows = [(1, "spark", 12), (2, "python", 8), (3, "spark", None)]
df = spark.createDataFrame(rows, "user_id long, topic string, minutes long")
selected = df.filter(F.col("topic") == "spark")
result = selected.withColumn("seconds", F.coalesce(F.col("minutes"), F.lit(0)) * 60)
result.select("user_id", "minutes", "seconds").show()''',
            '保留用户1和3，对应秒数720与0。0是本示例的填补规则，不代表用户3实际学习了0秒，真实分析应区分未知与观测值。',
            ['只保留minutes非空的数据，比较记录数。', '新增hours列并明确其数值类型与单位。']),
        lesson(
            ['通过groupBy计算主题统计', '用临时视图执行Spark SQL', '对照两种表达方式的结果'],
            'groupBy按键组织记录，配合count、sum、avg等聚合函数生成统计表。Spark SQL可对注册的临时视图查询；DataFrame表达式与SQL都由Spark执行，适合用不同写法验证相同统计口径。临时视图不是MySQL持久化表。',
            '示例按topic统计事件条数和分钟总和，再用SQL重复计算。主题维度的统计可帮助看板解释学习活动，但仅有条数无法推断学习质量；正式平台仍以清洗事件、有效状态变化和冻结批次为分析依据。',
            'sum对null的处理与count(*)统计行数不同，需要注明分母和缺失值口径。没有显式orderBy时不要依赖结果行顺序；小样本对比时排序是为了方便核对。',
            '''from pyspark.sql import functions as F
rows = [(1, "spark", 12), (2, "python", 8), (1, "spark", 5)]
df = spark.createDataFrame(rows, "user_id long, topic string, minutes long")
df.groupBy("topic").agg(F.count("*").alias("events"), F.sum("minutes").alias("minutes")).show()
df.createOrReplaceTempView("lesson_events")
spark.sql("SELECT topic, COUNT(*) AS events, SUM(minutes) AS minutes FROM lesson_events GROUP BY topic ORDER BY topic").show()''',
            'spark主题有2条记录、17分钟，python主题有1条记录、8分钟。两种写法统计值一致；输出表只是当前Spark会话中的教学结果。',
            ['添加一条python记录，两种方式都重新计算。', '统计每位用户的记录数，并说明为什么不能把记录数直接称为完成课程数。']),
        lesson(
            ['写入并重新读取Parquet', '理解列式格式和Schema保留', '在临时目录安全演示数据输出'],
            'Parquet是常见列式存储格式，保存Schema并支持结构化读取，适合离线分析分层输出。Spark写入Parquet的路径通常是目录，目录内可能有多个数据文件和标记文件，不能简单当作单个文件处理。',
            '示例仅在自动创建的临时目录内写入两条主题记录，再读取核对结构与条数。overwrite只用于本例新建临时路径；正式ODS、DWD、ADS采用已有批次目录，不能随意覆盖历史分析结果。临时目录适合本机演示，集群需所有相关节点可访问的数据路径。',
            'Parquet格式本身不保证事件唯一、数据有效或没有未来泄漏。存储格式、清洗质量和实验时间划分是不同层面的要求。不要将示例路径替换成平台线上data目录后直接覆盖。',
            '''from pathlib import Path
from tempfile import TemporaryDirectory
df = spark.createDataFrame([(1, "spark"), (2, "python")], "user_id long, topic string")
with TemporaryDirectory(prefix="lesson_parquet_") as folder:
    path = str(Path(folder) / "snapshot")
    df.write.mode("overwrite").parquet(path)
    restored = spark.read.parquet(path)
    restored.show()
    print(restored.count())''',
            '读回后包含user_id和topic两列、2条记录。with代码块结束会清理该临时目录，不影响平台的ODS/DWD历史快照。',
            ['新增一列并读回，核对Schema。', '解释为什么分批存储应记录批次编号和来源，而不只保存一个latest文件。']),
        lesson(
            ['过滤缺失用户及非法事件类型', '按事件UUID去重', '将时间字符串转换为分析时间字段'],
            '学习行为清洗应先明确规则和统计口径。教学样本包含缺失用户、非法类型、重复UUID及非法时间；过滤和类型转换后才能进行统计。规范事件类型与唯一事件标识有助于减少重复提交造成的误计数。',
            '示例只保留resource_view和learning_start两种教学事件，将时间转换为timestamp，并过滤无法解析的时间。UTC配置用于统一解释无时区教学文本。真实平台仍使用现有DWD规则和全部合法事件类型，本课不会修改生产任务。',
            'dropDuplicates在同UUID存在不同内容时不保证保留哪一条。这里重复记录完全一致；语义冲突需确定性规则或异常隔离，不能用任意去重掩盖冲突。清洗输出必须记录输入、过滤和输出数量。',
            '''from pyspark.sql import functions as F
spark.conf.set("spark.sql.session.timeZone", "UTC")
rows = [("e1", 1, "resource_view", "2026-10-01 09:00:00"), ("e1", 1, "resource_view", "2026-10-01 09:00:00"), ("e2", None, "learning_start", "bad"), ("e3", 2, "unknown", "2026-10-01 10:00:00")]
df = spark.createDataFrame(rows, "event_uuid string, user_id long, event_type string, time_text string")
valid = df.filter(F.col("user_id").isNotNull() & F.col("event_type").isin("resource_view", "learning_start"))
valid = valid.withColumn("occurred_at", F.to_timestamp("time_text"))
clean = valid.filter(F.col("occurred_at").isNotNull()).dropDuplicates(["event_uuid"])
print(df.count(), clean.count())
clean.show(truncate=False)''',
            '输入4条、输出1条，保留唯一的e1事件。正式数据质量报告还应分别统计异常原因；存在多重异常时须说明计数是否互斥。',
            ['添加一个合法learning_start事件，预测输出数量。', '构造同UUID不同用户的冲突，说明为什么应隔离或拒绝，而不是任意保留。']),
    ],
    [
        lesson(
            ['区分监督学习的分类与回归', '明确特征、标签和预测目标', '使用简单基线理解评估'],
            '机器学习从样本中建立输入与目标之间的模型关系。监督学习样本包含特征与标签：分类预测离散类别，回归预测连续数值。聚类等无监督任务没有相同形式的目标标签。先定义任务、观测时间和标签来源，比先挑复杂模型更重要。',
            '本课用微型数值样本演示回归基线：仅根据训练标签的平均值输出常数预测，再计算测试误差。平均值基线很简单，但为后续模型比较提供参照。平台的标签与行为推荐已有独立实现，本教学内容不引入新推荐算法。',
            '用户浏览或收藏不能直接作为学习能力的真实标签。合成样本只用于理解公式，不能写成真实用户效果。预测目标为连续数值时，应使用回归指标而不是分类准确率。',
            '''train_targets = [2.0, 4.0, 6.0]
baseline = sum(train_targets) / len(train_targets)
test_targets = [5.0, 7.0]
predictions = [baseline for _ in test_targets]
mae = sum(abs(y - p) for y, p in zip(test_targets, predictions)) / len(test_targets)
print(baseline, predictions, mae)''',
            '训练均值为4，预测为[4, 4]，平均绝对误差为2。该结果不代表模型已适合真实应用；需要更多数据和独立评价。',
            ['给出一个分类任务和一个回归任务，并定义标签。', '修改训练标签观察基线变化，说明为什么不能用测试标签计算训练均值。']),
        lesson(
            ['分离训练数据与测试数据', '对时间序列采用时间先后划分', '避免特征处理中的未来信息泄漏'],
            '训练集用于拟合规则，测试集用于评价未参与拟合的数据。对学习行为或推荐任务，采用时间划分可更贴近先观察历史、再预测后续行为的过程。随机划分并非所有场景都合适；评价方案需与任务部署方式匹配。',
            '示例以日期为边界，训练只包含边界之前的两条数据，测试包含边界当天及之后的数据。训练特征、标签和资源候选还应满足观测时点可用；即使事件日期分开，使用未来更新的画像也可能泄漏信息。',
            '不能先在全部数据上计算均值或挑选特征，再拆分训练测试。边界相等归入哪一侧必须明示。同一用户的多条事件也应避免把未来完成记录混入训练阶段。',
            '''from datetime import date
rows = [(date(2026, 10, 1), 2.0), (date(2026, 10, 2), 4.0), (date(2026, 10, 3), 6.0)]
cutoff = date(2026, 10, 3)
train = [row for row in rows if row[0] < cutoff]
test = [row for row in rows if row[0] >= cutoff]
assert max(row[0] for row in train) < min(row[0] for row in test)
print(len(train), len(test))''',
            '训练2条、测试1条，所有训练日期严格早于测试日期。真实实验要记录具体范围、快照批次及冻结时间，不凭空补充测试结果。',
            ['将边界改为10月2日，重新统计训练测试条数。', '举例说明使用全量用户画像会如何泄漏测试阶段兴趣。']),
        lesson(
            ['区分数值特征与类别特征', '只在训练集拟合预处理参数', '用训练统计量转换测试样本'],
            '特征应由预测时已知的信息构造。数值特征可按训练统计量进行标准化，类别特征可通过编码转为模型输入。预处理也是模型流程的一部分，其参数必须只从训练集估计，再一致应用到验证或测试样本。',
            '示例用训练数值计算均值和总体标准差，再转换一个测试值。总体标准差的分母为样本数量，是本例明确的公式；使用不同库时应核对标准差约定和缺失值处理。示例没有依赖额外机器学习库。',
            '不能用测试数据重新计算均值，也不能忽略零标准差导致除零。类别编码应考虑未知类别，分钟、秒等单位也需一致。缩放不是所有模型的必需步骤，应根据模型与数据特征选择。',
            '''from math import sqrt
train = [1.0, 2.0, 3.0]
mean = sum(train) / len(train)
variance = sum((value - mean) ** 2 for value in train) / len(train)
scale = sqrt(variance) or 1.0
test = [4.0]
transformed = [(value - mean) / scale for value in test]
print(mean, scale, transformed)''',
            '均值为2，标准差约0.8165，测试值4转换后约2.4495。测试值没有影响训练均值和标准差，因此保持训练与测试隔离。',
            ['把训练值全部设为2，解释示例如何避免除零。', '增加一个主题类别特征，讨论未知主题的编码策略。']),
        lesson(
            ['通过混淆计数计算Precision和Recall', '理解准确率在类别不平衡中的局限', '区分分类指标与推荐Top-N指标'],
            '二分类可将预测与标签交叉计数为真阳性、假阳性、假阴性和真阴性。Precision关注预测为正的样本有多少正确，Recall关注真实正例有多少被找回，Accuracy关注全部样本的正确比例。没有单一指标能解释所有业务需求。',
            '示例把1视为正类，并明确每个分母；分母为0时本例返回0以保证计算可执行，真实报告应说明该约定和样本规模。漏检代价高时Recall重要，误报代价高时Precision重要，但仍需结合场景。',
            '本课分类Recall不是平台推荐实验的Recall@10；推荐还涉及用户集合、候选、排序与相关性标签。不要把两者混写，也不要根据四条合成样本宣称模型有稳定准确率。',
            '''truth = [1, 1, 0, 0]
predicted = [1, 0, 1, 0]
tp = sum(y == 1 and p == 1 for y, p in zip(truth, predicted))
fp = sum(y == 0 and p == 1 for y, p in zip(truth, predicted))
fn = sum(y == 1 and p == 0 for y, p in zip(truth, predicted))
precision = tp / (tp + fp) if tp + fp else 0.0
recall = tp / (tp + fn) if tp + fn else 0.0
accuracy = sum(y == p for y, p in zip(truth, predicted)) / len(truth)
print(precision, recall, accuracy)''',
            'Precision、Recall和Accuracy均为0.5。完整实验还应记录类别分布、样本量和误差情况，必要时比较多个阈值。',
            ['把predicted改为全部0，分别计算三个指标。', '解释分类Recall与推荐Recall@10为什么不能直接比较。']),
        lesson(
            ['组织可复现的训练与评价流程', '保存配置、指标与数据说明', '正确报告基线和实验限制'],
            '一个完整实验应包含数据准备、划分、训练、预测、指标和结果记录。固定随机种子只能控制部分随机性，不能替代冻结输入数据、软件版本和算法参数。评价结果需要有足够测试样本，不应为了表现更好反复针对测试集调参。',
            '示例使用固定种子划分八个小样本，训练均值基线，再计算测试MAE。结果打印为JSON便于复核；整个过程只在内存运行，不写平台推荐表或修改AI配置。真正的训练算法可在独立课程练习中进一步研究，本平台算法保持不变。',
            '随机划分用于本章独立同分布微型示例，学习行为时间任务仍应按上一章的时间方法划分。固定种子的结果也只对给定输入与流程有效；微型样本误差不能证明泛化性能。',
            '''import json
import random
samples = [(x, 2.0 * x + 1.0) for x in range(8)]
random.Random(42).shuffle(samples)
train, test = samples[:6], samples[6:]
baseline = sum(y for _, y in train) / len(train)
mae = sum(abs(y - baseline) for _, y in test) / len(test)
report = {"algorithm": "mean_baseline", "seed": 42, "train_count": len(train), "test_count": len(test), "mae": mae}
print(json.dumps(report, ensure_ascii=False, sort_keys=True))''',
            '结果包含算法名、种子、训练6条、测试2条和实际计算的MAE。重复运行应得到相同结果；改变样本或流程时必须重新记录配置，而不是沿用旧指标。',
            ['重复运行确认结果一致，再修改种子比较划分。', '写一段实验限制说明，包含合成数据、样本量和基线复杂度。']),
    ],
]

def main():
    courses = json.loads((ROOT / 'database/seeds/course-chapters.json').read_text(encoding='utf-8'))
    if len(courses) != 3 or any(len(c['chapters']) != 5 for c in courses):
        raise SystemExit('Expected the existing three five-chapter courses')
    for course, lessons in zip(courses, LESSONS, strict=True):
        for chapter, entry in zip(course['chapters'], lessons, strict=True):
            explanation, case, caution, result = entry['content_parts']
            chapter.update({key: value for key, value in entry.items() if key != 'content_parts'})
            chapter['content'] = f"# {chapter['title']}\n\n## 核心知识\n{explanation}\n\n## 案例理解\n{case}\n\n## 常见误区\n{caution}\n\n## 示例预期结果\n{result}"
            chapter['video_url'] = '/demo/video.mp4'
    output = ROOT / 'database/seeds/course-teaching-content.json'
    output.write_text(json.dumps(courses, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Prepared 3 courses / 15 complete teaching chapters. No database or video writes.')

if __name__ == '__main__':
    main()
