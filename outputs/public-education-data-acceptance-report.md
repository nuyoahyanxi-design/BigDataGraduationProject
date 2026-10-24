# 公开教育真实数据来源与字段验收报告

日期：2026-10-23。

## 当前结论
OULAD 原始 ZIP 已从 UCI 官方托管地址完整下载并核验。来源取得阶段完成；尚未导入业务数据库、运行 Spark 外部数据流程或接入正式看板，不能把本阶段写成“真实数据已在系统上线”。

## 来源与许可
- 数据 DOI：[10.24432/C5KK69](https://doi.org/10.24432/C5KK69)。
- [UCI 官方页面](https://archive.ics.uci.edu/dataset/349/open+university+learning+analytics+dataset)。
- 许可：CC BY 4.0，署名 Kuzilek、Hlosta、Zdrahal；已保存来源文档和 ATTRIBUTION。
- 原件：data/external/oulad/oulad-uci.zip，46,748,244 字节。
- SHA-256：`f2ed1902616c1fe8d2824d872c0b7d2d72be435bf0124d077044fe4be2c6d3e4`。
- ZIP 全部 8 个条目 CRC 验证通过，七张 CSV 均完整流式读取，不只抽样。

## 实测数据规模
- 去重匿名学生：28,785。
- 学生—课程批次记录：32,593。
- 课程模块：7；课程开课批次：22。

| 表 | 实测行数 |
|---|---:|
| courses | 22 |
| studentInfo | 32,593 |
| vle | 6,364 |
| assessments | 206 |
| studentRegistration | 32,593 |
| studentAssessment | 173,912 |
| studentVle | 10,655,280 |

studentVle 是聚合交互表，不能将 10,655,280 行称为同等数量的独立观看或章节完成事件。原始总点击量为 39,605,099，含义是 sum_click 总和。

## 质量检查
- 必要列齐全；完整读取验证 CSV 与 ZIP CRC。
- 已查注册—选课、成绩—考核定义／选课、交互—选课／资源关联，以及负点击量、交互数字格式和重复选课键。
- 本轮这些检查的异常计数为空（0），不代表其他未执行检查都通过。
- 已检查空值及 ?／NA 等原始缺失标记，明细保存在 audit.json；缺失值不自动删除。当前 UCI 文件检查结果见下方，不能假定其他镜像的空值编码相同。
- 原始相对日范围 -25 至 269，保持相对课程开始日，不捏造当前时间戳。
- 独立核查工具的三项合成 fixture 测试通过，覆盖去重口径、异常关联保留和不完整档案拒绝；fixture 不是本报告真实数据来源。

## 接入决策
外部匿名学生不建成可登录账号，匿名课程不映射成现有五门自编课程；无收藏、视频时长和章节完成证据时不补造。采用独立 source_dataset 和独立外部分析入口，在看板提供明确的数据来源切换。Spark 保持 local，DWS 为任务内逻辑聚合，不创建虚构物理层。现有 MySQL 五表提取和 50000 行上限不适合直接承载原始大表，因此不改现有正式批次。

## 文件
- 原始 ZIP 与 ATTRIBUTION：data/external/oulad/（Git 忽略）。
- 来源记录：outputs/oulad-intake/source-check.json。
- 机器核查结果：outputs/oulad-intake/audit.json。
- 数据引用：docs/oulad-data-source.md。
- 接入设计：docs/public-education-data-design.md。
- 工具：scripts/audit_oulad_source.py；测试：backend/tests/test_public_data_intake.py。

## 历史问题与处理
原开放大学网站下载链接返回404；未验证的 Figshare 候选入口受403／超时限制，未使用该条目。后通过论文及 UCI 官方托管来源取得数据。慢速下载的失败 part 文件保留，不参与分析，也不提交Git。

## 阶段边界
未修改现有账号、课程、视频、业务数据库、后端接口、Spark任务、推荐算法或配置，未执行 git add/commit/push。完成原始数据来源与字段验收后按项目阶段规则停止；下一阶段为独立 Spark 分析及看板数据源接入，需保存其设计、实现与真实运行验收，不将其提前计为完成。

## 缺失值实测补充

下列字段存在缺失标记，原件保留，后续按字段语义处理：

- studentInfo：{"imd_band": 1111}
- vle：{"week_from": 5243, "week_to": 5243}
- assessments：{"date": 11}
- studentRegistration：{"date_unregistration": 22521, "date_registration": 45}
- studentAssessment：{"score": 173}
