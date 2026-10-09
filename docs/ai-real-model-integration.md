# AI真实模型接入验收

日期：2026-10-05。状态：真实认证失败，正常回答验收待完成。

## 配置与数据流
沿用现有 Vue /assistant → FastAPI /api/ai/questions → AgnesProvider → ai_qa_records → 本人历史查询。未新增功能、未修改业务表、未执行Spark任务。

后端进程环境读取 AI_ASSISTANT_ENABLED、AGNES_API_KEY、AGNES_MODEL。固定服务地址 https://apihub.agnes-ai.com/v1，Bearer认证、非流式单轮调用、45秒总超时、无自动重试。密钥由用户隐藏输入，仅存在后端进程环境；不写入文件、Git或报告。关闭终端后重新启动需重新输入。

在已激活环境的Ubuntu终端，从项目根运行：

`PYTHONPATH=backend python outputs/start-ai-real-model-secure.py`

模型名称必须来自该服务控制台，Key必须是该API服务的有效凭据，并具有模型权限。修改配置时先在该终端Ctrl+C停止后端，再执行上述命令。不要在聊天中发送凭据。

## 实际验证及修复
正式页面 http://localhost:5173/assistant，student_demo由用户手动登录。发现启用状态下Element Plus表单组件未导入，只补齐 AiAssistantView.vue 组件导入，保持架构与行为链路。此前构建及测试未覆盖真实启用表单，此次浏览器验证补足该证据。

通过页面提交一次非敏感Spark学习问题。配置模型 agnes-3.0-flash，真实服务返回401或403，适配层映射provider_auth / HTTP 502，没有取得回答。数据库保存failed记录；刷新后本人历史与查看记录可用，不自动重试。

超时、认证失败、限流通过6项受控故障测试验证，属于模拟供应商错误，不代表真实网络超时验收。正常真实回答必须在凭据修正后继续验证。
