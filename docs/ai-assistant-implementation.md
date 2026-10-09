# AI学习助手第一阶段实施方案

日期：2026-10-05。依据ai-assistant-design.md，本阶段用户已授权：新增独立ai_qa_records、FastAPI接口、Agnes适配、Vue问答页面、身份与本人历史控制。无RAG，无Spark变更，无已有业务表变更。

默认关闭；启用需AI_ASSISTANT_ENABLED=true、AGNES_API_KEY和AGNES_MODEL，固定官方HTTPS Host；配置不完整时只影响AI。实现单轮general/resource两模式，资源上下文仅用户明确允许外发的自编演示资源（资源ID允许列表AI_ALLOWED_RESOURCE_IDS），不抓外链。新增004迁移及映射，保留21个既有API操作并增加四个独立AI接口。

受理时短事务预留pending，调用供应商不持有数据库事务；同UUID相同语义重放，冲突409，超时unknown不自动重试。单worker进程锁/并发限额与MySQL计数，本机多worker不支持共享限流。个人历史30天窗口，暂不自动物理清理；历史可用不要求外部Key，但须功能开关启用。失去资源权限时遮蔽答案。消息纯文本渲染，不执行代码或模型工具。

先运行既有测试基线；旧计数测试改为真实发布元数据断言，OpenAPI断言补新路径但保留原路径；新增供应商MockTransport协议/异常测试及真实MySQL/API权限幂等测试；原后端、前端、Spark各套回归和生产构建，记录真实Agnes验证边界。后续完成结果追加到本文和验收报告。

## 实际实现与文件职责

004_create_ai_qa_records.sql及database/apply_ai_migration.py已执行并验证，仅新增ai_qa_records（21字段、4个非主键索引、2个RESTRICT外键、4个CHECK、utf8mb4_unicode_ci）。执行结果记录ai-migration-verification.json。apply脚本再次运行会核对已存在表而不再创建，生产启动不自动迁移。

backend/app/core/ai_config.py按环境读取可选配置；models/ai_qa.py映射新表；schemas/ai_assistant.py限制问题、模式、UUID4和外发确认版本；services/ai_assistant.py负责额度预留、幂等、个人历史和结果发布；services/agnes.py仅发送文本Chat Completions，不启用工具、重定向或重试；api/ai_assistant.py复用current_user。httpx0.28.1已存在于开发环境，现补入运行requirements，未额外安装包。

新接口：GET /api/ai/capabilities、POST /api/ai/questions、GET /api/ai/questions/{request_uuid}、GET /api/ai/history。已有21个API操作保留，总25个。pending返回202；同语义终态重放返回200含原记录，冲突409；新的模型失败POST返回502或504并持久化failed/unknown；GET/重放以记录状态表达此前错误，不再次调用模型。这是明确的传输契约细化。

Vue /assistant使用现有登录守卫；api/assistant.ts独立60秒请求超时；types/assistant.ts校验和状态提示；AiAssistantView.vue提供通用/资源模式、问题输入、外发确认、纯文本回答、状态刷新及本人历史分页。AppShell仅在已登录且服务端开关启用时显示菜单；配置查询失败被局部消化，不阻断原导航。

## 启用与运行

现有环境激活和backend/run.py启动方式保留。配置仅从后端进程环境加载，backend/.env.example是参考，不自动读取。默认AI_ASSISTANT_ENABLED=false，主系统不要求Key或模型。要启用须用户在本机安全设置AI_ASSISTANT_ENABLED=true、AGNES_API_KEY和AGNES_MODEL后重启后端。不要发Key到聊天，不使用VITE_*，不把真实值写入.env.example、Git或命令历史。

固定供应商Host为https://apihub.agnes-ai.com/v1，不接受任意地址。默认总超时45秒、输出上限1024token、用户20次/UTC日、总100次/UTC日、并发2，只支持单worker。缺少Key或模型时ready=false，禁止提交，但已启用的历史读取不依赖Key。未配置或开启真实Agnes，此轮未调用真实模型，不宣称模型权限、费用或供应商政策已验证。

资源模式由AI_ALLOWED_RESOURCE_IDS明确列出许可外发的自编资源，空列表拒绝全部资源上下文；依然检查published及resource_version。UI输入资源ID，不自动发送资源正文，暂未增加详情页答疑入口。不是RAG，不抓取外链、不使用向量库、不查询Spark画像。

## 事务、幂等与安全边界

认证查询会话在外部await前关闭；额度和pending在独立短事务受理，供应商调用不占数据库事务，完成后独立事务发布。单进程RLock加数据库pending计数限制并发。相同UUID请求处理期间不二次外发；超时为unknown，人工新UUID重新提问可能额外消耗。超过120秒pending在读取/受理时恢复为unknown，避免崩溃后卡死。

个人历史只能查询JWT用户，管理员也不能查看他人；不返回provider_request_id、指纹、token用量等内部字段。资源下架或不再允许外发时遮蔽问题和答案。明显凭据格式拒绝，但不能保证识别所有隐私。供应商返回工具调用、空答案、截断答案、非法JSON/过大响应均拒绝；无模型执行权限。网页仅文本插值，不解释HTML/脚本；登出或页面卸载清理内存，不持久化问题到浏览器。

历史显示最近30天，物理记录暂保留；自动到期清理尚未实现，启用前须确认实际保留策略。这一限制不应被表述为已实现30天物理删除。

## 验证及回归适配

后端185、前端54、Spark46，共285全部通过，无失败、错误或跳过。构成：原238+演示工具既有6+新增后端AI36+前端AI5。三个JUnit与日志保存outputs/ai-*-tests.xml、ai-spark-regression.xml及对应log，汇总ai-assistant-verification-summary.json。

旧真实批次断言绑定旧开发数据，先前真实账号联调导致计数变化。仅改测试为实际manifest、MySQL/API与Parquet的同源关系/数量守恒校验；未改Spark jobs/utils/configs。基础OpenAPI测试补充4个AI路径，未移除原有路径。部分Spark固定输入的算法单元断言保持不变。

前端初次HTTP集成断言通过但清理因未设置PYTHONPATH失败；仅精确清理本轮三个临时账号，再以绝对PYTHONPATH重跑，54项及清理均通过。最终原表行数不变、新AI表零行；SHOW CREATE TABLE自增计数因测试插入推进，字段/主外键/索引经实际映射核对一致，不把计数推进说成结构变更。

实际Uvicorn启动成功、25个操作、匿名AI历史401、Vue /assistant HTTP200。Computer正式浏览器验证admin_demo可进入/assistant并看到默认关闭提示，ai-assistant-disabled-page.jpg。Windows文件修改未立即被WSL Vite缓存更新，重启Vue后路由生效，未改系统监听配置。生产构建通过，仅保留既有看板大chunk警告；当前FastAPI/Vue保持运行。

本阶段没有真实Agnes Key、有效模型和收费/政策核验，所以真实模型成功问答与开启状态浏览器端到端尚未验证。模拟Provider测试只证明协议与异常处理；真实MySQL/TestClient测试证明鉴权、历史和事务状态，不能代替真实供应商验收。下一步须单独授权本机凭据配置与最小真实调用验证。
