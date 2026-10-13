# 课程学习页面UI优化验收报告

> 历史资料说明（2026-10-13补注）：下文设计、数量、失败与未验收结论属于原记录日期，不代表当前版本；保留原始证据，不将当时未执行的测试改写为通过。 当前技术栈、视频播放证据和各数据口径统一见[答辩当前状态说明](../docs/defense-current-state.md)；本次仅修订文档，没有重新验收或运行Spark。

日期：2026-10-05

## 实际完成
- 目录竖排根因：base.css全局nav为display:flex，章节目录继承后将标题及多按钮挤在一行。本轮在ChapterNavigation组件内明确display:block，按钮满宽、正常文字换行；不截断完整章节标题。
- 课程页桌面260px侧栏与自适应正文，总宽度最大1200px。AppShell仅对course-learning附加宽度类，其他页面保持原宽度。
- 侧栏显示课程名、所有章节、当前章节高亮和已完成标记；桌面可随滚动固定且溢出可滚动。
- 900px及以下自动上下排列，侧栏恢复静态、完整宽度；600px以下进一步收紧间距和文字尺寸。
- 视频16:9、object-fit:contain，保留全部HTML5播放事件。
- 正文最大800px，教学目标与练习分区、知识点标签、Markdown案例理解与常见误区保持既有内容。代码用深色块和内部水平滚动，不执行代码或HTML。
- 完成按钮仍调用原action与原禁用条件，没有改章节选择、播放/完成事件或幂等逻辑。

## 修改文件
frontend/src/views/CourseLearningView.vue
frontend/src/components/ChapterNavigation.vue
frontend/src/components/AppShell.vue
frontend/src/components/LearningVideo.vue
frontend/src/components/ChapterTeachingContent.vue
frontend/src/components/LearningMarkdown.vue
frontend/tests/chapter-navigation-ui.test.ts
另生成docs/course-learning-ui-design.md及本报告。

## 测试结果
- npm test：76通过、12跳过，共88项。新增3项真实目录组件SSR测试，覆盖课程名和完整长标题、当前/完成语义及忙碌禁用状态，均通过。12项为未设置本轮API联调目标的既有接口集成测试，没有将跳过记为通过。
- npm run build：通过，包含vue-tsc --noEmit类型检查。
- 既有Dashboard大于500KB提示保留，未扩展范围重构。
- CSS静态复核确认局部nav覆盖、260px网格、1200px容器、800px阅读宽度、16:9和900px响应式断点。
- 浏览器库存读取显示正式页停留/login，本轮未登录、未进入章节触发行为，也没有进行真实桌面/手机视觉截图验收。SSR测试和静态CSS检查不等同浏览器视觉验收。

日志：outputs/course-learning-ui-tests.log、outputs/course-learning-ui-build.log。

## 边界
没有修改backend、数据库、API、学习进度/事件、推荐或Spark。没有执行迁移、种子、业务数据写入或后端重启。侧栏展示真实章节标题，用户提供的示例名称未用于改动课程内容。

## 使用验证
刷新正式前端，登录后进入/resources/资源ID/learn；桌面检查左右布局与长章节标题，小于等于900px检查上下布局。该阶段仅有媒体示例地址，未新增真实文件。当前教学接口字段是否已安全重启启用属于前一阶段未完成的运行核验，本轮未处理或宣称完成。

本阶段完成后停止，等待下一步指令。
