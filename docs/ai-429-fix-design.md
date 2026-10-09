# AI连续请求429诊断与修复设计

2026-10-06。本机只读数据：student_demo当前UTC日20条问答、pending=0、provider_rate_limit累计0。当前Agnes供应商429被转换为502，项目个人额度默认20/global100；课程与通用共用额度，失败/超时已预留请求仍计数。现有额度按UTC日计算，北京时间08:00刷新而非00:00。内部拒绝发生于预留前，无新QA记录。

最小调整：APP_ENV=development默认个人100/全局1000，仍在原配置上限内；production保持20/100，显式AI_USER_DAILY_REQUEST_LIMIT和AI_GLOBAL_DAILY_REQUEST_LIMIT优先，并发2不变。不得删除记录或清零额度。来源通过X-AI-Limit-Source和Retry-After响应头及安全日志明确区分user_daily/global_daily/concurrency/provider_rate_limit，不改变API路径/问答响应模型。日志仅记录UTC时间、用户ID、course/general模式、来源、状态及耗时，供应商状态只保留数值。

前端ApiError透传白名单限流来源，AI专用反馈友好提示，不影响其他业务错误。课程/通用复用反馈；历史provider_rate_limit标记也显示友好文字。没有真实供应商429证据，不增加供应商自动重试，避免额外消耗；认证、用户隔离、UUID幂等、额度统计规则、UTC边界、并发和超时继续保留。

验证开发/生产默认与显式覆盖，连续课程/通用请求，限额来源和Retry-After，重放不重复调用，日志无问题/Key，前端429提示；执行全量前后端、TS和构建，再安全重启原后端加载配置并进行真实验收。
