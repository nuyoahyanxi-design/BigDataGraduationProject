# Agnes连接超时诊断方案

目标：定位真实provider_timeout，不调整教学检索、引用、数据库或学习链路。新增传输阶段诊断，保留原请求参数、45秒asyncio总上限和HTTPX connect=5。

以随机call_id关联request_start、response_headers、first_byte、response_complete、parsed_validated。日志仅包含UTC时间、单调时钟耗时、HTTP状态和异常类，不包含URL、headers、Key、问题、回答或异常文本。输出outputs/agnes-http-timings.jsonl，写入失败不影响调用。单元测试期间禁止污染真实时序日志。

HTTP状态没有取得时为null，首字节/响应完成未发生时不造时间。非流式供应商回答也采用HTTPX流式传输读取安全大小上限；不改变供应商stream=false。参考与课程逻辑不修改。

网络检查用不含认证的/v1请求，分别比较Windows代理、Windows直连、WSL直连和WSL代理入口。最小修复须为WSL可达的出站代理配置，不绕过TLS、不增加重试、不扩大本机代理至整个局域网，不调整安全限流。当前代理仅Windows localhost，须用户提供安全可达入口后验证；不可冒称修复完成。
