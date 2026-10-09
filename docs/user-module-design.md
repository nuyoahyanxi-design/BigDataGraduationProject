# 用户模块设计 V1.0

日期：2026-10-04。仅用户模块；沿用现有 users 表 9 字段，无迁移、无其他模块开发。

## API 与数据模型

| API | 输入 | 输出/状态 |
|---|---|---|
| POST /api/auth/register | username、password、可选 nickname、interest_tags | 201 安全用户信息；重复 409；格式错误 422 |
| POST /api/auth/login | username、password（JSON） | 200 access_token、token_type=bearer、expires_in；失败统一 401 |
| GET /api/users/me | Authorization: Bearer Token | 当前用户信息；缺失/无效/过期/停用身份 401 |
| PUT /api/users/interests | Bearer Token、interest_tags | 更新后的当前用户信息；格式错误 422 |

响应仅 id、username、nickname、role、status、interest_tags、created_at、updated_at；绝不返回 password 或 password_hash。请求禁止未知字段，不能提交 role/status/user_id；当前身份从 Token subject 获取并查数据库，不提供查询其他用户的路径。

用户名去首尾空白并转 ASCII 小写，3—50 位、字母/数字/下划线；数据库唯一约束处理并发重复。密码 8—128 字符，不裁剪；随机盐 scrypt N=16384,r=8,p=1，格式兼容数据库验收样本。密码强度及密码恢复后续单独设计。

兴趣为不超过 10 项的字符串数组，可空数组，拒绝重复、未知编码、非字符串及嵌套内容。首版受控字典：python、java、sql、mysql、spark、big-data、data-analysis、machine-learning、web-development、algorithms。编码集中到用户配置模块，后续扩展需版本化文档；此阶段不据此实现资源模块。

## 认证与角色

JWT 固定 HS256，密钥至少 32 字节，环境变量 JWT_SECRET；不在仓库、.env 或报告保存密钥。开发启动器从 Windows 凭据管理器获取/首次创建随机密钥并只注入进程环境。Token 包含 sub（字符串用户 ID）、role、iat、nbf、exp、iss、aud、jti、type=access；有效期 30 分钟，验证固定算法、签名、必需声明、issuer、audience、时间与 subject 格式。

每次认证检查数据库当前 active 状态和角色，不将 JWT 中的旧角色作为权限依据。公开注册固定 learner；admin 只能来自既有受控账号，不提供角色提升接口。提供 require_admin 依赖并测试，当前四接口允许活跃学习者/管理员操作自己的信息，不新增管理员业务接口。

## 事务与安全

注册显式提交，IntegrityError 回滚：唯一冲突 409，其他约束统一错误，不泄露 SQL。兴趣变更仅更新自身兴趣和 UTC updated_at。拒绝令牌异常统一 401。不存在账号执行固定 dummy 哈希验证，降低用户名时序差异；不宣称完全消除时序侧信道。

验证错误处理不返回 input，避免密码和 Token 被默认校验响应回显。ORM/SQL 错误统一去敏 503；不记录请求正文、认证头或令牌。SQLAlchemy 参数化查询。

## 实施与验收

core/security.py 处理哈希/JWT；schemas/users.py 安全输入输出；services/users.py 处理事务；api/users.py 提供四接口。既有 MySQL 上运行临时用户测试，结束只清理本次明确创建的用户，不影响已有样本；不写其他表。覆盖最少七场景及过期、伪造、停用、权限提升、隐私隔离、标签非法、数据库哈希持久化。同步路由避免密码哈希/数据库操作阻塞事件循环。

当前不提供刷新/退出撤销、找回密码、验证码、跨进程限流、生产 HTTPS。仅本机开发验收，不宣称达到公网部署验收。

参考：[PyJWT API 与固定算法验证](https://pyjwt.readthedocs.io/en/stable/api.html)、[Python scrypt](https://docs.python.org/3.11/library/hashlib.html#hashlib.scrypt)。
