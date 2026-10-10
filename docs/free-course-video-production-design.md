# 免费课程视频自动生产设计

本轮授权自动生产25章，先验证PySpark5章，再依同一流程生产其余20章。仅新增work辅助生产工具、outputs素材及frontend/public/videos标准MP4，不改业务代码、数据库、Spark或推荐算法，不提交Git。

环境检查：Windows默认python是WindowsApps占位入口；使用Codex自带Python（已有Pillow）。本机已有Microsoft Huihui Desktop中文离线语音，采用Windows SAPI合成，不访问收费API或HeyGen。该声音是系统合成旁白，非真人克隆或数字教师。未找到FFmpeg，使用独立work/free-video-runtime中的免费imageio-ffmpeg二进制，不修改项目虚拟环境。语音、课件、字幕、视频全本地生成。

完整读取既有25份chapter-plan及口播，按5场景生成1280×720白底深蓝课件图片；代码保留原文、自动换行，大图用箭头节点展示；口播按句生成WAV与准确音频段时长，逐句SRT同步并烧录。合理阅读/思考停顿仅置于场景末，按原预算校准180–300秒，不用空白场景凑时长。声音语速先样片验证，字幕不覆盖代码。

成片H.264/AAC MP4，720p16:9，可将静态课件按10fps编码（教学静态场景无需高帧率）。先outputs暂存→全量解码/画面检查→原子复制正式路径；无旧文件覆盖。调用原accept_course_videos.py，离线目录来自当前MySQL只读快照，与真实课程章节归属一致。离线验收报告明确标识来源，不修改验收门禁。25章完整通过后输出成片、时长、哈希与证据。
