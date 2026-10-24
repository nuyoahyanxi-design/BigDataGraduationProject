# OULAD 独立分析与看板接入验收报告

日期：2026-10-23。

## 实际完成
已执行 spark/jobs/oulad_analysis.py，Spark 3.5.7、local[2]。从已校验 ZIP 提取七张 CSV，独立 ODS Parquet 保存原始字段，DWD 规范缺失与交互整数；任务内关联和聚合承担 DWS 逻辑职责，ADS 输出汇总 JSON。没有独立 DWS 物理表，也没有运行 HDFS 集群。

批次：20261023T090521Z_d00d214a。专用发布指针 data/external/oulad/analysis/latest.json，采用临时文件＋os.replace 原子发布。数据和发布均位于独立外部来源目录，未调用既有 MySQL 抽取、平台画像或推荐发布任务。原子失败保留旧指针为静态设计审查，未通过故障注入声称运行验证。

## 实测数据对账
- 去重学生：28,785。
- 选课记录：32,593。
- 课程模块：7，开课批次：22。
- 聚合交互行：10,655,280。
- 总点击量：39,605,099。
与独立原件核查完全一致。日趋势、活动分类、课程模块的点击量总和均与总点击量一致；最终结果总和与选课记录数一致。原件 SHA-256：f2ed1902616c1fe8d2824d872c0b7d2d72be435bf0124d077044fe4be2c6d3e4。

## 接口及页面
新增管理员只读 /api/dashboard/public-education，读取专用发布，不返回学生明细；缺少发布返回 available=false，路径逃逸、损坏结果、批次不符拒绝读取。保留原 /overview 不变。

看板新增“平台数据／OULAD公开教育数据”切换，默认平台数据。公开数据展示四项概览、相对日趋势、原始选课结果、活动点击前8类和匿名模块交互量；详情保留全部活动、许可、引用、运行环境、批次和校验值。切换、刷新仅读取结果，不运行Spark。两个来源的指标互不冒用。

## 验证结果
- 前端类型检查、构建通过；171 项测试通过、12 项跳过，22 个测试文件通过、3 个跳过；原有大包提示保留。
- 后端共12项通过：7项外部发布与权限／异常文件测试、3项原件审查工具测试、2项既有实际MySQL只读启动／OpenAPI／连接检查。单元 fixture 不依赖被Git忽略的真实文件，合成测试值不当作真实结果。
- Spark 真正执行完成，独立对账通过；详情输入输出均10,655,280，检查的异常与关联缺失为0；不声称所有潜在数据问题均不存在。
- 真实 admin_demo 看板：外部4图表成功渲染、来源详情可展开；回切平台仍为用户6、资源12、行为119、画像4，原有批次显示不变。
- 桌面1440px内容宽1425px；手机390px内容宽375px，无横向溢出。
- 截图：outputs/oulad-analysis/desktop.png、mobile.png；独立对账：reconciliation.json。
- git diff --check通过。

## 真实数据边界
OULAD 是外部2013–2014历史教育数据，不是本平台新增账号、课程、收藏、视频时长或章节完成。相对日-25至269不是2026自然日期。最终结果不是本平台课程完成率；点击聚合行不是同等数量的独立视频观看。没有生成推荐效果、准确率提升或新推荐模型；学生端推荐仍使用现有平台批次。

## 修改文件
spark/jobs/oulad_analysis.py；backend/app/api/dashboard.py、schemas/public_education.py、services/public_education.py及测试；frontend/src/components/PublicEducationDashboard.vue、types/public-education.ts、api/dashboard.ts、views/DashboardView.vue及测试；docs/oulad-analysis-design.md和本报告。

## 边界与状态
未改业务数据库、既有账号、课程绑定、视频、推荐算法或配置。重新启动已有后端以加载新只读接口；没有修改认证流程。未暂存、提交或推送Git，前期改动保留。完成实现与自动／真实浏览器验证，保留公开数据看板等待人工验收。
