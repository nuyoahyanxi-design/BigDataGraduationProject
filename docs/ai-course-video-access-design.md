# AI课程视频接入实施方案

> 历史资料说明（2026-10-13补注）：下文设计、数量、失败与未验收结论属于原记录日期，不代表当前版本；保留原始证据，不将当时未执行的测试改写为通过。 当前技术栈、视频播放证据和各数据口径统一见[答辩当前状态说明](defense-current-state.md)；本次仅修订文档，没有重新验收或运行Spark。

日期：2026-10-10。状态：分析与方案已完成，等待用户确认后实施。
本轮只读源码与MySQL，新增设计、验收报告和只读证据。未改业务代码、数据库、Spark、推荐、正式批次；未生成视频、调用生成服务或安装依赖。

## 实施授权补充（2026-10-10）

用户已授权代码接入，最新指令指定frontend/public/videos作为默认目录，覆盖上文建议的backend/resources/videos默认目录。使用COURSE_VIDEO_ROOT支持后续自定义，后端/videos静态服务与Vite/videos代理共用资源。建立course_1068至course_1072目录与说明，不创建占位MP4，不添加/demo兼容路由或修改原正式章节绑定。复用播放事件和手动完成规则，补充视频时长显示并去除固定缺视频文案。

本轮实施仅源码、目录、文档及离线测试；后端媒体测试使用临时HTTP字节夹具，不是可播放视频，不连接正式数据库。正式数据库、Spark、正式指针和Git提交均禁止。真实解码播放须有用户提供合法成片后再验收；本轮不能宣称成片播放通过。

## 1. 当前系统分析

### 课程—章节—视频关系

已有 `resources(id) → course_chapters(resource_id,id) → video_url`。没有独立courses或videos表；课程复用resources，章节有独立ID。一章最多一个视频字段，不需要新建课程表、视频表或任务表。

本轮MySQL只读证据：outputs/ai-course-video-access/current-structure.json。
5门已发布教学课程资源为1068 Spark RDD基础教程、1069 PySpark数据处理实践、1070 Hadoop HDFS入门、1071 MySQL数据库基础、1072 Python机器学习基础，每门5章。其resource_type实际为document，但已有章节、课程读取和管理流程均支持它们；不为接视频修改类型。隐藏课程2253只有章430，正文目标尚未充分准备，不纳入本轮制作清单。

| 表/字段 | 当前用途与接入方式 |
| --- | --- |
| resources.id/title/status/version_no | 课程资源身份、名称、可见性和版本；保持已有值和正式数据 |
| course_chapters.id/resource_id/title/position | 章节归属、标题及顺序；复用现有25章ID，不增删重排 |
| video_url | 浏览器访问相对URL，存/videos/1069/6-v1.mp4等，不存Windows磁盘绝对路径 |
| video_name | 视频标题，播放器已有显示；可使用现有教学视频名称 |
| video_cover | 可选本地/images/封面URL，已有校验；首版可保持空 |
| video_duration_seconds | 成片实测秒数，可空；规划时长不能先当实际值写库 |
| video_position | 现有视频位置字段；首版每章一视频，无需改变 |
| chapter_progress.user_id/chapter_id/first_started_at/completed_at | 章节首次进入与手动完成时间；无累计观看时长或可信观看比例 |
| learning_progress.user_id/resource_id/status/first_started_at/completed_at/updated_at | 资源级开始/完成桥接状态，供既有统计使用 |
| chapter_events.event_uuid/event_type/resource_id/chapter_id/user_id/occurred_at/playback_seconds/is_effective/request_fingerprint/result | UUIDv4客户端章节动作、服务端发生时间、播放位置和幂等回执 |
| learning_events.event_uuid/event_type/event_source/session_id/occurred_at/received_at/is_effective/state_before/state_after | 资源级原有学习事件，Spark现有输入；桥接的学习开始/完成使用UUIDv5 |

现有接口：GET /api/resources/{id}/course返回章节及视频字段；POST /api/resources/{id}/chapters/{chapter_id}/events接收chapter_view、video_play、chapter_complete。事件schema禁止自行增加video_end等类型。管理员PUT章节接口已允许维护视频字段；已有学习记录时可修订内容，但不能增删或重排目录。

### 当前能力和缺口

已支持播放器controls、播放、标题、章节信息、播放位置、结束提示、失败提示、手动章节完成、失败重试及事件UUID幂等。尚缺真实文件、后端可配置媒体目录、/videos静态映射、前端媒体代理，以及管理员视频名称/时长/封面可见编辑字段（类型和payload已有这些字段，编辑页目前主要露出video_url）。没有视频上传、AI视频生成任务或成品自动发布功能，不能把已有AI问答当成视频生成能力。

25章目前全部video_url=/demo/video.mp4；名称已有，封面和实际时长为空。frontend/public只有videos/README.md，没有MP4/WebM。后端未发现StaticFiles挂载；Vite目前仅代理/api。

## 2. 数据结构变化

**零数据库结构变化、零事件schema变化、零Spark输入结构变化。** 不新增表、字段、事件类型，也不引入视频观看时长推荐权重。

未来独立章节视频绑定属于更新已有course_chapters媒体字段，不是迁移；本轮明确未授权正式数据库写入。实际实施可先在隔离配置与测试库验收，正式绑定必须单独获得授权。保存章节按现有服务会提升resources.version_no，应完整备份原媒体字段及资源版本，在事务中核验其他教学内容/顺序未变。不能直接复制本方案中的INSERT/UPDATE到正式库，本方案不提供可误执行的正式写库脚本。

## 3. 本地资源存储与访问方案

推荐最终目录（计划，本轮未创建）：

```text
backend/
  resources/
    videos/
      1068/
        1-v1.mp4
        2-v1.mp4
      1069/
        6-v1.mp4
        7-v1.mp4
      ...
work/ai-course-video/                 # 脚本、素材、候选文件，不对外服务
outputs/ai-course-video/              # 制作清单、验收证据、SHA256
frontend/public/images/course-video/ # 可选封面，沿用/images URL
```

course_id在这里指现有resource_id，文件名使用实际chapter_id。示例 `/videos/1069/6-v1.mp4`，不是章节排序1。成片采用版本文件名，不覆盖已审核旧文件；候选和私密资料不放服务目录。目录应被Git忽略，防止大文件及无关素材提交。

新增进程配置（建议，尚不存在）：`COURSE_VIDEO_ROOT`，缺省为项目backend/resources/videos；允许部署时指定其他本地绝对目录。Windows部署可指定D:\BigDataGraduationProject\backend\resources\videos；当前服务运行在WSL，必须配置/mnt/d/BigDataGraduationProject/backend/resources/videos，不能直接传Windows路径。配置只影响文件系统根，公开URL固定为/videos，不需要改数据库或前端API类型。

后端计划用现有FastAPI/Starlette静态服务将该目录只读挂载/videos；不引入第三方网站或供应商URL。启动时核验目录存在且为预期目录，错误配置要明确失败或关闭媒体能力，不能偷偷回退到项目根。仅放审核后的MP4/WebM，不启用上传、执行或目录列表；限制路径穿越及逃逸的符号链接。不要把auth/config/log放入媒体根。首版本地演示媒体可由知道URL的人读取，这不替代付费资源权限；若要求媒体鉴权，应另行设计带Range支持的鉴权服务，本阶段不扩大范围。

开发链路：浏览器5173 `/videos/...` → Vite媒体代理 → 后端8000 `/videos/...` → COURSE_VIDEO_ROOT文件。Vite新增/videos代理，复用现有API_PROXY_TARGET；API路径不变。部署时由同源反向代理分别转发/api、/videos，前端dist静态服务仍需配置媒体代理，不能假定vite build自动提供后端映射。

### 与现有占位地址兼容

先验收正式/videos结构，再决定是否暂保留/demo/video.mp4兼容。可选最小演示：将该精确地址只读映射到明确配置的一段审核视频并增加/demo精确代理，复用原25章URL，零正式数据库写入；共享演示片必须标注为通用播放器演示，不能冒充25个章节各自课程视频。更小的既有方案是人工放置frontend/public/demo/video.mp4，但该方式不满足后端可配置根和按章节独立管理，故仅作为临时演示备选。

正式课程目标采用每章独立/videos/{resource_id}/{chapter_id}-vN.mp4，需要后续授权绑定元数据。旧占位保留兼容，不删除旧批次，不重跑Spark。

## 4. 前端播放与学习行为方案

复用LearningVideo.vue和CourseLearningView.vue，不创建第二套播放器。现有video_name用于标题，course.title、selected.position/title用于课程及章节信息；video_duration_seconds仅展示实测时长。

保留点击播放、暂停、拖动、timeupdate、ended与error处理。成功加载后应显示可播放状态；结束后继续提示「视频播放完成，请阅读章节内容后确认完成本章节」。移除CourseLearningView里固定写死的「演示视频尚未提供」字样，保留手动确认及观看时长不可验证说明，文件失败时由现有播放器提示。

**播放结束不自动标记章节完成，不以拖到末尾或浏览器ended证明看完。** 这是对现有完成规则的保持。若要求ended立即产生完成章节事件，就会改变规则，应另行授权；不纳入最小兼容方案。

| 操作 | 原有事件/状态 | 是否进入现有Spark分析 |
| --- | --- | --- |
| 进入资源详情 | resource_view写learning_events，session_id及event_uuid为UUIDv4 | 后续授权的正常批次可抽取，本轮不重算 |
| 打开或切换章节 | chapter_view写chapter_events，创建章节首次开始记录 | 不直接抽取chapter_events |
| 第一次进入该课程且资源级进度不存在 | 服务端learning_start桥接，UUIDv5，写learning_events | 由原有清洗兼容规则支持 |
| 点击视频播放/恢复播放 | video_play写chapter_events，记录当次播放位置 | 不直接参与Spark热度，不把播放位置当时长 |
| 播放结束 | 本地ended状态与提示，无新事件类型 | 不新增Spark指标 |
| 阅读后点击完成本章节 | chapter_complete写chapter_events，更新chapter_progress.completed_at | 章节级不直接进入Spark |
| 全部章节完成 | learning_complete桥接，UUIDv5，更新learning_progress | 后续正常批次进入既有ODS/DWD/ADS |

注意：开始学习时间目前是首次打开章节，不是第一次点击播放；保持这一业务口径。已开始/已完成课程不会因重播重复桥接开始/完成。详情页正常路径负责资源浏览；直接打开/learn链接目前只生成章节浏览，不应为凑三种事件伪造resource_view。验收明确通过详情进入学习，未来若必须深链也产生资源浏览，应作为独立行为变更审查。

Spark TABLE_COLUMNS只抽取users、resources、learning_progress、favorites、learning_events，不包含chapter_events。本方案不能声称每个播放动作都会出现在ODS/DWD，目标闭环是细粒度在线章节记录+资源级既有离线桥接，保持正式批次不变。

可选完成按钮文案保持原样；不得以视频播放失败禁止阅读完成。原UUID失败重试继续使用同一UUID；播放结束不补发新UUID的video_play、chapter_complete。

## 5. 拟修改文件列表（方案，尚未实施）

| 文件 | 最小修改目的 |
| --- | --- |
| backend/app/core/media_config.py（拟新增） | COURSE_VIDEO_ROOT读取、规范化与检查，不混入数据库配置 |
| backend/app/main.py | 注册/videos只读静态服务，必要时精确兼容/demo/video.mp4 |
| frontend/vite.config.ts | /videos及可选精确/demo代理；保持/api目标不变 |
| frontend/src/views/CourseLearningView.vue | 去掉固定缺视频文案，保留完成规则 |
| frontend/src/views/AdminChapterEditView.vue | 暴露既有video_name、实测时长和可选封面输入，无新API |
| frontend/src/components/LearningVideo.vue（按验收需要） | 文件加载状态/视频标题回退，复用原play和ended处理，不改变事件类型 |
| backend/tests/test_video_assets.py（拟新增） | 临时媒体目录、路径边界、404、MIME及Range读取，不连正式库 |
| frontend/tests/courses.test.ts、相关课程组件测试 | 原播放/结束提示与手动完成保护、媒体表单回归 |
| .gitignore、frontend/public/videos/README.md、部署说明 | 忽略媒体大文件，修正文档中的旧占位路径并说明代理配置 |

不修改backend/app/services/courses.py桥接语义、数据库model/schema、Spark源码、推荐代码。媒体路径已被前后端校验支持，/videos分层目录和-v1版本命名无需改校验。

## 6. AI视频制作清单

本轮只有制作规划，没有调用生成模型。优先1069章6/7的1至2个真实成片验证，再扩展全部25章。复用实际标题、目标和正文，禁止为视频重排课程。下表时长是制作目标，非已生成时长；学习目标来自当前章节资料摘要。

制作方式：AI辅助讲解稿和配音，配合人工核对的代码、架构图及录屏，合成为本地教学视频。原生技术文本用课件/代码录屏，避免生成画面文字错误。成片明确AI辅助制作及来源；没有平台自动生成任务能力时只能称AI辅助制作后人工接入，不能宣称平台一键生成。后续选择真实生成服务需另外确认服务、授权、费用及课程资料外发范围；本轮不指定未经验证的供应商，不外发学习数据。

建议输出MP4、H.264视频与AAC音频、1080p、16:9、前置moov以便开始播放；这是制作目标，需实际文件和浏览器验收。每段结构：目标→概念→例子/代码→总结与练习。人工审查技术准确性、代码可读性、声音与字幕、版权，记录SHA256、实测时长和章节绑定清单。


### Spark RDD基础教程（resource_id=1068）

| 章节ID | 视频标题 | 目标时长 | 教学目标 | 本地文件 |
| --- | --- | --- | --- | --- |
| 1 | 什么是RDD？教学视频 | 3分钟 | 说明RDD的分区、不可变和血缘三个特征；区分转换操作与行动操作；解释RDD与DataFrame各自适用的场景 | 1068/1-v1.mp4 |
| 2 | RDD创建方式教学视频 | 3分钟 | 使用parallelize构造教学RDD；理解从外部文件创建RDD的方式；避免把大规模数据先集中到Driver | 1068/2-v1.mp4 |
| 3 | Transformation转换算子教学视频 | 5分钟 | 区分map、filter和flatMap；组合转换构建处理链；认识依赖关系与Shuffle的联系 | 1068/3-v1.mp4 |
| 4 | Action操作教学视频 | 4分钟 | 用count、take与reduce取得结果；理解行动触发计算；识别collect对Driver内存的风险 | 1068/4-v1.mp4 |
| 5 | WordCount案例教学视频 | 5分钟 | 完成分词、映射和按键计数；解释reduceByKey的聚合过程；理解WordCount与学习主题统计的联系 | 1068/5-v1.mp4 |

### PySpark数据处理实践（resource_id=1069）

| 章节ID | 视频标题 | 目标时长 | 教学目标 | 本地文件 |
| --- | --- | --- | --- | --- |
| 6 | DataFrame与Schema教学视频 | 4分钟 | 识别DataFrame的列名与Schema；使用显式类型创建小样本；区分结构化数据与无Schema元素集合 | 1069/6-v1.mp4 |
| 7 | 筛选与列转换教学视频 | 5分钟 | 用filter筛选学习记录；用withColumn派生新列；显式处理null值而不覆盖原字段 | 1069/7-v1.mp4 |
| 8 | 聚合与Spark SQL教学视频 | 5分钟 | 通过groupBy计算主题统计；用临时视图执行Spark SQL；对照两种表达方式的结果 | 1069/8-v1.mp4 |
| 9 | Parquet读写教学视频 | 4分钟 | 写入并重新读取Parquet；理解列式格式和Schema保留；在临时目录安全演示数据输出 | 1069/9-v1.mp4 |
| 10 | 学习行为清洗实践教学视频 | 5分钟 | 过滤缺失用户及非法事件类型；按事件UUID去重；将时间字符串转换为分析时间字段 | 1069/10-v1.mp4 |

### Hadoop HDFS入门（resource_id=1070）

| 章节ID | 视频标题 | 目标时长 | 教学目标 | 本地文件 |
| --- | --- | --- | --- | --- |
| 59 | HDFS架构与核心概念教学视频 | 4分钟 | 区分NameNode、DataNode和客户端；解释分布式文件系统与本机目录的区别；理解大文件批量读取的典型场景 | 1070/59-v1.mp4 |
| 60 | HDFS目录与文件操作教学视频 | 4分钟 | 创建自己的练习目录并上传小文件；使用ls与cat核对输入；区分本地源路径和HDFS目标路径 | 1070/60-v1.mp4 |
| 61 | 数据块与副本机制教学视频 | 3分钟 | 理解文件分块与冗余存储；区分副本数量与计算分区数；通过客户端观察文件状态 | 1070/61-v1.mp4 |
| 62 | HDFS读写流程与权限教学视频 | 4分钟 | 说明元数据查询与数据传输的区别；检查练习目录的访问权限；使用自己的身份读取已上传内容 | 1070/62-v1.mp4 |
| 63 | HDFS与Spark数据分析衔接教学视频 | 5分钟 | 在独立练习会话中读取HDFS数据；用DataFrame完成主题聚合；区分教学集群案例与平台本机链路 | 1070/63-v1.mp4 |

### MySQL数据库基础（resource_id=1071）

| 章节ID | 视频标题 | 目标时长 | 教学目标 | 本地文件 |
| --- | --- | --- | --- | --- |
| 54 | MySQL与关系型数据库基础教学视频 | 3分钟 | 识别数据库、数据表、行与列的关系；区分SQL查询与数据修改；理解MySQL在在线学习平台中的作用 | 1071/54-v1.mp4 |
| 55 | 数据表、字段与约束设计教学视频 | 4分钟 | 按含义选择数值和文本类型；理解主键、NOT NULL与唯一性；在独立会话创建练习表 | 1071/55-v1.mp4 |
| 56 | SELECT查询、条件筛选与排序教学视频 | 4分钟 | 组合WHERE、ORDER BY与LIMIT；避免SELECT所有列造成不必要传输；理解分页需要稳定排序 | 1071/56-v1.mp4 |
| 57 | 聚合查询与表连接教学视频 | 5分钟 | 用GROUP BY统计学习事件；理解LEFT JOIN如何保留无行为用户；区分COUNT(*)与COUNT(列) | 1071/57-v1.mp4 |
| 58 | 事务、回滚与索引基础教学视频 | 5分钟 | 用事务将相关状态变化组合处理；区分提交与回滚；认识索引的查询收益与维护成本 | 1071/58-v1.mp4 |

### Python机器学习基础（resource_id=1072）

| 章节ID | 视频标题 | 目标时长 | 教学目标 | 本地文件 |
| --- | --- | --- | --- | --- |
| 11 | 机器学习任务与数据教学视频 | 3分钟 | 区分监督学习的分类与回归；明确特征、标签和预测目标；使用简单基线理解评估 | 1072/11-v1.mp4 |
| 12 | 训练测试划分教学视频 | 4分钟 | 分离训练数据与测试数据；对时间序列采用时间先后划分；避免特征处理中的未来信息泄漏 | 1072/12-v1.mp4 |
| 13 | 特征与预处理教学视频 | 4分钟 | 区分数值特征与类别特征；只在训练集拟合预处理参数；用训练统计量转换测试样本 | 1072/13-v1.mp4 |
| 14 | 模型评价指标教学视频 | 5分钟 | 通过混淆计数计算Precision和Recall；理解准确率在类别不平衡中的局限；区分分类指标与推荐Top-N指标 | 1072/14-v1.mp4 |
| 15 | 完整实验与可复现教学视频 | 5分钟 | 组织可复现的训练与评价流程；保存配置、指标与数据说明；正确报告基线和实验限制 | 1072/15-v1.mp4 |

## 7. 实施顺序、验收与回滚

1. 方案确认后先实现可配置媒体根、静态读取和开发代理；使用隔离候选文件/临时测试库验证，不触碰正式章节或Spark。
2. 准备并人工审核1069章6/7成片。生成视频与正式元数据绑定均需要后续明确授权；本阶段止于方案。
3. 隔离验证：GET媒体为200且Content-Type正确，Range为206并可拖动；不存在文件404，不应收到Vite的HTML页面冒充媒体；非法路径不能访问配置、源码或目录外文件。验证Windows/WSL路径和部署代理。
4. 隔离用户从详情进入章节：resource_view、chapter_view和首次learning_start各自落表；播放记录video_play、UUID重放不重复；结束仅显示提示，不自动完成；手动完成写chapter_complete；全部章节完成才桥接learning_complete。已有进度回放不重置，不重复桥接。
5. 使用已有离线测试/隔离分析检查UUIDv4/v5规则，不运行正式Spark，不切latest。当前方案不要求把video_play新增到ODS。
6. 正式绑定授权后备份course_chapters原媒体字段、resources版本及受保护进度摘要，使用既有编辑事务只改媒体信息。核验章节顺序、正文、ID、学习进度与历史事件不变；新播放属于授权正常学习，不删除历史记录。
7. 验收通过再准许录制。需有真实成片播放及数据库回执证据，不能以静态HTMLvideo标签、模拟tests或生成任务受理代替通过。

回滚：实现代码可按专门提交或逐文件备份恢复；配置恢复旧值。正式媒体采用版本文件，不覆盖旧成片。若正式绑定已另获授权执行，仅按预先核验的原媒体字段及资源版本回滚，不回滚或删除后续真实学习事件。若期间存在其他管理编辑，禁止用整表快照覆盖，必须逐字段核对处理。Spark批次和latest在该阶段始终保持原值，无需数据发布回滚。

## 8. 本轮真实交付与未验证项

已完成：源码结构审查、正式MySQL只读课程/章节/媒体查询、现有本地文件检查、事件桥接与抽取边界分析、25段课程视频规划。未完成且未执行：静态媒体服务开发、播放器更改、视频生成、媒体播放、数据库写入、隔离运行测试、正式绑定、Spark重算、成片录制。

教学资源当前可阅读、手动完成，不等于AI视频已接入。等待用户确认本方案后进入实现阶段。
