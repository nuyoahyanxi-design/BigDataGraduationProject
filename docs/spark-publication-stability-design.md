# Spark批次发布稳定性修复设计

目标仅发布幂等、失败保护及测试隔离，不改变画像/推荐计算、数据字段或学习行为。

## 比较

在画像MySQL发布边界增加JSON等价比较，仅interest_profile.weights.<tag>、learning_preference.type_weights.<type>、learning_preference.completion_rate允许有限数值的abs_tol/rel_tol=1e-12。键集合、类型、整数计数、文本、用户ID、批次ID和时间严格。推荐score为DECIMAL(24,12)，已有精确规范化不改变；全局canonical和Spark算法不变。

## 状态

重复发布completed产物时，不在MySQL校验前降级为prepared；latest仅成功后更新，失败保留原指向。初次发布失败将本次manifest标为failed，不伪装completed或遗留prepared；安全记录错误类别，不输出凭据。画像及推荐发布端都做同类状态保护，推荐算法与排名不修改。保留内容/文件哈希严格校验和数据库事务。

## 测试隔离

Spark测试使用临时工作区，配置/代码只读链接、ODS/DWD冻结源副本、临时outputs。真实发布fixture生成独立随机源批次并更新副本批次元数据，调用真实MySQL发布；只清理该fixture精确批次ID的画像与推荐行，不修改既有记录或学习状态。正式latest与manifest不作为可写测试目标。

测试前后比较正式指针、manifest及Parquet哈希、核心/学习/画像/推荐持久行摘要，确保一致。原有临时用户/资源测试保留其明确的finally清理。报告只输出数量/哈希，不输出密码或凭据。

## 验证

新增真实MySQL浮点回读合法重试、小容差与真实冲突区分、严格键/计数/时间、completed失败保护、新批次failed、latest不变、推荐发布失败保护。执行Spark全套（含推荐和看板）以及后端推荐/看板回归。初始与最终正式数据一致性是验收门槛。未成功不宣称全部通过。
