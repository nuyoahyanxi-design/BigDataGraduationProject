# 后端基础工程

包含基础工程、用户模块四接口、资源模块五接口、学习行为模块八接口和推荐展示查询接口。资源写入仅管理员可用；行为和个人查询需要JWT。GET /api/recommendations/me 默认读取当前用户 content_v1 推荐，可用 algorithm=popular_v1 查询热门方法。推荐与画像来自已完成发布的 Spark 批次，接口不重新计算算法。

学习操作必须提供JSON event_uuid（UUIDv4），浏览还须session_id；DELETE取消收藏也使用JSON请求体。同一次逻辑操作重试保持UUID，真正新操作生成新UUID。原事件回执表示过去处理结果，当前状态通过个人查询获取。API行为名称大写，数据库编码仍为小写。详细边界见docs/learning-event-module-design.md。

在 WSL Ubuntu 22.04 使用现有环境启动：

```bash
source /mnt/d/BigDataGraduationProject/environments/activate-bigdata.sh
cd /mnt/d/BigDataGraduationProject/backend
python run.py
```

访问 http://127.0.0.1:8000/docs 查看基础文档。根路径返回 404 是预期行为。

运行基础验收：

```bash
python -m pytest tests -q --tb=short
```

配置参考 .env.example；应用只读取环境变量，不自动读取 .env。已有激活脚本安全加载 MySQL 凭据，run.py 私密加载/首次创建 Windows 凭据管理器中的 JWT 密钥。直接 uvicorn 启动需预先安全设置 JWT_SECRET；不要把密码或密钥写入命令、报告或版本控制。生产部署的凭据方式需后续单独设计。

依赖已在现有虚拟环境核验，requirements.txt 与 requirements-dev.txt 固定本次使用版本。必要时在同一环境执行 `python -m pip install -r requirements-dev.txt`；不要重建虚拟环境或修改系统 Python。

ORM 不自动建表，数据库结构以 database/migrations 为准。基础测试只读；业务测试创建隔离临时用户/资源/记录并限定清理。推荐展示测试明确模拟读取用的批次结果，不将其称作 Spark 生成，同时只读检查既有 Spark 真实发布批次。默认读取项目 outputs/recommendation-latest.json，可用 RECOMMENDATION_MANIFEST_PATH 指定绝对路径；未完成或损坏的指针返回503，不当作正常空结果。设计和验收见 docs/recommendation-display-design.md、outputs/recommendation-display-acceptance-report.md。
# 管理员后台基础

`GET /api/admin/users` 提供仅管理员可读的分页用户摘要；`GET /api/admin/batches` 提供数据管道、画像、推荐和看板各阶段最近发布记录。缺少生成时间显示未记录，不推断成功时间；批次展示读取发布元数据，不实时监控任务或执行Spark。资源管理继续使用原有 `/api/resources` 创建、修改与状态接口。设计及验收见 docs/admin-module-design.md、outputs/admin-module-acceptance-report.md。
