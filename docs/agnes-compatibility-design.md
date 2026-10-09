# Agnes结束原因兼容修复设计

2026-10-05。本轮只改后端适配与记录逻辑；不改模型、前端、数据库结构、权限或Spark链路。

接受非空文本的stop、缺省/null及length；length为成功回答并用现有error_code=answer_truncated标记，不自动重试。tool_calls/function_call仍拒绝，content_filter保持失败；未知结束原因拒绝。原有文本长度、角色、工具、安全限制保留。

响应摘要只允许HTTP状态、枚举化结束原因、正文存在性/长度、工具内容是否非空和非负Token数，不记录任意供应商文本、正文、提示、Key或headers。通过outputs/ai-provider-response-summaries.jsonl按request_uuid关联记录，不改表。摘要写入失败告警但不覆盖已提交业务结果；单worker约束沿用。历史记录18不能回填未知原始响应。
