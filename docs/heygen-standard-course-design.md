# HeyGen标准课程视频流程设计

只使用create_video_from_studio，不使用Video Agent。四场景：公共教师开场 → 配音课件 → 配音代码及架构 → 同一教师总结。两页1920×1080 PNG已人工排版及视觉检查，素材上传批次已完成。代码是课堂示意，未执行Spark。全部场景统一James Gao中文声音，速度0.9，MP4/16:9/1080p，默认烧录字幕。时长3–5分钟为验收要求，须实测，不以脚本文字数承诺。

首片主题Spark大数据计算框架简介与原chapter_006的DataFrame与Schema不同，先作为独立测试，不修改正式章节，不在未匹配前自动绑定。失败立即停止，不重试生成；交付完整参数。无业务代码/数据库/Spark/Git变化。

参考：https://developers.heygen.com/reference/create-video（2026-10-10核实Studio分支schema），当前模板列表为空。标准Studio能力存在，不推断账号渲染权限。
