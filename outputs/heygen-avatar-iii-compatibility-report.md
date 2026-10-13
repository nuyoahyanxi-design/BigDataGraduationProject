# HeyGen Avatar版本兼容切换报告

> 历史方案/验收补注（2026-10-13）：下文未生成、未导入、未验收或远程生产限制属于原阶段/方案的真实记录，不能用来判断当前正式教学媒体是否可播放。当前视频及批次状态见[答辩当前状态](../docs/defense-current-state.md)。不将旧方案未完成改写为该方案成功。

日期：2026-10-10。结果：Avatar III标准Studio任务已创建，尚在处理，未交付成片。

旧视频e2bde46b7c7636c026dae12c4d2423d8的get_video返回failed，失败码AVATAR_IV_VIDEO_GENERATION_DURATION_LIMIT_REACHED，原因Avatar IV monthly limit reached。未重新展示旧失败播放器。

实时公共look目录再次确认Kenji Office 1，Look ID 66500d4366974ae5816201d1f07debc9，状态completed，支持avatar_v/avatar_iv/avatar_iii。只将四场景任务中的开场与总结两个avatar_video场景engine.type改为avatar_iii，其他字段保持一致。保持720p、16:9、James Gao中文声音、原文内容、两页课件和字幕；同一教师风格未替换。

一次新建返回视频ID02027edf488df864900b3c7b7f758adb、waiting、mp4；show_video返回processing并打开自动更新播放器。当前方案是公共Kenji Office 1 + Avatar III + 720p Studio，账号已经接受请求，尚未证明完整渲染、下载、时长与播放可用。接口没有avatar_ii枚举，未伪造Avatar II或改用其他角色。未购买、未调整订阅、未增加额外试片。

参数记录：outputs/heygen-standard-test/studio-parameters-avatar-iii.json；任务与上一失败原因：generation-result-avatar-iii.json。原720p及1080p参数文件保留，不覆盖旧记录。

没有新MP4、正式视频绑定或验收通过记录。按播放器说明未再次轮询状态。若该任务终态仍受限制应停止，不自动换Avatar V、其他公共look或再次创建任务；不得将引擎目录支持等同于账号有可用额度。其余方案的真实可用性尚未验证。

本轮只新增设计、参数和报告，未改业务代码、数据库、Spark或正式发布数据，未提交Git。成片成功后的视频验收及绑定是后续完成条件，当前任务创建成功不能替代成片完成。
