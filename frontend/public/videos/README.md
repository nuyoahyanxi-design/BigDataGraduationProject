# 章节视频自动识别目录

默认frontend/public/videos，后端/videos只读访问；COURSE_VIDEO_ROOT可配置实际根目录，Vite将/videos代理到API_PROXY_TARGET。

唯一自动命名规则：course_<resource_id>/chapter_<chapter_id至少3位>.mp4。
例：course_1069/chapter_006.mp4 → /videos/course_1069/chapter_006.mp4。
课程ID不补零，章节ID至少补齐三位；ID1001对应chapter_1001.mp4；章节ID不等于章节顺序。每章一个标准文件。未来新增课程/章节遵循同一规则，不维护25章硬编码配置。

学生课程读取时，有效标准MP4优先于数据库原video_url；只替换响应副本，不写库。管理员编辑读取仍显示数据库保存的旧值，以免无意将自动映射写库。文件缺失或检查不通过时保留原URL，阅读与手动完成不受影响；需要刷新课程页才能重新发现文件。

检查范围：大小至少1024字节且至多2GiB、MP4容器ftyp/moov/mdat、视频轨、路径边界。可通过COURSE_VIDEO_MIN_BYTES设置最小字节数（必须正整数）。结构检查不证明可解码、音频正常或教学内容正确，成片仍要浏览器验收。正常AI导出建议H.264/AAC MP4。最终答辩版本的25个已验收MP4已通过.gitignore白名单纳入Git候选；其他本地媒体仍忽略。

导入：
1. 在正式目录之外人工审查成片与权利、真实时长、声音和字幕。
2. 将文件先复制到同目录chapter_006.mp4.part，完成后同目录原子改名为chapter_006.mp4，不直接边上传边写标准名。
3. 在WSL项目根执行（复用已有环境，不安装依赖）：
   source environments/activate-bigdata.sh
   PYTHONPATH=backend python backend/tools/scan_course_videos.py
4. 查看outputs/course-video-scan下每次独立时间戳JSON/Markdown报告，确认目标章节可自动绑定。全量完整退出0；缺失/异常退出2；配置/数据库失败退出1。部分导入时其余缺失是事实，不伪造完整。
5. 用学生账号刷新课程并进入对应章节，URL应为/videos标准地址；检查浏览器视频加载、播放、暂停、拖动及结束提示。结束不自动完成，手动按钮仍产生原章节完成事件。

仅离线目录校验：工具支持--catalog <JSON目录快照>，格式为resources[{id,title,status}]及chapters[{chapter_id,resource_id,title,video_url}]。此方式不连数据库，报告标记offline_catalog；不能替代实时正式绑定检查。--root只控制本次扫描根目录，不自动修改运行服务配置。

版本替换：先安排该章无人播放的窗口，避免同一URL的分段下载跨版本。标准文件名保持固定，先把旧成片备份到服务目录外（带SHA256和时间），将新成片通过.part同目录改名替换；刷新浏览器。文件服务使用ETag/修改时间，代码结构检查缓存随大小/修改时间/变化时间失效。正常情况下不需重启、写库或运行Spark；不要人为保留全部时间戳伪装旧文件。回滚仅恢复旧视频文件，不删除学习事件。

课程目录已有1068/1069/1070/1071/1072。现有数据库的/demo/video.mp4占位地址保持原值；放入有效标准文件后仅学生响应使用自动URL。管理员编辑页原URL不变不代表学生映射失败，绑定验证以扫描报告与学生课程响应为准。

生产dist部署必须配置同源/videos代理。不要把私人媒体或凭据放在公开媒体目录。除25个正式验收MP4外，其他MP4/WebM在Git忽略范围；只有规范MP4参与自动识别，手动WebM URL兼容保持原样。原片备份、候选及生产中间文件位于outputs/work，保留在磁盘但不纳入版本提交。
