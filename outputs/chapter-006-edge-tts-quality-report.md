# 首章课程视频语音质量优化报告

## 结果

第6章Edge-TTS教师旁白和试听视频已生成，自动检查通过。正式视频暂未替换，其余24章未处理。自然度、停顿和发音仍等待人工试听，不能宣布主观质量已通过。

课程：PySpark数据处理实践（1069）。章节：DataFrame与Schema（6，课程第1章）。视频标题：DataFrame与Schema教学视频。

## 实际方案

隔离安装edge-tts 7.2.8到work/edge-tts-runtime，不变更项目依赖。在线查询确认zh-CN-YunxiNeural与zh-CN-XiaoxiaoNeural可用，本次选择中文男声YunxiNeural，初始语速-10%。发送内容只有既有自编24句课程脚本，没有发送账号、数据库或凭据。Edge-TTS是在线服务，并非离线模型；本轮无购买、无付费API。

原讲稿未改：移除显示用换行后逐句生成。通过音频非静音区域裁剪首尾空白，再以FFmpeg atempo保音高匹配原字幕cue长度，保留原句间和课件阅读空白。各句atempo为0.756–0.954，即约5%–24%减速，未加速或截断词句；边界基于振幅阈值而非词级语音识别。原字幕24条起止、视频结构和章节绑定保持一致。为了避免改变字幕时间轴，没有重新生成或烧录字幕。

候选复用原视频流（-c:v copy），只替换AAC旁白音轨。1280×720、16:9、25fps，219.72秒。

## 验证

- 24/24在线语音合成成功；第23、24句曾返回NoAudioReceived，有限重试后成功。此现象是后续批量联网生成需要处理的风险。
- MP3全部成功解码，逐句适配固定cue时长；原脚本24句完整保留。
- 候选MP4完整音视频解码退出0。
- 复用视频流SHA256与原片完全一致，因此画面、课件切换、烧录字幕与分辨率不变。
- 新PCM总时长219.72354秒，与目标时间线差小于一个24kHz采样间隔；该检查证明时长对齐，不证明每个字的主观同步。
- 25正式MP4及四latest共29个文件哈希一致，未覆盖正式文件。没有修改数据库、后端、Spark、推荐系统或目录结构，未提交Git。

## 听感比较与待判定

| 项目 | 旧版 | 新版已验证条件 | 人工确认内容 |
|---|---|---|---|
| 自然度 | Microsoft Huihui Desktop系统语音 | Edge中文神经男声已合成 | 是否更接近教师讲授、是否有拉伸感 |
| 停顿 | 旧语音句内及原句间停顿 | 保留原句间空白，句内使用新声线韵律 | 是否有拖长、突兀或呼吸不足 |
| 语速 | 固定旧语速 | -10%生成后逐句减速匹配时间轴 | 听起来是否过慢或各句不均匀 |
| 发音 | 旧系统语音术语读法 | 原脚本不变，未替换术语文字 | DataFrame、Schema、long、string、PySpark等是否清楚 |

未通过人工试听前不批量替换。如果固定时间轴下听感仍过慢，应先调整合成语速并重新匹配，不能擅自移动字幕或改写讲稿。

## 交付文件

全部位于outputs/chapter-006-edge-tts/：

- chapter_006-edge-tts-preview.mp4：完整新旁白候选，可直接播放。
- teacher-narration-aligned.wav：完整对齐教师旁白。
- old-30s.mp3 / edge-30s.mp3：开头30秒新旧比较。
- cue-00.mp3至cue-23.mp3：原速合成音频；aligned-*.wav为时长适配版。
- unchanged-subtitle.srt：原字幕副本。
- voices.json、verification.json、sha256.txt：声线及验证证据。

候选SHA256：35673cf02fc80b436555075644c2cab7cc59230e12d366178ac3deae0d4eb788

设计文档：docs/chapter-006-edge-tts-design.md。媒体脚本：work/chapter-006-edge-tts.py、work/assemble-chapter-006-edge-tts.py。

## 下一步

请先听新旧30秒及完整候选的代码讲解、场景转换和结尾。确认“教师声线、停顿、语速、发音”可接受后，再替换本章并授权其余24章批量处理。本轮停止于单章试听交付。

技术来源：https://github.com/rany2/edge-tts（语音列表、声音与语速参数的项目说明）；本报告可用性以本轮实际成功任务为准。


## 用户试听确认后单章替换

用户确认“新旁白可以”后，已仅替换正式chapter_006.mp4。备份：outputs/chapter-006-edge-tts/before-edge-replacement-chapter_006.mp4。其余24视频及四latest共28文件SHA256保持一致。静态访问验证：{'verified': True, 'status': 200, 'sha256': '35673cf02fc80b436555075644c2cab7cc59230e12d366178ac3deae0d4eb788'}。其余24章未处理，等待批量授权。替换证据：同目录replacement-result.json。
