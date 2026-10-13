# 真实系统截图

> 历史材料补注（2026-10-13）：本文审查/修订结果或截图属于原日期与冻结版本，不是当前批次的实时数据。当前基线b8474f2、源批次20261013T052412Z_1fc73f17，真实视频播放及数量口径见[答辩当前状态](../docs/defense-current-state.md)；原审查行号、截图文件和历史结果不改写。

采集日期：2026-10-11。来源为本机浏览器实际运行页面，未生成界面图片；浏览器截图统一保存为PNG（仅格式转换，不修改页面内容）。

| 文件 | 对应页面 | 账号 |
|---|---|---|
| 01-login.png | /login，空白登录表单 | 未登录 |
| 02-home.png | / | student_demo |
| 03-course-list.png | /resources | student_demo |
| 04-learning.png | /resources/1069/learn，第2章筛选与列转换 | student_demo |
| 05-profile.png | /recommendations中的画像区域（截取） | student_demo |
| 06-recommendation.png | /recommendations，内容推荐 | student_demo |
| 07-dashboard.png | /dashboard | admin_demo（用户自行登录） |

前端首页、后端OpenAPI返回HTTP200，MySQL只读SELECT1通过。截图没有密码、密钥、Token或请求头。画像和看板保留真实批次时间及开发验收样本说明，不声称真实用户研究效果。

页面使用浏览器当前尺寸，完整页截图用于内容较长的页面，画像截图仅截取真实画像区域。用户画像没有独立路由。课程列表包含既有验收资源，没有为截图改数据或隐藏真实内容。

没有修改账号、手动完成章节、收藏、发送AI问答或运行Spark。正常进入课程时，页面按既有逻辑记录学习行为；因此截图浏览不能被描述为完全无数据库写入。此次没有执行数据库编辑、迁移或数据修复。

后续更新截图时使用同名真实文件，人工核对隐私和显示效果，保持根README相对链接一致；.gitkeep保留。
