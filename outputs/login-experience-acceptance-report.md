# 登录体验与账号自助功能验收报告

日期：2026-10-23。

## 已完成
1. 登录页：暖白双栏插画、输入框图标、密码显隐、整行按钮、手机单列。
2. 服务端 PNG 验证码：120 秒、单次消费、错误也消费，刷新获取新图片；登录、注册和密码重置校验。单进程内存限流、容量上限。JSON 不返回答案。
3. 注册：复用现有接口，账号默认 learner，禁止提交角色；注册事务同时保存恢复码摘要，明文仅本次返回。
4. 记住我：默认标签页保存、30 分钟；勾选后本地保存令牌与截止时间、7 天，不保存密码。退出清理两种存储。
5. 恢复码找回：用户名、恢复码、验证码及新密码；用户行锁保护同一账号，密码哈希与恢复码摘要同一事务更新；旧码失效并显示新码，重置后不自动登录。
6. 已有账号：个人账户页可验证当前密码生成或轮换恢复码，不自动为演示账号设置。
7. JWT 增加密码指纹，重置密码后旧令牌失效；升级前没有指纹的旧会话同样需要重新登录。

## 数据库与数据边界
- 已显式执行 008_create_auth_recovery_codes.sql，只新增认证辅助表，无启动自动建表。
- 初次执行前后已有表结构和行数一致；复核迁移幂等且全部现有表 CHECKSUM、行数及结构一致，证据为 outputs/login-auth-migration-evidence.json。复核 created=false 表示表已在本轮首次执行时创建，不代表未执行迁移。
- 未修改现有演示账号密码、角色或恢复码，未新增实际业务用户；认证完整写入流程测试全部在独立 SQLite 内存库完成。MySQL 只执行新增表及只读核验。
- 未修改学习内容、Spark、推荐算法、视频、账号配置或凭据存储。

## 验证结果
- 类型检查与生产构建通过；原有超过 500kB 构建包提示保留。
- 前端：22 文件通过、3 文件跳过；170 项通过、12 项跳过。新增 6 项会话持久化测试覆盖重开恢复、退出、过期、受限存储与不保存密码。
- 后端：12 项隔离认证 HTTP 测试通过；另 2 项实际 MySQL 只读启动/OpenAPI/连接检查通过，共 14 项。未运行会修改开发业务数据的全套后端集成测试。
- 实际运行端经前端代理：验证码 HTTP 200，PNG 格式，答案不在 JSON；缺少验证码的登录 HTTP 400。证据 outputs/login-live-probe.json。
- 浏览器：登录、注册、找回入口与表单真实显示；1440px 和 390px 无横向溢出，验证码图片成功加载。
- 截图：outputs/login-experience/login-desktop.png、register-desktop.png、reset-desktop.png、login-mobile.png，未包含明文密码或恢复码。
- 浏览器未代用户识别验证码、提交注册或修改密码。完整账号流程由隔离测试验证，真人验收需用户自行输入验证码。

## 安全限制
- 此为当前本地单进程部署实现，验证码及限流状态重启会清空，多实例须迁移共享存储。验证码不代表高强度反机器人保护。
- 沿用现有 Bearer 浏览器存储方式；7 天令牌仍受 XSS 风险影响，非本机部署需 HTTPS。退出清理本机缓存，不声称撤销所有设备会话；密码重置会撤销旧密码对应的全部令牌。
- 无邮箱或手机号找回；旧账号需先登录生成恢复码。没有密码且没有恢复码时仅能由维护人员线下核验，未开放免验证重置接口。
- AUTH_CAPTCHA_REQUIRED 默认为 true，既有集成测试在测试进程关闭，以保留直接 API fixture；新增隔离认证测试强制 true。生产不应关闭。

## 文件与阶段状态
主要代码：backend/app/api/users.py、core/security.py、schemas/users.py、services/users.py、services/auth_challenges.py、models/auth_recovery.py；数据库增量迁移及应用工具；前端 LoginView、RecoverySettings、HomeView、认证 API、类型、会话存储和错误提示；对应测试及 docs/login-experience-design.md。
保留本轮前已有文档与视觉改动；未读取未跟踪的账号密码文本，未执行 git add/commit/push。完成后等待人工验收，不继续扩展功能。

参考：[OWASP 认证](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)、[密码恢复](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html)。
