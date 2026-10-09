# 学习行为采集与状态管理设计 V1.0

日期：2026-10-04。仅行为产生、状态及个人查询，沿用五表51字段，不加表/字段，不开发Spark、画像、推荐或前端。

## 1. 行为模型

用户需求中的大写行为名称为API编码，数据库沿用确认设计及CHECK要求的小写：RESOURCE_VIEW→resource_view、LEARNING_START→learning_start、LEARNING_COMPLETE→learning_complete、FAVORITE_ADD→favorite_add、FAVORITE_REMOVE→favorite_remove。响应及查询过滤使用大写，持久化采用小写，不修改已有事件或迁移。

浏览有效性1、来源client、会话UUID必填、状态前后空；四业务事件来源server。开始not_started→in_progress；完成in_progress→completed；收藏not_favorited→favorited；取消反向。相同状态新UUID形成0回执，不刷新首次开始/完成/收藏时间。完成未开始资源拒绝409，不写事件。拒绝请求不计为被接受的业务行为。

## 2. API

| 接口 | 请求/输出 |
|---|---|
| POST /api/resources/{id}/view | event_uuid(UUIDv4)、session_id(UUIDv4)、可选带时区client_occurred_at；返回事件回执 |
| POST /api/resources/{id}/start | event_uuid、可选session_id；返回事件回执 |
| POST /api/resources/{id}/complete | 同上 |
| POST /api/resources/{id}/favorite | 同上 |
| DELETE /api/resources/{id}/favorite | JSON body，同上；同逻辑请求重试保持UUID |
| GET /api/users/me/progress | 分页，可选resource_id、status；指定尚无记录资源返回not_started派生项（不插入）；普通列表只列已开始项 |
| GET /api/users/me/favorites | 分页，返回个人收藏关系及资源ID，不暴露下架资源正文 |
| GET /api/users/me/events | 分页，可选resource_id、event_type(大写)、is_effective=0/1；仅个人历史 |

所有请求必须活跃JWT身份，不接受user_id或来源/版本/状态字段注入。所有写回执200且重放响应完全一致；查询page>=1、page_size<=100。不存在或新操作不可用资源404；无Token/停用401，UUID语义冲突409，格式422，持久化错误去敏503。

新浏览/开始/完成/收藏只接受published；管理员也不得对草稿产生学习证据。下架或软删除资源可取消个人已有收藏，历史查询保留关系/事件；非发布且无收藏的新取消请求404。匹配旧回执优先返回，因此资源后来下架不改变过去成功请求结果。

## 3. 幂等

event_uuid规范小写UUIDv4且数据库全局唯一。指纹SHA256(JSON紧凑数组[1,user_id,resource_id,数据库事件类型]，UTF-8)；运行时资源版本、会话、客户端时间不参与语义，改这些重试仍返回原回执。改变用户/资源/事件类型返回统一409，不泄露别人的记录。

首先尝试读原回执；未找到时结束只读认证事务，重新开始业务事务，按用户行锁后再读回执，避免MySQL REPEATABLE READ认证快照漏看刚提交的同UUID。四业务按用户行FOR UPDATE串行，解决不存在收藏/进度行的并发；浏览只持有用户共享读锁，不进行业务状态串行写锁。统一用户→资源共享锁，与管理员用户→资源排他锁顺序一致。

成功事务中的0回执必须保留：旧的“取消不存在收藏”重试不得删除之后新建的收藏。唯一冲突先整体回滚，再在新快照读已提交回执验证指纹；死锁1213/锁等待1205至多3次尝试，沿用UUID，耗尽返回去敏503，不无限循环。

## 4. 事务与时间

业务状态变化先flush但不commit，再插入事件flush，统一commit；任一步失败rollback。开始同样保证进度+事件同事务。事件不可通过API修改/删除。

received_at为HTTP中间件入口UTC毫秒时间，occurred_at在锁取得后确定，至少received_at；进度/收藏变化使用同一occurred_at。客户端时间仅浏览诊断，必须带时区转换UTC，不能控制排序。事件resource_version取事务内锁定资源当前版本；不代表历史元数据内容已保存。

提交后事件refresh，所有重放返回原UUID、状态、时间、版本及有效性，不混入当前状态。当前状态通过独立个人查询获取。资源/进度版本时间变化不会覆盖原事件。

## 5. 架构与验收

schemas/learning.py定义输入、事件回执、个人状态与分页；services/learning.py负责锁、事务、指纹及查询；api/learning.py提供八接口。复用现有认证及会话，无DDL或后台任务。

验收真实MySQL：五类有效事件、同UUID完全重放、跨用户/资源/类型冲突、新UUID无变化0回执、旧取消重放、新收藏保留、完成流程及注入真实CHECK失败后的状态回滚、并发、权限与个人查询；测试仅本轮创建ID，最终按事件→收藏/进度→资源→用户清理。全套回归之前阶段，证据保存在outputs。

限制：手动完成不证明实际学完；浏览不能证明页面实际可见；无离线队列/时长/限流/跨时钟纠偏；查询分页不保证并发写入时固定快照。后续Spark须过滤0回执及按既定口径清洗，但本阶段不实施。

参考：[SQLAlchemy事务管理](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html)、[MySQL锁定读取](https://dev.mysql.com/doc/refman/8.0/en/innodb-locking-reads.html)。
