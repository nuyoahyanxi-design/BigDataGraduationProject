# AI课程视频接入实施报告

> 历史资料说明（2026-10-13补注）：下文设计、数量、失败与未验收结论属于原记录日期，不代表当前版本；保留原始证据，不将当时未执行的测试改写为通过。 当前技术栈、视频播放证据和各数据口径统一见[答辩当前状态说明](../docs/defense-current-state.md)；本次仅修订文档，没有重新验收或运行Spark。

日期：2026-10-10（Asia/Shanghai）。代码接入完成；真实成片播放尚待视频文件与正式章节绑定授权。
Git HEAD保持19b4739598a86a2307f62b135c7d27de2b78af1e，未提交Git。此前答辩展示优化的6个前端修改仍保留，本轮没有覆盖。

## 1. 修改文件与实现

| 本轮文件 | 内容 |
| --- | --- |
| backend/app/core/media.py（新增） | COURSE_VIDEO_ROOT配置，默认frontend/public/videos；只读MP4/WebM静态服务、目录有效性检查、目录外符号链接与路径保护 |
| backend/app/main.py | 挂载/videos，原有API和学习中间件保留 |
| frontend/vite.config.ts | /videos代理使用原API_PROXY_TARGET，与/api同源访问 |
| frontend/src/components/LearningVideo.vue | 复用HTML5播放器；显示标题、分秒时长，元数据加载后显示实际时长；切换URL清空上一段元数据/播放状态 |
| frontend/src/views/CourseLearningView.vue | 视频标题为空时使用当前章节标题；去掉固定“演示视频尚未提供”，保留结束提示和手动完成规则 |
| frontend/public/videos/README.md | 目录、URL、部署代理、文件替换与正式数据边界说明 |
| frontend/public/videos/course_1068至course_1072/.gitkeep | 建立5个课程目录，无占位MP4 |
| .gitignore | 忽略videos目录中的MP4/WebM，真实文件不进入Git |
| backend/tests/test_video_assets.py（新增） | 不连接MySQL的隔离静态服务测试 |
| frontend/tests/courses.test.ts | 分层路径、标题、时长及播放器回退检查 |
| frontend/tests/course-flow-components.test.ts | 原章节浏览、手动完成、切换章节事件与进度回归；导航交互使用测试适配器，真实目录展示由既有测试覆盖 |
| frontend/tests/video-player-components.test.ts（新增） | 实际播放器组件事件处理、元数据、结束提示、重播和切换复位 |
| docs/ai-course-video-access-design.md | 最新实施授权补充，默认目录依用户指令调整 |

没有增加学习状态系统；没有修改ChapterAction、chapter_events结构、UUIDv4请求/UUIDv5桥接、章节完成按钮业务处理或推荐算法。数据结构变化为零。

本轮仅本地目录和代码，不生成AI视频、不添加真实成片、不上传媒体、不修改正式章节video_url。

## 2. 测试结果

### 隔离运行测试

- 后端：7项通过。独立FastAPI测试实例挂载临时媒体目录，不启动正式应用数据库生命周期。临时.mp4名称文件只有“HTTP byte fixture, not a generated video”字节，是不可播放HTTP夹具，不是生成视频，未放入项目视频目录。
- 读取200、video/mp4 MIME、HEAD、Range 206与内容范围、不存在文件404、说明文件不可访问、路径与目录外符号链接保护、非法配置拒绝均通过。
- 前端：21个文件、164项测试全部通过，包含原推荐/画像接口展示、看板、登录、资源、课程等离线套件。真实数据库集成测试显式排除，未创建正式测试账号。
- 播放组件：视频标题与4:05时长可显示；ended只显示提示且不发play/完成事件；正常play传递原播放位置；切换视频重置时间、结束与元数据。
- 课程页面：chapter_view→用户点击chapter_complete→章节进度20%；切换第二章只新增chapter_view，进度不被自动完成。UUID继续生成，原API路径与字段不变。此为隔离组件和HTTP适配器验证，不宣称已在正式数据库写入视频事件。
- npm run build、vue-tsc类型检查通过；最终测试适配器修改后再次typecheck通过。构建有既有chunk体积提示，未为此重构。
- 新测试最初缺SSR上下文、随后目录交互适配不足导致失败，均只修改测试夹具修复，最终全套通过。初次日志保留，frontend-tests.log为最终结果。

### 当前服务与正式数据检查

- 有序停止原后端进程并用已有启动脚本重启；后端启动数据库SELECT 1通过，前端Vite配置自动重启，服务保持运行。
- 实际后端OpenAPI 200；后端与前端代理访问尚未放文件的/videos/course_1069/chapter_006.mp4均404，符合实际，不返回HTML冒充媒体。
- 原管理员会话恢复、/api/users/me与/dashboard/overview均200。浏览器正式看板仍显示源批次20261010T060537Z_fb2d2acb及配套画像/推荐；见dashboard-regression.txt。
- 四个latest SHA256与上阶段完全一致，未重跑Spark、切换指针或重新发布。
- 12张表结构与发布前结构一致（忽略自增计数器）；数量与本轮前相同：learning_events91、chapter_events67、chapter_progress17、learning_progress11、resources13、course_chapters26、users6、favorites3、user_profiles34、recommendation_results436、ai_qa_records50、ai_course_contexts25。
- backend/app/services/courses.py、backend/app/models和Spark无新增修改。没有正式数据库写入操作；只读数量/结构检查不等于本轮全历史记录摘要审计。

### 未验证内容

真实媒体解码、声音、实际播放/拖动/结束、正式数据库video_play落库、实际成片时长和跨浏览器播放尚未验证：本轮禁止生成视频，且正式25章仍绑定不存在的/demo/video.mp4。不能称正式课程已经有真实视频，也不能把HTTP字节夹具200当作视频播放成功。接口实现与组件交互已完成，真正媒体闭环须后续提供合法成片并授权绑定。

## 3. 演示流程

当前可演示：正式登录→课程详情→章节目录、正文、视频标题/时长区域和缺文件回退→手动完成章节→画像与推荐/管理员看板。注意本轮未在正式账号执行学习写入。

真实视频准备并获准绑定后：
1. 学生从资源详情进入课程（详情资源浏览与首次章节学习仍按现有事件记录）。
2. 选择已绑定视频章节，查看课程、章节、视频标题及实际时长。
3. 点击播放，原video_play事件记录当前播放位置；可暂停、继续和切换章节。
4. 播放结束仅显示“请阅读章节内容后确认完成本章节”。
5. 用户点击完成本章节，提交原chapter_complete；全部章节完成才按原桥接生成learning_complete。
6. 展示章节进度和离线画像边界；不能称本次观看已即时进入冻结ADS，Spark仍按后续另获授权的批次处理。

本地访问为同源/videos，不依赖第三方视频网站。媒体服务为公开本地教学文件读取，不提供私有媒体鉴权；不要放个人或机密资料。

## 4. 后续视频文件替换方法

默认根：D:\BigDataGraduationProject\frontend\public\videos\。
例如课程1069章6：course_1069/chapter_006-v1.mp4，对应URL /videos/course_1069/chapter_006-v1.mp4。
当前已有5个course目录；章ID不是排序。1069实际章ID6–10，1068为1–5，1072为11–15，1071为54–58，1070为59–63。不要按排序重建章节。

步骤：
1. 用户提供自行制作或有权使用的真实MP4/WebM，人工检查教学内容、字幕、声音、时长及权限；本轮未生成。
2. 文件放入对应课程目录，建议采用版本名，不覆盖旧成片。
3. 验证后端8000及前端5173的/videos完整路径200、Range206和浏览器真实解码可播放。
4. 另行授权后使用已有章节管理更新该章节video_url；保留标题、正文、目标、练习、顺序及已有进度。当前编辑页可维护video_url；video_name/时长继续使用已有字段，实际时长为空时播放器从metadata读取，不要求先写库。
5. 新文件替换采用-v2.mp4并在获得授权后更新绑定；不用重跑Spark。不要修改旧正式批次或清空学习历史。视频仍需手动确认章节完成。

自定义根：启动后端前设置COURSE_VIDEO_ROOT。WSL用/mnt/d/...或Linux绝对路径；Windows原生用D:\...。目录必须存在，配置无效启动明确失败。修改根后重启后端。Vite /videos代理随API_PROXY_TARGET走；正式dist部署需配置同源反向代理，不能以vite build代替后端映射。示例目录中MP4/WebM已被Git忽略，但发布给浏览器的媒体仍是公开可读。

正式数据库保持原占位绑定，这是本次禁止写库的明确边界；代码无法在不改绑定或添加共享占位别名的前提下自动把25章变成独立视频，本轮没有绕过该约束。

## 5. 证据、回滚与阶段结束

证据目录：D:\BigDataGraduationProject\outputs\ai-course-video-implementation\。
包含backend-media-tests.log、frontend-tests.log、build.log、typecheck-final.log、runtime-http.json、database-check.json、pointer-checks.json、dashboard-regression.txt；SHA256清单见evidence-sha256.json。

回滚仅本轮文件：恢复原main.py、vite.config.ts、LearningVideo.vue、CourseLearningView.vue及原相关课程测试；移除本轮新增media模块/测试及.gitkeep目录记录，恢复README与.gitignore新增块。保留此前答辩展示优化的修改，不执行全工作区reset。新增代码未提交，因此回滚前核对本轮清单及后续编辑，避免覆盖其他修改；恢复后重启后端/前端。数据库与发布指针无需回滚。

本阶段代码接入及隔离验收完成。真实视频文件替换、正式章节绑定、真实播放验收等待后续授权，不自动推进。
