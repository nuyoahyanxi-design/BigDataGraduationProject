# 正式演示账号准备报告

日期：2026-10-05。最终状态：两账号已通过用户手工输入口令完成正式注册、登录及权限验证。完成时间2026-10-05 12:13:01（Asia/Shanghai）。demo-account-setup-evidence.json状态completed。不是仅工具或方案准备完成。

## 实际完成

- 已保存docs/demo-account-setup.md，明确正式注册/登录流程和本机管理员角色初始化边界。
- 已实现backend/tools/setup_demo_accounts.py，固定目标student_demo与admin_demo，不添加公开管理员注册接口。
- 注册调用POST /api/auth/register，密码由现有后端生成哈希；工具不写password_hash。admin_demo完成身份验证后，单行事务只更新role及updated_at，再重新正式登录验证。
- 用户通过getpass输入并确认两个密码；不自动生成，不写文件/参数/环境/Git/报告；非交互终端拒绝读取，防止回退到明文输入。
- --check只读确认后端可达，当前两个目标账号均不存在。该检查不创建账号。
- 启动本轮临时后端及专门的本机交互窗口。两个密码都确认后才开始API注册，不修改dbstage_user_*或删除数据。

## 实际账号创建结果

| 账号 | ID | 角色 | 状态 | 正式注册 | 正式登录/当前用户 | 管理员只读接口 |
|---|---:|---|---|---|---|---|
| student_demo | 134 | learner | active | 201 | 200 / 200 | 403，符合权限 |
| admin_demo | 135 | admin | active | 201（初始learner） | 角色初始化后重新登录200 / 200 | 200，符合权限 |

两个账号均本轮新建，密码由用户在交互窗口手工输入并确认，没有自动生成或保存密码。student_demo兴趣初始为python、spark；admin_demo为空兴趣。注册由正式接口产生密码哈希，没有直接修改或写入密码哈希；只有admin_demo的角色与更新时间由受限本机事务调整。MySQL结构、既有资源及其他业务数据未变更。

工具完成原dbstage记录全部字段的前后对比，dbstage_records_unchanged=true。没有读取或回显原口令，也没有用MySQL/Ubuntu密码作为默认应用口令。

## 已验证内容

工具安全边界测试6项通过（0.96秒）：管理员角色初始化只改变role/updated_at、保留原密码哈希对象；拒绝dbstage和student_demo及disabled账号提权；拒绝非交互输入；API错误不输出响应体。测试使用内存模拟对象，不创建真实演示账号。

证据：demo-account-setup-tool-tests.log、demo-account-setup-precheck.log、demo-account-setup-window.json；实际创建过程仅记录去敏demo-account-setup-evidence.json。

## 当前限制及失败处理

本次用户密码输入、注册和登录已完成；没有执行真实浏览器页面联调。以后若重跑出错或中断，可能留下已完成注册的账号，应保留数据，不删除或重置；重跑必须使用用户已掌握的同一密码，通过正式登录确认身份。工具不提供密码找回，用户应自行安全保存。

不运行原固定小样本全量测试、不执行学习操作、资源修改、Spark重算或浏览器联调。原数据验证由工具对dbstage全部字段的前后只读比对完成，成功时证据写dbstage_records_unchanged=true。

## 下一步与停止边界

实际创建及接口验证已完成，关闭本轮临时后端后停止。交互终端若仍显示Press Enter to close可由用户按回车关闭。不要把密码发到聊天。新账号尚未运行Spark批次，推荐与画像可能暂为空；这是后续联调流程需要处理的状态，不能本轮提前计算。下一步浏览器联调须用户另行授权。

本轮新增两位线上用户，部分历史测试固定原4用户/3学习者数量；以后全量测试需区分演示数据与测试基线，不能通过删除演示账号恢复旧断言。历史238项结果属于最终验收时的快照，本轮新增工具6项测试另行记录，不将其冒充新全量回归。
