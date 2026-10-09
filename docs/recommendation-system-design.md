# 个性化推荐系统设计 v1

日期：2026-10-04。本阶段实现热门 Baseline 与基于用户画像的内容推荐，生成可解释 Top-N、Parquet/JSON 实验文件和 MySQL 结果。不实现前端、AI、ALS、推荐接口或在线效果实验。

## 目标与输入架构

使用已完成 user_profiles 批次，由画像 manifest 定位同源 ODS users/resources/learning_progress 与 DWD learning_events。校验完成状态、源批次、截止时间和文件哈希；画像必须覆盖快照中全部 active learner 且每人只有一条。规则参数来自 spark/configs/recommendation.json，无密码。

Spark DataFrame 进行行为聚合、最新收藏窗口、标签向量内积、反连接过滤及窗口 Top-N；只有最终有限 Top-N collect 到驱动发布。先落 Parquet 并读回，再 MySQL 单事务发布，最后标记完成及最新指针。每用户每算法最多 N=5；候选不足时返回实际条数，不重复填充。

## 热门推荐 popular_v1

统计完整冻结快照历史，截至 snapshot_at 的有效 learner 行为，不声称“最近”。V_r 为不同用户/资源/北京时间自然日浏览数；S_r、C_r 为不同用户/资源开始、完成数；F_r 为用户/资源最后收藏事件仍是 favorite_add 的用户数。取消收藏撤销该收藏贡献，不产生正热度。

H_r = 1×V_r + 2×S_r + 3×C_r + 2×F_r。

按 H 降序、resource_id 升序，逐用户排除已完成后选 Top-N。没有热度仍可作为冷启动候选，解释明确为“暂无历史热度，按资源编号确定顺序”。分数为原始 H，不与内容分数直接比较。参数为初始经验规则，没有用测试集调优。

## 内容推荐 content_v1

用户向量 U 为已发布画像 interest_profile.weights，在全部标签空间保留正权重；观测用户使用已有行为/显式混合画像，新用户使用显式兴趣画像。资源标签去重，资源向量 R 的标签分量为 1，其余为 0。

cos(U,R)=Σ_{t∈资源标签} U_t / (sqrt(Σ全部用户标签 U_t²) × sqrt(资源去重标签数))。

零向量、空资源标签或没有重合的相似度为 0。分数保留 12 位小数并限制 [0,1]；用户范数包含未在该资源出现的标签，不能仅对交集归一化。无 TF-IDF、无学习能力推断。

内容排序：相似度降序、H 降序、resource_id 升序。正相似候选优先；余量由零相似候选按热度补足。零兴趣用户整份结果走热门回退。回退行 algorithm 仍是 content_v1（表示完整策略），score=0 表示没有标签相似性，reason 明确标注“热门回退”并包含 H；不能将回退伪称内容匹配。另存独立 popular_v1 结果用于 Baseline 比较。

原因例：“与你的行为兴趣画像匹配：python、spark”；explicit_only 则“与你设置的兴趣标签匹配：python”。只有真实交集才生成匹配原因，不声称最近学习、资源质量或能力适配。

## 过滤与确定性

只推荐快照 published 资源。合并 ODS completed 进度和 DWD learning_complete，按 user/resource 反连接去除已完成。同一算法同用户资源只出现一次，排名从 1 连续；资源重复标签不重复算分，完全相同资源投影去重，冲突 ID 拒绝。

全部源时间固定 UTC，活跃日口径 Asia/Shanghai。批次身份包含画像批次及代码、参数 SHA256；参数/代码变更产生新推荐批次。同批次结果与排名必须相同，禁止覆盖冲突结果。生成时间只记在 manifest，第一次创建后重跑保持。

发布事务锁定当前用户（按 ID 顺序）及资源共享锁，核对 active learner、published 及当前无 completed 进度；若冻结结果已过期则拒绝整个批次，不静默移除行改变排名。需重新抽取、画像、推荐。历史表保留不可变结果；以后展示接口仍须重新过滤当前状态，本阶段无展示接口。

## recommendation_results：新增迁移的原因及最小模型

必须新增 003，因为 user_profiles 是用户特征，不能表达一人多资源、多个算法的排名与原因。仅新增此表，不改变核心业务表或画像表。

|字段|类型/空值/默认|说明|
|---|---|---|
|user_id|BIGINT UNSIGNED，非空，无默认|FK users(id)，RESTRICT|
|resource_id|BIGINT UNSIGNED，非空，无默认|FK resources(id)，RESTRICT|
|batch_id|VARCHAR(64) ascii_bin，非空，无默认|推荐批次；关联画像/源批次记录在 manifest|
|algorithm|VARCHAR(32) ascii_bin，非空，无默认|popular_v1 / content_v1|
|score|DECIMAL(24,12)，非空，无默认|H 或余弦；content 回退为 0|
|rank|INT UNSIGNED，非空，无默认|从 1 起，同用户批次算法不重复|
|reason|VARCHAR(1000)，非空，无默认|真实依据及回退说明|

主键(user_id,batch_id,algorithm,resource_id)；唯一索引(user_id,batch_id,algorithm,rank)；批次索引(batch_id)。两个外键 RESTRICT；CHECK 校验算法枚举、非负分数、content 不超过 1、rank≥1、非空原因。没有无用途 id、时间字段或额外实验表，生成时间与参数版本统一存 manifest。rank 为 SQL 保留字，显式反引号引用。

## 结果文件与实验准备

data/ads/recommendations/batch_id=<推荐批次>/results 保存七字段 Parquet；outputs/recommendations/<批次>/results.json 保存方便检查的结果及 metadata。manifest 保存算法版本、完整参数、代码摘要、画像批次、源批次、源截止时间、首次生成时间、用户/资源/输出数量、文件哈希、结果摘要、发布状态。即便候选为零也生成有 schema 的空 Parquet 与 metadata，保存零结果用户数。

后续评价应重新设计训练/测试时间切分，用相同候选池比较两个算法，记录 Precision@K/Recall@K 等；本阶段只准备可复现产物，不用同一历史数据评分冒充离线效果评价。

## 实现与验证

新增 spark/utils/recommendations.py、spark/jobs/recommendations.py、spark/configs/recommendation.json、spark/tests/test_recommendations.py、database/migrations/003_create_recommendation_results.sql。复用已有环境与 MYSQL_*；不创建虚拟环境或安装依赖。旧后端基础测试仅更新数据库表清单，不新增 ORM/接口。

验证兴趣区分、显式冷启动、无兴趣热门回退、下架/完成过滤、相似度手算、收藏撤销、标签及资源去重、零候选、参数边界、真实 Parquet/MySQL、重复运行、事务回滚与批次冲突。串行任务，同一目标目录独占锁；崩溃留下未完成目录保留现场，不能当成功。

本地默认候选笛卡尔积最多 2000000 对，最终记录最多 50000 行；超限失败，不截断。没有分布式负载、在线服务、长期资源历史标签回放或推荐有效性验收。

参考：[Spark 3.5.7 Window](https://spark.apache.org/docs/3.5.7/api/python/reference/pyspark.sql/api/pyspark.sql.Window.html) 用于确定性排名，[MySQL CREATE TABLE](https://dev.mysql.com/doc/refman/8.0/en/create-table.html) 用于主键、约束和索引。算法权重及回退策略为本项目设计。
