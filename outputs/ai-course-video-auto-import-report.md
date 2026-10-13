# AI课程视频资源自动导入方案

> 历史资料说明（2026-10-13补注）：下文设计、数量、失败与未验收结论属于原记录日期，不代表当前版本；保留原始证据，不将当时未执行的测试改写为通过。 当前技术栈、视频播放证据和各数据口径统一见[答辩当前状态说明](../docs/defense-current-state.md)；本次仅修订文档，没有重新验收或运行Spark。

日期：2026-10-10。历史阶段状态：当时资源管理能力已实现并验收、正式媒体尚未导入；后续媒体与播放证据见页首统一口径。
Git HEAD保持19b4739598a86a2307f62b135c7d27de2b78af1e，未提交Git。没有数据库迁移、Spark运行、推荐公式修改、正式发布或新事件类型。

## 1. 当前实现分析与推荐方案

原流程：resources课程资源 → course_chapters.video_url → GET /api/resources/{id}/course → LearningVideo读取video_url → 原章节动作接口。
数据库中25章的video_url仍是/demo/video.mp4，且真实文件不存在。现有字段足够支持视频，问题是逐章改库绑定不适合本次“只放文件、不写正式数据”的目标。

采用方案A：规则自动URL + 只读响应映射。
学生GET课程时，按课程ID、章节ID寻找标准文件；文件通过结构检查后，返回副本中的video_url改为/videos/course_<课程ID>/chapter_<章节ID>.mp4，时长返回为空让播放器从真实metadata读取。数据库对象不赋值、不flush、不commit，旧批次及资源版本不变。
管理员读取课程用于编辑时仍返回数据库保存值，避免编辑正文时把只读映射意外写库；管理员编辑页看到/demo占位并不表示学生映射失败。自动绑定验证以学生响应与扫描报告为准。没有新增映射配置文件，未来新增课程遵循同一规则，不改25章硬编码列表。

新流程：章节 → 标准文件结构检查 → 学生响应自动URL → 原播放器 → 原video_play/手动chapter_complete。
缺文件或异常时保留旧URL，章节正文、进度、手动确认仍可使用。需要刷新/重新进入课程获取新响应；不是后台轮询或数据库持久绑定。默认标准文件优先，若想恢复旧手动URL，应先将对应标准文件移出公开目录。

已有video_url为空但标准视频有效的未来章节，现在允许原video_play动作；仅扩展媒体可用性判断，不改变请求字段、UUID、幂等、章节/整课完成状态或事件结构。视频结束仍不自动提交完成。

## 2. 修改文件列表

| 文件 | 本轮内容 |
| --- | --- |
| backend/app/core/video_catalog.py（新增） | 规范路径、MP4结构检查、只读URL发现与章节响应副本 |
| backend/app/core/media.py | 提取统一video_root供服务和扫描复用，原/videos静态行为保留 |
| backend/app/services/courses.py | 学生课程读取自动映射；为空URL的原播放动作允许有效标准文件 |
| backend/tools/scan_course_videos.py（新增） | 只读MySQL/离线目录快照扫描、独立时间戳JSON及Markdown报告 |
| backend/tests/test_video_auto_import.py（新增） | 25章、未来课程、异常文件、映射不写库、原事件及桥接回归 |
| frontend/tests/video-import-ui.ts（新增） | 仅测试入口，调用隔离课程响应与真实LearningVideo；不进入生产入口 |
| frontend/public/videos/README.md | 最终目录、导入、检查、替换和部署说明 |
| docs/ai-course-video-auto-import-design.md | 阶段设计与验证边界 |

outputs/ai-course-video-auto-import/serve-isolated.py仅为本轮隔离测试服务，不属于正式应用。之前阶段未提交的前端展示/视频播放改动保留，本轮未覆盖它们。

## 3. 完整目录规范

根目录：frontend/public/videos/；可用COURSE_VIDEO_ROOT配置其他已存在目录。当前WSL进程需要/mnt/d/...路径，Windows原生使用D:\...。
命名规则：course_<resource_id>/chapter_<chapter_id至少三位>.mp4。课程ID不补零；章节ID不是章节顺序。006是数据库章6；1001不截短，使用chapter_1001.mp4。只接受小写.mp4作为自动识别文件，一个章节一个标准文件。

```text
videos/
  course_1068/ chapter_001.mp4 … chapter_005.mp4
  course_1069/ chapter_006.mp4 … chapter_010.mp4
  course_1070/ chapter_059.mp4 … chapter_063.mp4
  course_1071/ chapter_054.mp4 … chapter_058.mp4
  course_1072/ chapter_011.mp4 … chapter_015.mp4
```

正式目录当前只有README/.gitkeep，没有生成或放入MP4。MP4/WebM已有Git忽略规则，真实成片不提交Git。

| 课程ID | 章节ID | 标题 | 必须放置的相对路径 |
| --- | --- | --- | --- |
| 1068 | 1 | 什么是RDD？ | course_1068/chapter_001.mp4 |
| 1068 | 2 | RDD创建方式 | course_1068/chapter_002.mp4 |
| 1068 | 3 | Transformation转换算子 | course_1068/chapter_003.mp4 |
| 1068 | 4 | Action操作 | course_1068/chapter_004.mp4 |
| 1068 | 5 | WordCount案例 | course_1068/chapter_005.mp4 |
| 1069 | 6 | DataFrame与Schema | course_1069/chapter_006.mp4 |
| 1069 | 7 | 筛选与列转换 | course_1069/chapter_007.mp4 |
| 1069 | 8 | 聚合与Spark SQL | course_1069/chapter_008.mp4 |
| 1069 | 9 | Parquet读写 | course_1069/chapter_009.mp4 |
| 1069 | 10 | 学习行为清洗实践 | course_1069/chapter_010.mp4 |
| 1070 | 59 | HDFS架构与核心概念 | course_1070/chapter_059.mp4 |
| 1070 | 60 | HDFS目录与文件操作 | course_1070/chapter_060.mp4 |
| 1070 | 61 | 数据块与副本机制 | course_1070/chapter_061.mp4 |
| 1070 | 62 | HDFS读写流程与权限 | course_1070/chapter_062.mp4 |
| 1070 | 63 | HDFS与Spark数据分析衔接 | course_1070/chapter_063.mp4 |
| 1071 | 54 | MySQL与关系型数据库基础 | course_1071/chapter_054.mp4 |
| 1071 | 55 | 数据表、字段与约束设计 | course_1071/chapter_055.mp4 |
| 1071 | 56 | SELECT查询、条件筛选与排序 | course_1071/chapter_056.mp4 |
| 1071 | 57 | 聚合查询与表连接 | course_1071/chapter_057.mp4 |
| 1071 | 58 | 事务、回滚与索引基础 | course_1071/chapter_058.mp4 |
| 1072 | 11 | 机器学习任务与数据 | course_1072/chapter_011.mp4 |
| 1072 | 12 | 训练测试划分 | course_1072/chapter_012.mp4 |
| 1072 | 13 | 特征与预处理 | course_1072/chapter_013.mp4 |
| 1072 | 14 | 模型评价指标 | course_1072/chapter_014.mp4 |
| 1072 | 15 | 完整实验与可复现 | course_1072/chapter_015.mp4 |

未来新课程只需已有课程资源及正确归属的章节，使用同一规则；不创建额外表。课程仍需已发布且对学生可见，扫描不会把隐藏/不存在课程当成正常候选。手动WebM仍可由原流程读取，但不参与本次MP4自动规则。

## 4. 扫描能力及当前真实检查报告

扫描使用只读MySQL一致性快照，查询resources和course_chapters，不更新任何表。检查：课程/章节存在与归属、命名、缺文件、文件大小、ftyp/moov/mdat容器、视频轨handler、路径/目录外链接；生成SHA256供文件核对。默认大小1024字节至2GiB，COURSE_VIDEO_MIN_BYTES可设置正整数最小值。读取呈现只检查结构，不在每个请求对整个成片做SHA256；缓存按大小、mtime和ctime失效。

不以扩展名或HTTP200冒称解码通过；MP4结构检查也不能证明音频、字幕、教学内容或全文件解码无误，需浏览器验收。当前环境无ffprobe，未安装新依赖。

正式目录扫描实测：
- 总章节25。
- 可自动绑定0。
- 缺失25。
- 异常0。
- 真实课程视频已导入0。

报告：outputs/ai-course-video-auto-import/scans/scan-20261010T071629636822Z.md及对应JSON。扫描缺失返回程序退出码2，是事实检查而非服务故障，不将空目录报告成全部绑定。

用户提供既有12.mp4的隔离目录另测：可自动识别2份测试副本、其余23章缺失、异常0。两份是同一文件的字节一致副本，仅验证章6/7规则与切换，不是两段AI教学成片，不位于正式媒体根。见real-scans/scan-20261010T072339272766Z.md。

## 5. 使用说明与AI成片导入流程

### 常规扫描命令（WSL项目根）

```bash
source environments/activate-bigdata.sh
PYTHONPATH=backend python backend/tools/scan_course_videos.py
```

每次报告保存outputs/course-video-scan/scan-<独立UTC时间戳>.json及.md，既有报告不覆盖。
退出码：0=全量有效且无异常；2=缺失/异常；1=目录/快照/数据库配置等执行失败。部分导入应查看每章状态，剩余缺失不能算完成。

可选参数：
- --root <目录>：只控制此次扫描，不能改变运行中服务的视频根。
- --output <报告目录>：调整报告输出目录。
- --catalog <JSON目录快照>：离线测试，包含resources[{id,title,status}]、chapters[{chapter_id,resource_id,title,video_url}]；报告明确标记offline_catalog，不能代替实时数据库归属核对。

### 从AI成片到系统播放

1. AI制作完成后先在正式目录外审查内容、代码、字幕、声音、版权和真实时长；不把本次12.mp4测试素材当成25章成片。
2. 根据上表命名，把视频复制到目标课程目录的临时名，例如chapter_006.mp4.part，传输完整后在同一目录原子改名为chapter_006.mp4。不要边写边使用标准名；残留part等异常文件会被扫描报告提示。
3. 执行只读扫描，确认该章structurally_valid、大小与SHA256符合审核记录，课程与章节归属正确。全量25章最终应为25/25、缺失0、异常0；目前尚未达到该内容状态。
4. 学生登录并刷新/重新进入课程，GET响应中的video_url应为/videos/course_1069/chapter_006.mp4。此即虚拟自动绑定，不需要保存管理员表单、修改数据库或重跑Spark。
5. 浏览器验收加载时长、实际播放时间推进、暂停/拖动、章节切换、结束提示。播放结束不能自动完成，手动确认仍使用原章节完成事件。真实正式账号学习会正常写学习记录，必须有对应阶段授权；本轮只在隔离模拟事件环境验证。
6. 推荐/画像仍使用已发布离线快照，不会因放入MP4立即重算。不得重新发布或修改推荐权重。

### 后续替换/回滚视频

替换前安排该章无人播放窗口，避免同一URL的分段读取跨版本。标准URL固定；旧文件先备份到服务目录外并记SHA256，再用新文件.part同目录原子替换，刷新浏览器。通常不需重启或写库；正常文件修改时间/ETag和结构缓存会更新。不要人为保留所有旧时间戳伪装文件未变。回滚只恢复旧成片，不回滚或删除新学习事件。
若要用其他磁盘根，设置COURSE_VIDEO_ROOT并重启后端；正式dist部署保持同源/videos反向代理。只放公开教学媒体，不放凭据和私人资料。

## 6. 测试结果与证据

### 自动测试

- 18项后端测试通过：空25章、全部25章结构夹具、未来课程26章、大小/容器错误、错误课程/章节/归属/补零、目录外链接、替换后缓存失效、学生映射/管理员原值、播放不完成、UUID幂等重放、首次chapter_view产生UUIDv5 learning_start、整课手动完成产生原UUIDv5 learning_complete、无文件且空URL拒绝播放，以及原HTTP媒体200/HEAD/Range206/404保护。
- 测试使用临时MP4容器字节夹具和Session适配器，不连接MySQL，不生成可播放视频。首次读取Session夹具缺迭代接口导致1项失败，仅修正测试夹具，最终18项全部通过。
- 前端21文件、164项原离线测试全部通过，包含章节切换/手动完成、原推荐与画像展示、看板、登录等；真实DB集成测试排除。vue-tsc类型检查通过。无生产前端源码变动，无需为测试入口重新发布。

### 真实文件浏览器验收

用户明确提供F:\Users\Nuyoah\Desktop\12.mp4（9,848,992字节）。复制到outputs/ai-course-video-auto-import/isolated/videos的章6/7，两个副本SHA256均与原文件一致，原文件未改动。
独立8011服务仅监听本机，使用原媒体服务与实际read_course映射函数，但课程/用户目录是内存模拟，完全不连接正式数据库。播放器是现有LearningVideo.vue；测试入口不进入正式构建。

真实核验：
- 规则响应返回章6/7标准URL，而非旧/demo地址，见real-rule-response.json。
- 浏览器成功加载，duration=258.816009秒（显示4:18）。实际播放currentTime从0推进，观察到11.675659秒；自动响应驱动复测推进到42.101381秒，paused=false、readyState=4、error=null。
- 暂停、切换章7后当前时间归零，标准URL切换。
- 为避免宣称全片观看，使用隔离按钮跳到末尾测试ended：当前时间到258.816009、ended=true、error=null；页面显示完成提示，模拟完成次数仍0。
- 手动确认后模拟完成次数从0变1。浏览器播放/完成计数仅为测试模拟；实际后端原act事件逻辑另由18项隔离测试覆盖，未在正式数据库写事件。
- 没有做完整4分钟全片内容、声音质量或教学正确性验收；不把一段测试视频认定为AI课程成品。

截图：real-rule-playback-ended.jpg；页面文本和确认后状态见real-rule-playback-ended.txt、real-rule-playback-confirmed.txt。用户文件复制检查见real-test-file-check.json。

### 正式数据保护

12张表数量、结构和受保护记录摘要前后全部一致；摘要排除users中的password_hash/username/nickname，不回显凭据。course_chapters原25章视频字段、进度和事件均未修改。见database-before.json、database-after.json、database-protection-check.json。
四个latest指针与正式发布记录SHA256一致；Spark任务及数据库model/schema没有本轮修改；Git HEAD不变，未提交或发布。
正式videos目录MP4数量仍0。测试副本与报告均在忽略的outputs下，没有用测试素材污染正式课程。

## 7. 回滚与阶段结束

本轮三处已有文件的回退语义版本保存before/media.py、before/courses.py、before/videos-README.md；README是直接备份，media/courses由本轮精确逆向变更还原。回滚前检查是否存在后续编辑，再逐文件恢复；移除本轮新增video_catalog、扫描工具与测试入口或停止引用。保留前面阶段的播放器、展示文案和未提交修改，不执行全工作区reset。恢复后重启后端，数据库与发布指针不用回滚。

隔离8011服务在验收后停止；正式前后端保持运行。用户原视频保留不动，隔离副本保留为可核对证据，未加入Git。完整证据校验清单见evidence-sha256.json。

结论：自动资源识别、只读绑定和真实播放器功能已通过本阶段验证；正式25章AI视频内容仍为缺失状态。生成成片后按规范放置即可在学生课程刷新时自动识别，不需要写正式数据库。下一阶段若验收正式学习记录，应另获授权，不自动推进。

