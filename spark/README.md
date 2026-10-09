# Spark数据处理第一阶段

必须在WSL激活已有环境，并从项目根目录运行：

```bash
source /mnt/d/BigDataGraduationProject/environments/activate-bigdata.sh
cd /mnt/d/BigDataGraduationProject
python -m spark.jobs.pipeline
python -m pytest spark/tests -q --tb=short
```

配置来自MYSQL环境变量，非敏感Spark参数见configs/pipeline.json。PySpark3.5.7、Java17；Connector/J8.0.33位于lib。每次完整运行产生独立ODS/DWD批次，不覆盖旧数据；outputs/spark-data-pipeline-latest.json只指向全流程成功批次。

抽取通过PySpark JVM单JDBC一致性连接，不是五连接并行抽取。每表最多50000行，超限失败；适合当前MVP，不能据此宣称分布式抽取能力。五表投影排除账号隐私/密码哈希及资源正文/外链，ODS是分析快照，不是完整备份。

jobs/extract.py、clean.py、quality.py可被编排调用；使用build_spark启动会话，按extract→clean→quality顺序传同一batch。不要单独重新清洗到已存在DWD目录；重复完整运行产生新批次。批次manifest非completed不得使用。失败批次保留用于诊断，不自动删除。

驱动下载来源为Maven Central官方坐标com.mysql:mysql-connector-j:8.0.33；jar SHA256：e2a3b2fc726a1ac64e998585db86b30fa8bf3f706195b78bb77c5f99bf877bd9。二进制与数据均忽略Git；部署时按坐标恢复并核对摘要。当前本机WSL到Windows MySQL使用未启用TLS的本地连接，公网部署须另行设计。

质量报告区分异常、重复与正常0回执排除；ODS保留原事件，DWD事实仅is_effective=1。以上描述数据链路阶段；后续画像及推荐任务如下。尚无Spark集群调度或前端实现。

## 画像与推荐阶段

在已有 WSL 环境中从项目根目录运行：

```bash
python -m spark.jobs.user_profiles
python -m spark.jobs.recommendations
python -m spark.jobs.recommendations --profile-batch <已完成画像批次> --top-n 5
python -m pytest spark/tests/test_recommendations.py -q --tb=short
```

画像默认消费数据链路 latest；推荐默认消费画像 latest，再由画像定位同源 ODS/DWD，不混用其他批次。参数见 configs/recommendation.json；数据与密码不进入 Git。需要先执行数据库迁移 001、002、003。

推荐分别生成 popular_v1 和 content_v1，后者包含明确标注的热门回退，score=0 不表示标签相似。结果保存在 data/ads/recommendations/batch_id=<批次>/results；实验 JSON 在 outputs/recommendations/<批次>/results.json，完整 metadata 在 manifest 和 outputs/recommendation-latest.json。新参数/代码生成新批次，同批次重跑校验而不覆盖冲突结果。

离线过滤 published 与未完成资源，发布前检查当前状态。过期资源/用户/完成状态导致整个发布失败，应从 pipeline→user_profiles→recommendations 生成新的冻结批次。未完成或 writing manifest 保留用于排查；没有完成指针不可作为成功结果。此处是离线推荐产物，不是展示接口；以后展示仍须过滤当前业务状态。

## 推荐离线实验阶段

```bash
python -m spark.jobs.recommendation_experiment
python -m spark.jobs.recommendation_experiment --train-batch <较早快照> --test-batch <较晚快照>
python -m pytest spark/tests/test_recommendation_experiment.py -q --tb=short
```

实验配置见 configs/recommendation-experiment.json。使用训练时真实 ODS 元数据和进度重算训练画像，不能直接复用全历史线上画像。Top-10 与两个已有算法规则保持一致，结果只保存 outputs/experiments/recommendation/<run_id>，不发布到 MySQL 或替换线上推荐指针。latest.json 指向成功实验；metrics.json 中 null 表示没有可评价标签，不代表零命中率。联合推荐计时包含两种算法的共享 Spark 计算，不用于单算法速度比较。具体边界和公式见 docs/recommendation-experiment-design.md。

## 明确模拟的实验数据准备

```bash
python -m pytest spark/tests/test_experiment_seed_data.py -q --tb=short
python -m spark.jobs.prepare_experiment_data
python outputs/verify-experiment-data-preparation.py
```

生成 50 个资源、30 名学习者的独立离线模拟 ODS/DWD，再调用已有实验，完全不写 MySQL，不创建可登录账号。主题、人数、固定种子及历史模拟时间见 configs/experiment-data-preparation.json；生成器先冻结训练状态，写完训练快照再生成测试行为。受控标签沿用后端校验字典。模拟 ID 只在该数据集内有效，不能用作线上账号身份。

data/ods、data/dwd 独立批次 manifest 标为 synthetic；不会替换生产数据链路/画像/推荐 latest。阶段配置、资源种子、学习者分组、质量和复现核验见 outputs/experiment-data-preparation/<run_id>，成功阶段指针为其 latest.json。实验仍在 outputs/experiments/recommendation/<实验ID>，data_origin 明确模拟主题偏好模型。旧空测试集实验的特定验证脚本仅用于旧阶段记录；本阶段请使用上述专用核验脚本，不将模拟指标当真实用户效果。
# 数据分析看板统计

在WSL项目根目录激活已有bigdata-graduation-env后执行：

```bash
python -m spark.jobs.dashboard_metrics
python -m pytest spark/tests/test_dashboard_metrics.py -q
```

任务读取已完成推荐发布对应的ODS/DWD冻结批次，生成data/ads/daily_metrics Parquet及outputs/dashboard-latest.json。仅进行描述统计，不运行新推荐算法，不修改MySQL。缺少推荐发布时使用数据链路最新已完成批次，配套推荐显示未生成。后端GET /api/dashboard/overview读取已发布结果，管理员可在/dashboard查看。刷新页面不会执行任务；批次、数据性质与截止时间请查阅docs/dashboard-design.md。
