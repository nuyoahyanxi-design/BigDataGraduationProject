# 课程 AI 助手 V1 实现说明

日期：2026-10-05。本阶段是第一阶段已确认设计的最小增量实现，保留原独立AI页面及通用接口。

## 1. 功能与页面

课程学习页教学内容下增加CourseAiAssistant折叠面板。默认课程助手，点击打开才检查能力/读取本课程个人历史；打开页面或切换章节不自动提交模型问题。通用AI继续用原askAI及/api/ai/questions，切换模式清除外发确认，保留原/assistant及全部历史入口。

面板复用AiAnswerContent、ai-feedback、Axios JWT认证、原近30天问答机制。支持问题、回答、服务端引用、章节跳转、pending状态刷新、历史分页和展开/收起。章节引用跳转调用现有selectChapter，遵守busy/pending规则；问答本身不写学习事件或改变学习进度。当前选章只作为有词汇命中的排序加分，不强制把无关章当作引用。组件离开或Token变化时丢弃迟到结果。

## 2. 复用架构

原api/ai_assistant.py提取execute_question作为共享执行入口；原POST /api/ai/questions调用它，不改旧输入和返回结构。课程新路由也调用同一入口和服务reserve/finish、同一AgnesProvider。共享settings、current_user、问题凭据检查、全局RLock、每日额度、并发、供应商错误、状态恢复和UUID记录。

旧reserve新增可选course_options，默认None时保持原资源片段流程；课程请求携带chapter_id及固定course-assistant-v1指纹命名空间。上下文只在新UUID请求中检索，在同一短会话事务预留问答和附属记录，事务提交后才await外部模型。相同UUID复用原问答和引用；换问题、章节或跨旧resource模式冲突409，其他用户404。

Agnes适配文件、请求参数、模型/Key管理、输出限制和超时未修改。无检索命中时context=None调用原通用方式，由后端给回答固定加说明，并保持30000字符上限及代码围栏完整性检查。

## 3. 数据模型与007迁移

仅新增ai_course_contexts：qa_record_id主键并外键关联ai_qa_records.id；course_title、references JSON、context_hash、retrieval_version、created_at。JSON引用最多3条；使用InnoDB及utf8mb4_unicode_ci。没有修改任何已有表。

原因：直接在ai_qa_records.mode加入course会违反原CHECK；只返回即时引用不能可靠重放历史，章节内容更新后也会混淆依据。内部继续mode=resource、resource_id=course_id，附属表冻结实际参考章节及上下文摘要，不保存Key或完整章节资料。通用记录不创建附属行，旧资源片段无附属行仍按原方式展示。

007迁移已通过tools/apply_course_ai_migration.py执行和核验。工具确认原表结构、课程章节和受保护数据摘要未变；可重复运行做核验，不自动改已有表。MySQL DDL隐式提交，回退应用可保留新表，不自动删除数据。

## 4. 检索与引用真实性

course_id对应resources.id，资源类型为document也可拥有章节。读取课程名称、简介、分类、标签及course_chapters的标题、目标、知识点、Markdown、代码、练习。

关键词使用英文标识符与中文双字片段、停用词过滤，按标题0.30/知识点0.25/目标0.15/正文0.20/代码0.05/练习0.05的命中比例评分；命中后当前章加0.05；分数降序、position/id升序，最多3章。context上限6000字符，每章最多1700，正文以完整段落或完整代码块选取，不执行代码、外链或视频。遇到凭据样式拒绝外发。

references来自实际加入context的章节，包含course_name、chapter_name、chapter_id、position。内部fragment_hash只存附属记录，不返回前端。任何模型自行声称的章节都不能变成引用按钮。历史使用原引用，不按当前资料重新检索；课程不可见或许可撤销时隐藏原问题、回答、课程名和引用。

无命中或无章节：references=[]，回答固定以“当前课程资料中未找到相关内容，以下回答基于通用知识。”开头。禁止为补齐数量构造不存在的章。前端标注“本次提供给模型的课程资料”，不把引用列表等同逐句事实验证。

## 5. 新增接口

- POST /api/resources/{course_id}/ai/questions：request_uuid、question（1–2000字符）、可选chapter_id、既有consent_version。
- GET /api/resources/{course_id}/ai/questions/{request_uuid}：本人本课程记录，pending返回202。
- GET /api/resources/{course_id}/ai/history：本人本课程近30天，page及page_size（最多50），拒绝多余参数。

返回复用原Record并增加course_id、course_title、references、retrieval_version。旧history仅对课程附属记录显示课程增强来源说明，不改变旧记录返回契约。只有active登录用户可用，不提供user_id输入或管理员查看他人问答能力。

## 6. 安全与上线条件

课程必须已发布、非隐藏联调资源406，并在已有AI_ALLOWED_RESOURCE_IDS批准名单中。管理员可管理草稿不代表可以将草稿外发。课程问答与通用问答共享额度、并发及失败记录；不降低已有授权、幂等、凭据过滤或供应商校验。API Key、JWT、密码不写入文档/日志/浏览器。

现有白名单默认空，本轮初次运行核验也是空；实现不能绕过此策略。待明确批准的编号按原环境变量机制配置。未批准时面板说明“当前课程不可用或尚未批准资料外发，可切换通用AI继续提问”；通用问答不被课程历史的404影响。

部署：007先迁移，再重载后端；当前8000后端已重载并确认三个路径注册，匿名历史401。前端Vite刷新即可加载，生产部署使用构建产物。批准名单在启动后端的同一终端设定，模型/Key沿用既有配置；不要把Key放VITE变量。

## 7. 文件职责

backend新增models/ai_course.py、schemas/course_ai.py、services/course_ai_retrieval.py、services/course_ai_records.py、api/course_ai.py、tools/apply_course_ai_migration.py；小范围修改models/__init__.py、main.py、原api/services ai_assistant.py。新增tests/test_course_ai.py；基础路由清单测试更新，管理员列表测试允许新增真实课程但仍核验原五门正式课程。

frontend新增types/course-assistant.ts、api/course-assistant.ts、services/course-assistant.ts、components/CourseAiAssistant.vue；CourseLearningView只添加组件与引用选章衔接；新增服务与实际组件测试，旧学习组件测试补齐Element Plus测试替身。原AiAssistantView.vue未修改，原学习操作函数未改。

数据库新增007迁移；README和database/README补充部署说明。Spark、推荐、用户画像、Agnes及现有课程内容均无代码/数据修改。

## 8. 后续扩展与限制

V1单轮、关键词检索，不保证理解所有同义词；context为选取片段而非全课程记忆。references是真实提供资料的来源，并不证明模型没有事实错误。模型调用成功与回答教学质量仍需真实模型、登录浏览器验收。

未来可替换检索器为Embedding，但保留权限、预算、服务端引用和幂等契约。智能自动选择课程/通用模式只预留扩展边界，本轮未实现。
