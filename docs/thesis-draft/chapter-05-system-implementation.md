# 第五章 系统实现

> 当前口径补注（2026-10-13）：正文中的冻结版本与旧批次是历史依据；当前代码基线为b8474f2，最新Spark源批次为20261013T052412Z_1fc73f17。 当前技术栈、视频播放证据和各数据口径统一见[答辩当前状态说明](../defense-current-state.md)；本次仅修订文档，没有重新验收或运行Spark。

> 初稿基准：v1.0-defense-ready（9dbbb9d911b194108f4e404457677ba013f196fb）。编制日期：2026-10-11。本章依据冻结源码描述实现流程，没有运行业务写入、Spark任务或新增实验。页面截图是2026-10-11采集的实际展示状态，不等于所有环境可无条件复现。

系统实现分为在线业务与离线计算。Vue前端提供操作和展示，FastAPI执行身份、权限和事务，MySQL保存状态及事件；Spark在local[2]本机模式中处理批次，生成画像、推荐和看板产物。以下分别介绍七个模块，截图与问答为论文编辑和答辩准备资料。

## 5.1 用户认证模块实现

### 5.1.1 功能描述

用户认证模块实现账号注册、登录、当前用户信息与兴趣更新，并为学习者和管理员提供服务端权限检查。注册默认创建active学习者，普通注册不能自行获得管理员角色。前端根据已认证用户组织入口，但管理权限仍由后端控制。

用户密码以带随机盐的scrypt哈希保存。登录成功后返回有时效的JWT，用户信息响应不返回密码哈希。令牌是请求认证依据，不是加密保存密码的方式，也不能取代资源和当前账号状态检查。

### 5.1.2 实现流程

用户接口在api/users.py中定义。注册首先查询用户名，创建用户时调用hash_password，提交后处理唯一约束冲突；登录由authenticate查找用户并验证密码，只有密码正确且账号active才能通过。不存在用户时使用DUMMY_HASH完成验证路径，接口统一返回无效凭据，不公开详细账号失败原因。

security.py使用16字节随机盐和scrypt参数n=16384、r=8、p=1计算摘要，校验通过hmac.compare_digest比较。JWT使用HS256，包含sub、role、iat、nbf、exp、iss、aud、jti及type，默认有效期1800秒。签名密钥由环境加载并有长度检查，不写入源码。

受保护请求经过current_user：读取Bearer令牌、验证签名和必需声明、获取用户ID，再查MySQL当前用户与active状态。require_admin在当前用户上进一步检查实际角色，拒绝非管理员。因而令牌存在并不保证账号停用后仍可访问，也不能仅靠前端路由跳转越过管理权限。

前端auth状态保存令牌、用户及到期时间，sessionStorage持久化会话必要信息。恢复过程读取会话并获取当前用户；失效和过期会清空状态或提示登录。路由守卫控制页面导航，接口层负责附带认证信息。该实现是本项目会话机制，不宣称已经验证所有浏览器安全或生产认证场景。

```text
输入凭据 → authenticate校验 → issue_token
        → 前端保存会话 → 后续Bearer请求
        → decode_token → 查询active用户 → 角色/资源检查
```

### 5.1.3 可插入截图位置

在登录流程之后插入“图5-1 用户登录界面”，使用[01-login.png](../../screenshots/01-login.png)；在会话说明后插入“图5-2 学习者首页”，使用[02-home.png](../../screenshots/02-home.png)。只展示空白登录表单或成功身份，不展示密码、JWT和请求头。

### 5.1.4 对应项目文件

- [用户路由与依赖](../../backend/app/api/users.py)
- [用户服务](../../backend/app/services/users.py)
- [安全实现](../../backend/app/core/security.py)
- [认证状态](../../frontend/src/stores/auth.ts)、[路由入口](../../frontend/src/router/index.ts)

### 5.1.5 答辩可能问题

1. **JWT内容是否加密？** 当前使用签名令牌验证完整性，不能把它说成内容加密。
2. **管理员权限是否由前端决定？** 不由前端决定，后端查询用户并检查实际角色。
3. **能通过注册创建管理员吗？** 普通注册固定创建学习者，普通注册没有赋予管理员角色的入口，管理员使用已有演示账号；本文不声称提供管理员修改用户角色的页面。
4. **登录成功是否证明所有接口安全？** 不能，需要分别核验权限、业务校验与安全边界。

## 5.2 课程学习模块实现

### 5.2.1 功能描述

课程模块把资源、章节和教学内容组合为学习流程。学生可以浏览课程、进入章节、查看目标、知识说明、代码和练习，并播放本地视频。章节进度通过手动确认维护，页面展示完成章节数及课程状态，不进行自动能力评价。

正式视频覆盖五门课程二十五个目标章节，路径按course_<资源ID>/chapter_<章节ID>.mp4组织。该数字描述正式视频集合，不代表数据库所有章节只有二十五条。

### 5.2.2 实现流程

课程读取由GET /api/resources/{id}/course调用read_course。服务检查资源可见性，按position读取章节，查询本人chapter_progress与learning_progress，组合标题、播放信息和已完成状态。管理员与学习者的资源读取和视频自动发现使用既有规则，读取发现结果不自动改写ORM字段或绑定。

CourseLearningView.vue加载课程后选择章节，发出chapter_view动作并按回执更新完成状态。页面展示教学内容与学习提示，video_play和chapter_complete使用统一动作路径，提交期间控制重复交互。动作请求和失败重试保持事件语义，不把用户点击次数直接理解为完成次数。

video_catalog按资源/章节命名查找媒体，并检查路径、MP4结构及是否有视频轨道等条件。结构检查用于运行时发现，不等于完整播放验证；backend/tools/accept_course_videos.py承担独立完整验收。二者需要分开说明，不能把文件存在或结构有效称为解码全部通过。

LearningVideo.vue使用HTML video元素与安全媒体地址，preload为metadata。加载元数据后保存实际duration，播放及timeupdate更新当前位置；播放时向父组件发出play事件。ended仅更新播放结束状态并提示阅读后确认完成，不调用完成接口。

时长显示优先使用接口传入duration，没有该值时使用媒体metadata；媒体读取并不把时长写回数据库。新增旁白的独立SRT仍是候选交付产物，当前组件没有自动加载新SRT能力。

用户手动完成时，后端校验章节关系和先前访问状态，更新chapter_progress。完成章节数与总数形成课程状态，全部完成后按规则桥接整课完成。对于已有章节课程，旧资源完成接口检查章节完成数，避免绕过章节流程直接完成整课。

课程AI作为教学扩展保留。api/course_ai.py的提问接口复用execute_question处理身份、课程条件、外发确认及额度，课程资料按关键词检索后随许可范围内的问题交给外部模型；course_ai_records提供本人问答、历史和引用读取。问答记录与ai_course_contexts保存的引用元数据对应，不修改学习进度，也不参与content_v1推荐评分。实现存在不等于专业回答已全部验证，第六章单独列出历史请求和内容质量边界。

### 5.2.3 可插入截图位置

在课程读取说明后插入“图5-3 课程列表”，使用[03-course-list.png](../../screenshots/03-course-list.png)。在播放器与章节内容说明后插入“图5-4 PySpark章节学习界面”，使用[04-learning.png](../../screenshots/04-learning.png)。长截图应选取清晰区域，保留手动完成或时长说明，不改动页面数据。

### 5.2.4 对应项目文件

- [课程接口](../../backend/app/api/courses.py)、[课程服务](../../backend/app/services/courses.py)
- [章节请求模型](../../backend/app/schemas/courses.py)、[课程数据模型](../../backend/app/models/courses.py)
- [学习页面](../../frontend/src/views/CourseLearningView.vue)、[播放器](../../frontend/src/components/LearningVideo.vue)
- [视频发现](../../backend/app/core/video_catalog.py)、[静态服务](../../backend/app/core/media.py)
- [视频验收工具](../../backend/tools/accept_course_videos.py)、[最新视频报告](../../outputs/course-teaching-rhythm-final-replacement-report.md)
- [课程AI接口](../../backend/app/api/course_ai.py)、[问答处理](../../backend/app/api/ai_assistant.py)、[本人记录与引用读取](../../backend/app/services/course_ai_records.py)

### 5.2.5 答辩可能问题

1. **播完视频就完成了吗？** 不会，ended只提示，完成需要手动业务动作。
2. **播放位置是否证明看满？** 不证明，它是部分播放动作的位置记录，没有强制观看认证。
3. **视频自动发现是否改数据库？** 读取时组合播放信息，不自动修改章节绑定。
4. **新增旁白字幕是否已显示？** 独立SRT不由当前播放器自动加载，应明确这一边界。

## 5.3 学习行为采集实现

### 5.3.1 功能描述

学习行为采集把访问、进度和收藏操作转换为可追溯记录。主learning_events支持resource_view、learning_start、learning_complete、favorite_add和favorite_remove；chapter_events保存chapter_view、video_play和chapter_complete等章节动作。两套记录具有不同粒度，不全部混入一个分析事实表。

事件包含用户、资源、类型、时间、来源、版本、有效性和请求指纹等信息。业务状态与事件在服务事务中协调，同UUID重试和新UUID但状态无变化属于不同情形。

### 5.3.2 实现流程

learning.py通过fingerprint对版本、用户、资源与动作类型生成语义摘要，existing_receipt根据UUID查询既有记录。语义一致返回原回执，UUID被其他语义占用时返回冲突；需要新操作时，服务重新组织事务并检查当前用户与资源状态。

_perform根据动作读取进度或收藏状态。首次开始创建in_progress，开始已存在时标记无状态变化；完成要求先开始，已有章节课程还检查章节全部完成。收藏重复添加或不存在时取消同样可以形成is_effective=0回执。状态先在事务中flush，事件插入后commit，异常rollback；锁等待或死锁仅按代码限定次数重试，并要求继续使用相同UUID。

服务使用服务器时间与接收时间协调权威事件时间，保存状态前后和资源版本。资源浏览的client来源不意味着直接信任客户端时间，客户端时间是独立字段，分析仍按实际权威和截止规则处理。

courses.py对章节动作构造包含用户、资源、章节、事件类型和播放位置的语义摘要，检查用户、所属课程、章节和前置访问。chapter_complete只在首次完成时有效，重复确认不累计完成数。课程首次开始和全部章节完成时调用bridge，在同一服务流程中生成主学习事件。

桥接UUID采用UUIDv5与源章节请求及动作类型形成确定性标识，来源为server。其余细粒度章节活动保留在chapter_events；Spark抽取的是五表投影中的learning_events，不会直接计算所有播放事件或完整观看时长。

```text
业务动作 → 身份/状态检查 → UUID与指纹核对
        → 进度或收藏变化 → 插入事件 → 事务提交
章节动作 → chapter_events + chapter_progress
        → 首次开始/整课完成时桥接learning_events
```

### 5.3.3 可插入截图位置

在章节桥接之后插入“图5-5 学习行为与进度提示”，从[04-learning.png](../../screenshots/04-learning.png)截取真实提示区域。此图证明页面展示而非数据库每项约束；可另绘“图5-6 主事件与章节桥接时序”，依据实际函数，不展示含令牌的请求截图。

### 5.3.4 对应项目文件

- [学习接口](../../backend/app/api/learning.py)、[主事件服务](../../backend/app/services/learning.py)
- [课程事件服务](../../backend/app/services/courses.py)
- [核心模型](../../backend/app/models/core.py)、[课程模型](../../backend/app/models/courses.py)
- [核心迁移](../../database/migrations/001_create_core_tables.sql)、[课程迁移](../../database/migrations/005_create_course_learning.sql)

### 5.3.5 答辩可能问题

1. **同UUID重试会重复写吗？** 同语义返回既有回执，冲突拒绝，并有唯一约束与事务处理。
2. **新UUID重复开始是否有效？** 状态已存在时可能记录无变化回执，不等于新增有效学习。
3. **所有章节记录都进入Spark吗？** 不会，只有桥接主事件等五表分析输入进入当前链路。
4. **是否实现分布式exactly-once？** 不能如此扩大，只能说明当前数据库请求和事务规则。

## 5.4 Spark数据处理流程实现

### 5.4.1 功能描述

Spark数据处理把业务分析投影转换为有效行为和可用批次。pipeline编排extract、clean、quality，输出ODS/DWD路径与质量报告。画像、推荐和看板任务在其后分别读取来源，不由页面请求触发全套任务。

当前配置master为local[2]，driver内存1g、Shuffle分区2、单表抽取上限50000行。local[2]是本机两个工作线程，不是两台服务器；抽取上限不是已经验证的吞吐数值。

### 5.4.2 实现流程

build_spark按配置建立Spark会话，批任务结束时释放会话。extract生成新的批次ID，通过mysql_snapshot的JDBC一致性只读连接读取schemas白名单：users、resources、learning_progress、favorites和learning_events。密码哈希、资源全文和全部课程/AI表不在该分析投影中。

ODS写入data/ods/batch_id=<批次>/<表>，加入源库、源表、批次与快照时间。文件采用Parquet，write模式避免直接覆盖既有目录；写后读回核对行数及内容，manifest保存表结构、文件摘要和completed或failed状态。

clean调用clean_events处理主行为。它标准化UUID和时间，关联用户/资源引用，检查事件类型、ID、权威时间、版本、有效性、状态语义和请求指纹。客户端及会话UUID保持相应v4规则，服务器learning_start/learning_complete允许合法v5桥接，不能将所有v5无条件视为有效。

清洗区分字段/语义无效、同UUID回执冲突、一致重复和no_state_change。有效事件进入DWD，拒绝信息保留quality_reason、quality_reasons和quality_class。质量检查满足输入=有效输出+过滤记录，主原因和多原因统计不应直接混合相加；无变化排除也不等同业务库异常或删除。

pipeline只有在extract、clean与quality顺序成功后写入成功的spark-data-pipeline-latest.json；发生异常时不发布新的成功源批次。具体后续任务仍有自己的校验与发布规则，不能把pipeline描写成一个跨所有结果表和文件的全局事务。

```text
JDBC五表一致性分析投影 → ODS Parquet
                   → 清洗/质量检查 → DWD有效事件
                   → 任务内聚合（DWS逻辑职责）
                   → ADS画像/推荐/日指标
                   → 各任务校验与结果发布
```

DWS为任务内逻辑聚合职责，不存在独立物理落盘层；没有独立data/dws目录、物理表或发布任务，聚合在profiles、recommendations和dashboard_metrics等计算中完成。ADS产物使用本地文件，没有HDFS部署；HDFS仅是平台教学课程主题。当前实现的保护和校验规则不能被描述为生产集群性能实验。

### 5.4.3 可插入截图位置

本节不使用页面图替代Spark执行证据。可在分层流程之后插入“图5-7 Spark处理与批次图”，来源为[architecture.md](../architecture.md)与[Draw.io文件](../architecture.drawio)。任务日志图如需插入，必须来自已有授权运行的真实日志并注明日期、源批次和范围。已有计算记录的检查范围见第六章。

### 5.4.4 对应项目文件

- [pipeline任务](../../spark/jobs/pipeline.py)、[extract任务](../../spark/jobs/extract.py)
- [clean任务](../../spark/jobs/clean.py)、[quality任务](../../spark/jobs/quality.py)
- [清洗规则](../../spark/utils/cleaning.py)、[JDBC快照](../../spark/utils/mysql_snapshot.py)、[投影字段](../../spark/utils/schemas.py)
- [Spark会话](../../spark/utils/session.py)、[运行参数](../../spark/configs/pipeline.json)
- [文件与摘要工具](../../spark/utils/files.py)、[正式发布报告](../../outputs/formal-release-result-report.md)

### 5.4.5 答辩可能问题

1. **五张表是否五个任意并行连接？** 当前使用一致性JDBC快照连接组织读取，不是互不协调的抽取。
2. **ODS是否全库备份？** 不是，是字段白名单分析投影。
3. **DWD排除是否删除MySQL记录？** 不会，清洗在分析产物中区分，原始输入仍可追溯。
4. **DWS在哪里？** 在画像、推荐、统计任务的聚合职责中，没有独立落盘。
5. **为何允许UUIDv5？** 服务端确定性课程桥接采用v5，清洗按来源和事件语义限制允许。

## 5.5 用户画像生成实现

### 5.5.1 功能描述

画像汇总用户兴趣、活跃情况和资源学习偏好，覆盖快照中的active learner，并保存证据类别、生成时间与来源截止。画像不是知识测验或能力预测，也不对所有用户自动假定存在历史行为。

### 5.5.2 实现流程

user_profiles任务选择已完成的源ODS/DWD批次，核对manifest与文件摘要，并调用compute_profiles。该函数只处理有效、发生时间不晚于截止且属于快照有效学习者的事件，将UTC事件转换到Asia/Shanghai业务日。

活动画像计算活跃天数和各类有效事件次数。学习偏好按不同已开始资源关联不同完成资源，统计started_resources、completed_resources及完成率；没有开始资源时完成率为None。资源类型偏好使用已开始资源基础分及完成加分，归一化后描述偏好，不代表掌握程度。

兴趣计算中，浏览按用户、资源、业务日去重后权重为1，开始和完成分别为2、3；收藏通过最后有效添加/取消状态取权重2。资源标签去重并排除空标签，单个行为分值除以标签数后分配到各标签，用户标签得分归一化形成行为兴趣。

显式兴趣标签按去重等权归一化。当显式和行为兴趣均存在时，画像采用30%显式与70%行为组合；只有一种时使用已有部分。输出interest_profile、activity_profile及learning_preference，证据标记observed、explicit_only或no_evidence。活动事件次数、日去重兴趣贡献及资源去重进度具有不同口径，不能把三者统一称为浏览量。

结果写入ADS/user_profiles批次，保存解释与校验信息，经任务验证后写MySQL user_profiles并更新画像发布信息。历史以用户和批次身份保留；SQL结果、文件和指针的保证需要按任务流程分别讨论。

前端画像位于推荐页，由后端依据推荐指针的profile_batch_id读取配套记录，并检查截止信息。它不任意拼接另一个最新画像，不在页面访问时计算新画像。该展示使用原始兴趣画像，与推荐函数的显式标签覆盖分支要区别，下一节进一步说明。

### 5.5.3 可插入截图位置

在结果读取之后插入“图5-8 当前用户画像摘要”，使用[05-profile.png](../../screenshots/05-profile.png)。保留兴趣、活动、完成率与统计截止信息，避免只截百分比使其被误解为能力得分。

### 5.5.4 对应项目文件

- [画像计算](../../spark/utils/profiles.py)、[画像任务与发布](../../spark/jobs/user_profiles.py)
- [结果ORM](../../backend/app/models/analytics.py)、[画像迁移](../../database/migrations/002_create_user_profiles.sql)
- [画像配套读取](../../backend/app/services/recommendations.py)、[推荐页面](../../frontend/src/views/RecommendationsView.vue)

### 5.5.5 答辩可能问题

1. **显式和行为兴趣如何组合？** 两者同时存在时画像采用30/70组合，否则使用已有信息。
2. **没有事件就没有画像吗？** 有效学习者仍覆盖，可以显式兴趣或无证据状态表示。
3. **完成率无分母怎么办？** 没有已开始资源时返回空值，不伪造0或100%。
4. **推荐使用完全相同兴趣向量吗？** 不一定，存在显式兴趣时推荐源码会构造等权显式向量。

## 5.6 推荐结果生成实现

### 5.6.1 功能描述

推荐模块实现popular_v1热门基线与content_v1融合推荐，输出资源、算法、排名、分数和解释。默认线上参数top_n为5；独立评价任务使用Top-10，不等于页面应固定显示十条。

算法不包含ALS、深度网络或在线参数训练。60/25/15权重来自冻结源码，是当前工程规则，不是本章证明的最优实验结果。

### 5.6.2 实现流程

recommendations任务读取指定来源的ODS/DWD和配套画像，验证状态、覆盖及摘要。compute_recommendations只接受快照active learner，并检查画像恰好覆盖这些对象。eligible_resources按来源与许可条件排除指定验收专用资源，资源还需published。标签必须可解析，数组元素不能为null或空白字符串；空数组在compute_recommendations中允许存在，其标签相似度为0。

匹配向量先从画像读取；当users中存在非空显式interest_tags时，源码用等权显式标签替代匹配权重，否则保留画像权重。资源标签和用户权重随后按canonical_tag统一主题别名，合并标签权重并重新计算范数。画像30/70组合和此处推荐向量选择不是同一个规则，不能混写。

有效行为只保留不晚于截止且属于有效学习者的事件。热度中浏览按用户/资源/业务日去重，开始与完成按用户/资源去重，收藏使用最后有效状态。当前参数view=1、start=2、complete=3、favorite=2，因此热度为：

$$
H(r)=V(r)+2S(r)+3C(r)+2F(r)
$$

personal_heat使用个人相应行为分值，并按用户内最大个人热度归一化为behavior_score。整体heat按最大资源热度归一化为popularity_score，无热度时为零。候选通过用户与资源组合形成，并用进度和有效完成事件排除已完成资源；候选对数和输出上限超限失败，不静默截断为成功结果。

标签匹配使用权重向量和二值资源标签的余弦相似度，无范数或空标签时为零。has_history来自该用户有效历史事件存在性；有历史时评分为：

$$
Score(u,r)=0.60\,Similarity(u,r)+0.25\,Behavior(u,r)+0.15\,Popularity(r)
$$

无历史时用归一化热度回退，不对所有用户无条件使用融合式。相似度为零也不等于有历史用户停止使用整个融合计算，因为个人行为和热度仍可能提供分数。

popular_v1按原始heat降序、资源ID升序排名。content_v1按综合分数、heat降序及资源ID升序排名；稳定排序避免同分候选任意变化。理由根据热度、兴趣匹配、个人行为或补充回退分支生成。结果以规定精度保存，不把页面百分比说成预测概率。

任务写ADS/recommendations并校验，按批次与算法保存到MySQL recommendation_results，发布指针带source_batch_id、profile_batch_id、as_of_utc和生成时间等信息。后端load_publication有大小、格式与时间检查，随后按发布批次和当前用户读取结果。

线上接口再次过滤当前已下架、不可见和已完成资源，画像按配套批次读取。因此页面可能少于五条，既不会补足到固定数量，也不触发Spark重算。整课完成的在线过滤与下一批次评分更新是不同机制；单章完成不保证推荐排名立即改变。

### 5.6.3 可插入截图位置

在理由和线上过滤之后插入“图5-9 内容推荐结果”，使用[06-recommendation.png](../../screenshots/06-recommendation.png)，保留理由、算法、分数和来源说明。截图支持界面实现，不证明Recall、NDCG或真实学习效果提升。本章不插入未核验的算法提升柱状图。

### 5.6.4 对应项目文件

- [推荐计算](../../spark/utils/recommendations.py)、[推荐参数](../../spark/configs/recommendation.json)
- [推荐任务](../../spark/jobs/recommendations.py)、[结果表迁移](../../database/migrations/003_create_recommendation_results.sql)
- [推荐读取服务](../../backend/app/services/recommendations.py)、[推荐接口](../../backend/app/api/recommendations.py)
- [推荐页面](../../frontend/src/views/RecommendationsView.vue)、[评价实现](../../spark/utils/recommendation_evaluation.py)

### 5.6.5 答辩可能问题

1. **推荐属于哪种模型？** 当前是热门与标签/行为/热度融合评分，不是自训练深度模型。
2. **浏览次数怎么计算热度？** 热度按用户/资源/业务日去重，不直接累计全部浏览请求。
3. **有显式兴趣时为何与画像不同？** 推荐源码优先构造等权显式标签匹配向量，页面画像另有组合规则。
4. **得分百分比是准确率吗？** 不是，排序得分与实验评价指标不同。
5. **线上五条和实验十条矛盾吗？** 配置用途不同，在线过滤还可能减少可见条数。
6. **算法效果提升多少？** 本章只描述实现，没有足够同版本实验依据就不报告提升数值。

## 5.7 数据分析看板实现

### 5.7.1 功能描述

管理员看板展示来源、统计截止、清洗信息、用户活动、资源分类、学习完成情况及配套推荐统计。后端GET /api/dashboard/overview要求require_admin，学习者不能通过直接页面导航取得管理数据。看板是描述统计和来源展示，不是学习效果预测模型。

### 5.7.2 实现流程

dashboard_metrics任务读取ODS、DWD、质量记录和配套信息，调用compute_metrics。函数根据统计截止转换到Asia/Shanghai日期，以该日期为末日构建包含截止日及其前29天的30个自然日序列；事件只保留不晚于具体截止时刻的记录，将有效学习者行为按日期及类型聚合，无事件日期补零。全快照有效事件与三十天窗口事件分别保存，不能互换解释。

用户统计来自用户快照。学习完成情况把active learner的in_progress和completed进度统计为已开始组合，completed占已开始组合得到完成率，分母为零时为空。该比例描述进度记录，不代表掌握程度或真实课程效果。

任务形成daily_metrics Parquet与摘要，读回并保存校验信息，发布dashboard-latest.json。后端load_dashboard限制读取大小，核对内容摘要、数据结构、时间及配套推荐截止。没有文件返回尚无统计状态，格式或摘要不合法时返回不可用，不能伪造空图当作正常完成。

在overview中，后端将资源总量、已发布数量和分类分布替换为当前MySQL可见资源查询，并在source说明当前来源及演示资源排除。该替换是响应对象的读取组合，不更新冻结Spark文件或业务库。其余行为和进度等快照指标仍保留批次范围。

配套画像数量和证据分布按profile_batch_id读取；推荐数量按指定recommendation batch及算法聚合，并按展示规则排除指定隐藏资源。这里的推荐行数、用户数和不同资源数是发布统计，不是线上曝光、点击率或实验Coverage。不能把不同分母名称统一称为“推荐覆盖率”。

DashboardView.vue获取结果，借助dashboard-charts与ECharts展示趋势、分类、完成及推荐统计，并说明更新和来源。刷新按钮重新读取既有文件与当前数据库相关信息，不触发Spark。部分实时资源信息可能变化，不能承诺整个看板永久与旧快照数字完全一致。

### 5.7.3 可插入截图位置

在统计读取和展示之后插入“图5-10 管理员数据分析看板”，使用[07-dashboard.png](../../screenshots/07-dashboard.png)。可分别截取来源区及图表区，保留开发验收样本说明和时间，避免整张长图缩小后无法辨认。

### 5.7.4 对应项目文件

- [统计计算](../../spark/utils/dashboard_metrics.py)、[看板任务](../../spark/jobs/dashboard_metrics.py)
- [看板接口](../../backend/app/api/dashboard.py)、[看板读取服务](../../backend/app/services/dashboard.py)
- [响应模型](../../backend/app/schemas/dashboard.py)、[看板页面](../../frontend/src/views/DashboardView.vue)
- [图表组织](../../frontend/src/services/dashboard-charts.ts)、[真实截图说明](../../screenshots/README.md)

### 5.7.5 答辩可能问题

1. **所有看板数据都是实时的吗？** 不是，行为和进度按批次，部分资源统计读取当前MySQL。
2. **点击刷新是否运行Spark？** 不会，只读取发布信息和当前相关业务数据。
3. **完成率是否教学有效率？** 不是，分母是已开始的进度组合，描述流程状态。
4. **推荐行数是否曝光或Coverage？** 不是，是配套批次数据库结果统计，不能替代实验指标。
5. **图表有数据是否证明效果？** 只能支持显示和读取能力，样本性质与效果评价需另外说明。

---

## 本章小结

本章按七个模块说明了冻结版本的实际实现。认证与权限为业务入口提供控制，课程和事件服务按事务与幂等规则维护状态；Spark在local[2]模式中处理ODS/DWD，聚合逻辑承担DWS职责，ADS保存画像、推荐和统计结果。画像向量、推荐分支及在线过滤按源码分别处理，看板则明确区分快照和当前资源来源。

以上实现描述不新增算法、数据库表或实验结论。第五章证明路径应以源码与指定产物为依据，对应的接口、处理结果、批次、页面和媒体验收证据以及未覆盖项在第六章分别说明，不据实现流程推导算法效果提升或全系统全部通过。

## 图片与证据使用说明

本章截图均来自现有screenshots，图号为论文排版建议，不新增或修改图片。使用源码证据时固定v1.0-defense-ready，历史报告中的旧批次、旧评分或测试数量必须注明范围。除流程图外，不用图示代替真实任务执行记录；不展示凭据、Token或私有配置。图片插入建议与答辩问答属于编辑附注，不视为正文图表已排版完成。
