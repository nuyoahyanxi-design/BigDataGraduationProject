# 课程章节与视频学习增量设计

> 2026-10-10稳定化补充：客户端章节请求仍使用UUIDv4；服务端课程级开始/完成桥接沿用确定性UUIDv5。Spark清洗仅兼容server来源的这两类UUIDv5事件，session_id仍严格UUIDv4。实现与验收见learning-behavior-stability-design.md及对应阶段报告。

本阶段新增课程学习闭环，不修改推荐算法、Spark任务、AI模块或原业务表字段。

新增course_chapters：资源外键、标题、position、Markdown文本、知识标签；每章最多一个本地视频，video_name/url/cover/duration/position。新增chapter_progress：用户与章节联合主键、首次学习、完成时间。新增chapter_events：UUID唯一、用户/资源/章节、chapter_view/video_play/chapter_complete、时间、播放位置、有效标记、语义指纹和结果回执JSON。

章节事件独立保存，Spark暂不读取新增细粒度指标；首次章节访问写原learning_start，最后章节完成写原learning_complete，业务状态与两类事件同事务，维持原推荐分析口径。不将新增事件硬塞入旧表CHECK范围。旧直接完成接口仅对拥有章节的课程增加完成条件，无章节资源保持原逻辑。旧已完成记录不降级，课程页分别展示旧课程状态与新章节进度。

新增认证API：GET /api/resources/{id}/course；管理员POST /api/resources/{id}/chapters；POST /api/resources/{id}/chapters/{chapter_id}/events；GET /api/users/me/chapter-events。事件UUID语义校验、重复请求返回保存回执，写入失败整体回滚；用户锁串行防并发最后章节重复完成。用户不能指定其他用户。

Vue新增/resources/:id/learn、章节导航、HTML5视频组件及安全Markdown展示组件。资源详情开始学习只导航，课程页章节访问才启动状态；有章节资源禁用旧直接完成，提供继续学习。无章节资源通过课程页阅读正文与原行为接口完成，保持兼容。

视频/videos/demo.mp4只占位，不生成视频。视频播放记录video_play、显示播放时间和ended结果，不把浏览器事件当作可信观看时长。缺视频不阻塞阅读完成，明示自报完成，不实现强制观看验证。Markdown只支持安全文本节点、标题/列表/代码块，不用v-html，不加载外部媒体。

三个已有专业资源复用并追加5章，共15章，不删除或改资源内容。管理员初始化经正式章节API，幂等检查顺序与内容冲突，不改密码。数据库迁移005只CREATE新表，执行前后记录核心表数量。

测试：旧后端回归、新章节权限/关联/幂等/完成约束/事务回滚/旧数据兼容；前端接口/章节进度/播放器及文本安全测试、类型检查和构建。演示真实视频尚缺，生产后端需使用原安全配置重启加载新路由，不终止当前用户持Key进程。

## 实现后的API与模型细节

course_chapters字段：id、resource_id、title、position、content、knowledge_tags、video_name、video_url、video_cover、video_duration_seconds、video_position、created_at。每章一视频，不建媒体服务器；时长未知用null，不伪造。
chapter_progress字段：user_id、chapter_id、first_started_at、completed_at。只表示手动完成，不表示观看时长。
chapter_events字段：id、event_uuid、user_id、resource_id、chapter_id、event_type、occurred_at、playback_seconds、is_effective、request_fingerprint、result。playback_seconds是播放事件发生时的媒体位置，不是学习时长；位置并不可信，不参与推荐。result保存当次回执，重放不会因后续进度改变回执。

|接口|权限|内容|
|---|---|---|
|GET /api/resources/{id}/course|已登录，学习者仅已发布|章节正文、视频元数据、自己的完成标记及旧课程状态|
|POST /api/resources/{id}/chapters|管理员|新增章；position唯一，章节学习开始后冻结目录，防中途改变完成分母|
|POST /api/resources/{id}/chapters/{chapter_id}/events|已登录，仅已发布|event_uuid(UUID4)、event_type三种之一、可选playback_seconds（仅video_play）|
|GET /api/users/me/chapter-events|已登录|只返回本人，page/page_size，页大小最大100|

章节事件与课程级兼容事件同事务。桥接事件UUID由章节请求UUID与事件类型派生，不重复触发旧事件；用户锁串行，同资源外键约束阻止跨课程章节串用。章节重复完成is_effective=0，保留操作事件。动作必须先chapter_view，课程view首次生成learning_start。资源下架后不可新增章节学习事件。

已有已完成课程添加章节后，课程状态保持completed，但新章节目录从未完成开始；页面分别展示，不能用旧完成推断新章节完成。没有章节的资源在学习页阅读原内容，并沿用原start/complete。详情页不再直接操作课程开始/完成。

Spark仍只读取原五表及原五事件；当前不读取chapter_events，也不计算视频时长或章节完成率。新细粒度表为未来扩展保留。画像、推荐60/25/15、AI助手源码未更改。

## 启动和验证

迁移005已在本机执行，种子已创建15章。保持现有environments、wsl、spark-experiments不变。

1. 在WSL加载原环境：source /mnt/d/BigDataGraduationProject/environments/activate-bigdata.sh。
2. 后端使用原安全启动方式，在backend工作目录并确保PYTHONPATH含backend。AI需使用原outputs/start-ai-real-model-secure.py安全配置，不把Key写文件。本阶段不自动终止旧持Key进程。
3. 前端沿用已有5173开发服务；新部署在frontend使用API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev -- --host 0.0.0.0。
4. 用现有学习者登录，打开/resources/1068，再点击开始学习/进入课程学习。进入/resources/1068/learn，切换章节、阅读、完成。1069/1072也各5章。旧账号已经完成的课程保持完成；验证新课程完成事件请用尚未完成该课程的测试学习者。
5. 当前demo.mp4不存在，视频播放实际验证须自行准备合法媒体。播放器显示缺视频提示，阅读后仍能完成，不宣称已观看视频。
6. 全部章节完成后旧learning_events应出现一次learning_complete，之后按原Spark四段链路重算；细粒度章节事件从新查询接口读取。

自动检查：backend python -m pytest；frontend npm test、npm run typecheck、npm run build。报告记录实际结果与现场服务是否已重启，不把TestClient当作正式浏览器。
