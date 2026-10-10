# 正式批次发布结果与验收报告

日期：2026-10-10。状态：正式发布成功，各阶段验证通过，无失败重试、无旧批次删除。

## 正式发布结果

| 项目 | 结果 |
|---|---|
| 代码版本 | 19b4739598a86a2307f62b135c7d27de2b78af1e，main，工作区干净 |
| 发布开始 | 北京时间2026-10-10 14:04:51.425（UTC06:04:51.425） |
| 最终指针提交完成 | 北京时间2026-10-10 14:14:26.372（UTC06:14:26.372） |
| ODS | completed，五表分析投影6/13/11/3/90，数量、Parquet读回、SHA256通过 |
| DWD | completed，90输入→89有效，1条no_state_change，4条v5桥接完整保留 |
| 画像 | completed，4行ADS及MySQL发布，逐字段读回通过 |
| 推荐 | completed，24个候选组合→两算法36行，过滤/排名/读回通过 |
| 看板 | completed，30自然日指标，Parquet读回与配套批次通过 |
| latest | 四指针最终阶段才切换，completed、同源、哈希与读取通过 |
| 历史保护 | 原173个manifest/Parquet不变；原四指针已备份后按授权更新；旧MySQL结果内容不变 |
| 回滚 | 本轮未触发；121文件旧备份复核通过，保留全部新/旧批次 |

新批次：

- 源：20261010T060537Z_fb2d2acb。
- 画像：20261010T060537Z_fb2d2acb_p1_5f4a3dd7c998。
- 推荐：20261010T060537Z_fb2d2acb_r1_ce8dd66f8a6c5b25f9cd。
- 看板：20261010T060537Z_fb2d2acb_d1_170f4f800992。
- 源快照截止UTC2026-10-10 06:05:36.910（北京时间14:05:36.910）。

## 阶段1：写入静默与候选/备份复核

用户已授权正式发布。运行前复查commit及冻结源码/配置哈希、备份清单121项。Windows及WSL应用端口8000/5173均未运行；现有应用入口原已停止，保持停止，不启动测试/种子/额外批处理。初始Spark进程检查无任务。

两次相隔10秒的MySQL只读一致性快照：学习事件均90，最大事件时间均UTC2026-10-09 13:00:00.879，最大接收时间13:00:00.870；表结构、受保护内容摘要及数据库外键状态一致。未来事件0，数据库时间已覆盖事件边界，临时测试账号0。

每阶段前后重新校验数据/代码/历史文件。监测保证是应用入口关闭加重复摘要检查，不把它描述为数据库全局写锁。整个执行期间未发现输入漂移。

## 阶段2：ODS/DWD/ADS计算检查点

| 检查点 | 输入 | 输出 | manifest | 新文件根目录 | 验证 |
|---|---|---|---|---|---|
| ODS | users6/resources13/progress11/favorites3/events90 | 同输入 | completed | data/ods/batch_id=20261010T060537Z_fb2d2acb | 原任务读回及各Parquet SHA256通过 |
| DWD | 90事件 | 89有效+1拒绝 | completed | data/dwd/batch_id=20261010T060537Z_fb2d2acb | 数量守恒、无异常、4条v5、读回和SHA256通过 |
| 画像计算 | 89有效事件、同源用户/资源 | 4学习者画像 | prepared | data/ads/user_profiles/batch_id=20261010T060537Z_fb2d2acb_p1_5f4a3dd7c998 | 原计算、内容摘要、完整七字段Parquet读回通过；此时未SQL发布 |
| 推荐计算 | 4用户×6候选资源=24组合、同源画像/行为/进度 | 两算法36结果 | prepared | data/ads/recommendations/batch_id=20261010T060537Z_fb2d2acb_r1_ce8dd66f8a6c5b25f9cd | 原计算、完整七字段Parquet、SHA256及完成/发布/测试夹具过滤/去重/连续排名通过 |

质量报告仅1条正常无状态变化排除，没有invalid_event_uuid/future_authoritative_time。ODS中的4条有效v5与DWD保留集合完全相同。

每个检查点完成后先输出结果，再单独执行下一检查点；正式四latest始终保持旧值。

## 阶段3：ADS数据库发布与看板

画像调用未修改的publish_mysql函数发布4行；真实MySQL逐字段读回，JSON浮点指标沿用既有1e-12容差，其他身份/时间/计数严格。校验后新manifest completed，mysql_publication=passed。

推荐调用未修改的publish_mysql函数发布36行；原事务检查active learner、published资源及当前完成状态，事务内读回与Parquet严格一致。校验后新manifest completed，mysql_publication=passed。

看板调用原dashboard_metrics.run读取本次工作目录推荐指针和同源ODS/DWD，生成30日Parquet及completed manifest，校验读回、SHA256、推荐/画像配套批次。

本阶段只追加新数据库批次；正式四指针仍不切换。SQL总数画像30→34、推荐400→436；旧批次记录摘要一致。其余业务表数量不变：users6/resources13/progress11/favorites3/events90/course_chapters26/chapter_progress17/chapter_events65/ai_qa_records50/ai_course_contexts25。

## 阶段4：最终提交及独立验收

切换前通过实际后端只读服务核对4学习者×2算法共8组结果，确认本次推荐/画像配套、当前完成过滤、隐藏资源过滤；看板来源与本次三批次一致。使用工作目录指针验证，不启动HTTP服务，不写学习事件。

所有检查通过后复制本次质量报告及推荐JSON到新的正式outputs批次目录，不覆盖旧目录。四指针临时文件预先写入、校验，再逐文件os.replace；维护状态覆盖整个切换。单文件原子替换不等于四文件跨文件原子事务，已通过服务入口关闭避免暴露中间状态。

切换后再次核对四指针原字节哈希、同源关系、manifest/Parquet文件哈希、数据库旧行与业务保护摘要。独立验证再次通过真实后端推荐和看板只读服务（正式指针路径），结果均指向新批次。

推荐物理结果36行，正式展示/看板统计30行来自既有隐藏资源406过滤；各算法可见行分别4/4/4/3，共15行，不将展示过滤误判为结果丢失。原推荐公式及过滤语义没有修改。

## 调度适配说明

本轮发布执行器outputs/execute-formal-release.py是被Git忽略的操作产物，不修改已冻结生产源码。既有任务默认立即SQL提交/切换指针，无法直接满足用户要求的最终统一指针切换；因此本次采用工作目录承接阶段元数据。

ODS/DWD/质量直接调用原extract/clean/quality组成任务。画像/推荐准备通过AST提取已冻结run函数在SQL发布前的原计算前缀，保留原字段、公式、参数、身份哈希、Parquet校验；prepared画像仅在这次已校验的准备计算入口被允许消费，不伪标completed或mysql_publication=passed。阶段3再调用原SQL发布函数，成功校验才标completed。看板原任务使用同源工作目录指针。阶段4才更新正式四latest。生产公式、数据库、业务ID生成均未重写，候选Git版本保持不变；执行器SHA256已记录在最终证据。

## 历史保护与回滚信息

旧177个正式文件中，只有四个授权发布指针变化；其余173个旧manifest/Parquet哈希一致。包含两个历史prepared现场，未删除、未改写。所有旧画像/推荐行不变，新增行仅属于本次精确批次。

旧备份路径：D:\BigDataGraduationProject\outputs\formal-release\20261010T055720Z-6b9d6c42。121项及清单校验再次通过，没有覆盖旧备份。

若后续需要回滚，应重新进入静默，按此备份原字节成套恢复四旧latest，校验旧源20261005T102319Z_fdb1d523及配套画像/推荐/看板关系、哈希和数据库旧行；保留本次新批次及数据库追加结果，不DELETE或DROP。旧业务数据/文件若损坏则需单独评估，不能只靠指针恢复。此说明不是本轮已执行回滚。

## 证据与验证边界

本次执行目录：outputs/formal-release/execution-20261010T060451Z-444db06b。

- quiet/ods/dwd/profiles_prepare/recommendations_prepare/profiles_publish/recommendations_publish/dashboard/commit-evidence.json：九个检查点结果。
- precommit-service-checks.json：提交前8组推荐与看板服务检查。
- final-verification.json：提交后独立文件、数据库、服务读取与备份校验。
- evidence-sha256.json：结果证据文件摘要。
- 各阶段日志位于outputs/formal-release-*.log；活动状态formal-release-active-context.json已completed。

本轮实际正式Spark/Parquet/MySQL发布及服务函数验证通过。没有用旧测试冒充新发布验证；没有启动前后端或进行真人浏览器登录/页面验收，不能声称完整浏览器端到端发布验收。AI两表仅核对安全元信息与数量，未读取私人问答正文。应用服务保持发布前原有停止状态，未自动恢复。
