# 完整教学章节增强设计

## 目标与边界
在现有课程章节上增加教学内容展示，初始化既有三门课程各5章，不修改users/resources、chapter_progress、chapter_events、推荐算法或Spark任务。只增加章节内容字段，不增加练习提交、评分或自动判定完成的新业务。

## 模型与迁移
复用course_chapters.title、content（Markdown正文）、knowledge_tags、video_url。迁移006仅向course_chapters增加learning_objectives JSON NULL、example_code LONGTEXT NULL、exercises JSON NULL；JSON字段加ARRAY类型CHECK。允许旧章节为空以兼容已有记录；新的写入校验目标/练习列表条数和单项长度。课程查询接口原路径不变，增量返回三个字段。

## 页面
章节标题 → 视频 → 教学目标和知识点 → Markdown讲解 → 独立代码示例 → 章节练习 → 原完成按钮。正文和代码继续以安全文本节点渲染，不执行HTML、不运行用户代码。新增独立ChapterTeachingContent组件，复用LearningMarkdown，缺失新字段显示友好空态，正常完成行为继续原流程。

## 初始化策略
保留既有章节ID、资源ID、排序、标题、完成状态、事件和知识点标签。只对三个指定资源现有的5章更新正文、目标、代码、练习及video_url。内容种子作为新版本文件，原种子保留。操作前校验课程唯一、五章标题/位置一致，并备份章节原内容；同一事务发布15章，重复执行相同内容跳过。初始化工具只授权更新课程章节教学字段，不修改users/resources，不重置进度。

所有视频使用用户指定/demo/video.mp4，仅新增该精确本地地址的安全白名单，继续允许既有/videos/资源；不允许外部URL、脚本或路径穿越。不创建视频文件，播放器加载失败时说明可先阅读正文。

## 验证与运行
先执行迁移及初始化，再执行后端pytest、前端npm test、类型检查和构建，验证课程返回完整内容、空字段回退、安全渲染、视频地址与原章节流程。新代码需安全重启后端才能供浏览器使用，Key仍由现有安全窗口输入，不读取旧进程Key。Spark不重算、不变更。

## 教学依据
原创新教学案例面向Python3.11、Spark3.5.7，代码使用已有PySpark或Python标准库，小数据只为理解概念，不宣称真实模型效果。
- https://spark.apache.org/docs/3.5.7/rdd-programming-guide.html
- https://spark.apache.org/docs/3.5.7/sql-programming-guide.html
- https://spark.apache.org/docs/3.5.7/ml-pipeline.html
