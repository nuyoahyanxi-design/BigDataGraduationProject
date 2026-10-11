# 项目系统架构

日期：2026-10-11。依据当前源码与配置整理；本轮仅文档及服务启动检查，没有执行Spark任务或数据库迁移。

## 总体架构

```mermaid
flowchart TD
    U[学习者 / 管理员] --> V[Vue 3前端
TypeScript / Element Plus / ECharts]
    V -->|HTTP / JWT| API[FastAPI后端API
权限、事务与业务服务]
    API --> DB[(MySQL业务数据库
用户、资源、学习行为、课程与进度)]
    API --> MEDIA[本地课程视频静态服务
25个正式MP4]
    API -.许可与外发确认.-> AI[Agnes模型接口
通用与课程AI问答]
    DB -->|Spark JDBC分析投影快照| ODS[ODS
一致性快照 / Parquet]
    subgraph SPARK[Spark处理任务：local2本机批处理]
        ODS --> DWD[DWD
有效行为清洗与质量校验]
        DWD --> DWS[DWS逻辑聚合
任务内计算；无独立落盘层]
        DWS --> P[用户画像
兴趣与行为特征]
        P --> R[推荐计算
popular_v1 / content_v1]
        DWS --> M[看板统计
日指标与行为聚合]
        P --> ADS[ADS
画像 / 推荐 / 日指标Parquet]
        R --> ADS
        M --> ADS
    end
    ODS -.资源与用户元数据.-> P
    ODS -.候选资源目录.-> R
    ADS --> PUB[校验与批次发布
保留历史版本]
    PUB --> RES[(MySQL画像与推荐结果表)]
    PUB --> PTR[outputs最新批次指针
及质量报告]
    RES -->|读取| API
    PTR -->|批次与统计读取| API
    API --> SHOW[结果展示
用户画像 / 个性化推荐 / 管理看板]
    SHOW --> V
```

[Draw.io可编辑源文件](architecture.drawio)可通过diagrams.net的“文件→打开→从设备”导入。图中的MySQL业务库与结果表属于同一MySQL部署，拆分节点仅表示职责。

## 分层与实际实现

| 层次 | 实现与来源 |
|---|---|
| ODS | spark/jobs/extract.py：users、resources、learning_progress、favorites、learning_events分析投影快照 |
| DWD | spark/jobs/clean.py、quality.py：有效行为清洗、质量核验 |
| DWS逻辑层 | 聚合在spark/utils及画像、推荐、看板任务中完成；没有data/dws目录或独立DWS发布任务 |
| ADS | data/ads/user_profiles、recommendations、daily_metrics下的批次Parquet |
| 画像 | spark/jobs/user_profiles.py；校验后发布MySQL user_profiles |
| 推荐 | spark/jobs/recommendations.py；热度基线与融合标签/行为/热度，发布recommendation_results |
| 看板 | spark/jobs/dashboard_metrics.py；日指标Parquet及配套批次信息 |
| 编排与实验 | pipeline.py编排抽取/清洗/质量；recommendation_experiment.py独立离线评价，不自动发布线上 |

实际存储链路为ODS→DWD→ADS。DWS在图中是理解聚合职责的逻辑标注，不代表新增了分层任务、目录或数据库表。

## 在线业务与离线边界

- frontend/src/router/index.ts定义登录、首页、资源、章节学习、推荐与管理看板；画像在推荐页展示。
- backend/app/main.py注册用户、资源、学习行为、课程、推荐、看板、管理员和AI接口，并挂载/videos。
- MySQL采用database/migrations/001–007 SQL迁移；章节行为并非全部直接进入五表分析，只有既有桥接规则生成的主学习事件进入链路。
- Spark参数来自spark/configs/pipeline.json，当前master为local[2]；使用本地Parquet，没有部署HDFS或集群调度器。
- 前端刷新读取已发布结果，不触发Spark；画像及推荐通过MySQL结果表展示，看板结合已发布文件及当前数据库部分信息。
- AI是可选外部模型能力，受认证、许可、确认和额度控制；没有向量数据库或自动学习进度更新。
- 视频文件位于frontend/public/videos，绑定通过现有课程字段与目录规则识别，本轮不修改绑定或视频。

## 运行与验证边界

当前服务通过原有脚本启动；登录页面已实际查看，后端OpenAPI与前端首页的HTTP检查见本轮交付说明。此架构文档不替代全系统验收。测试、正式发布与最新视频证据见根README链接；密钥、私有配置、原片备份、候选、数据文件不随展示文档公开。
