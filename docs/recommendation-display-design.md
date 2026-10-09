# 推荐结果展示链路设计

日期：2026-10-05。仅实现当前用户推荐查询、画像摘要和推荐页面；用户已授权设计与实施，交付后停止。

## 数据与批次方案

复用既有 recommendation_results（七字段）和 user_profiles（七字段），只增加准确的 SQLAlchemy 映射，不执行 DDL 或迁移，不修改 Spark 算法。最新已发布批次通过 outputs/recommendation-latest.json 定位，该文件包含 batch_id、profile_batch_id、generated_at、as_of_utc 和发布完成状态。不使用字符串最大批次或每用户任意历史批次作为最新结果。

后端从环境变量 RECOMMENDATION_MANIFEST_PATH 读取配置路径，未配置则使用项目 outputs 中的既有最新指针。逐请求读取完整 JSON，只接受 status=completed、mysql_publication=passed。缺少文件表示尚未发布，返回空结果；文件损坏或未完成返回去敏503，禁止把失败当正常空结果。同请求的推荐与画像批次来自一次指针读取，防止混用两个独立最新指针。时间统一显式 UTC 输出。

## API 与权限

新增 GET /api/recommendations/me，默认 algorithm=content_v1，允许指定 popular_v1 用于查看 Baseline。只接受 algorithm 参数；拒绝 user_id 等额外查询参数。身份来自既有 current_user JWT 验证，每条推荐和画像查询都限定当前 user.id。未登录、无效Token或停用账号沿用401。管理员也只能看自己的结果，不新增后台查询。

返回结构：batch_id、generated_at、as_of_utc、algorithm、items、profile、explicit_interest_tags、message。每项包含 resource_id、嵌套 ResourceSummary、algorithm、score、rank、reason。score 使用十进制字符串保留数据库精度；排序保持原批次 rank，过滤后的名次可能有空缺，不重新计算算法排名。默认每用户只看一种算法，避免两个方法的同一资源混在一起。

结果读取联结当前资源，过滤 status!=published 和当前 completed 进度。只读，不新增浏览或学习事件。当前库已过滤完的空结果提示“暂无可展示的推荐，可先浏览学习资源”；新用户尚未批处理不冒充在线冷启动。快照无结果时也返回批次信息，不虚构分数或原因。

## 画像摘要

查询同 user.id 且 batch_id=profile_batch_id 的 user_profiles。摘要包含 batch_id、generated_at、as_of_utc、兴趣权重和证据类型、行为次数、活跃天数、开始/完成资源数及完成率。字段映射已有JSON键，不推断能力。当前显式兴趣独立展示，与冻结画像区分；画像不存在时显示待生成，不将当前标签包装成Spark画像。所有时间注明UTC，完成率无分母显示暂无。

## 前端架构与交互

新增受保护 /recommendations，导航与首页增加入口。types/recommendations.ts 对应响应，api/recommendations.ts 封装请求。页面展示画像摘要、推荐卡片、理由、算法、分数和原始名次；可切换内容推荐与热门 Baseline，说明两者分数口径不能直接比较。点击查看资源沿用已有详情路由，浏览事件只在详情产生。

处理加载、503失败重试、无画像、零推荐及旧请求响应覆盖问题。理由和标签用Vue插值，不渲染原始HTML。不新增图表、看板、后台或AI。

## 验证与数据边界

后端测试通过正式API创建隔离临时学习者，为读取测试明确模拟批次结果和画像（只写本次临时用户结果），使用独立临时manifest路径，不改生产指针或既有结果。验证两用户隔离、401、额外身份参数拒绝、理由、空结果、配套画像、当前下架/完成过滤、未完成批次与缺失指针。测试结束清理限定用户/资源/结果，记录数量前后对照。另只读查询真实Spark已发布批次，确认接口能够读取既有产物，不用模拟数据冒充算法生成。

前端执行类型与构建检查、API和守卫测试及此前模块回归。独立模拟组件入口验证卡片理由、画像、切换及空结果；模拟入口不引用于生产构建，不视为真人端到端验证。真实接口和浏览器模拟组件证据分别记录到验收报告。

组件入口为 frontend/tests/recommendation-ui.html，使用 ?empty=1 验证无推荐和无画像场景；顶部明确标记模拟数据。此入口引入实际 RecommendationsView，不新增生产业务路由。
