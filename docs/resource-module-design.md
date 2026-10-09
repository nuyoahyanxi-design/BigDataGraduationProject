# 资源管理模块设计 V1.0

日期：2026-10-04。范围：基于现有 resources 的17字段映射，实施五个接口；不加字段/表，不接入学习、收藏、事件、推荐、Spark或前端。

## API与权限

| 接口 | 输入与规则 | 输出 |
|---|---|---|
| POST /api/resources | 管理员；可编辑字段，服务端固定draft、版本1、created_by当前管理员 | 201资源详情 |
| PUT /api/resources/{id} | 管理员；完整替换可编辑字段，不能提交状态/版本/创建者/时间 | 200资源详情 |
| PATCH /api/resources/{id}/status | 管理员；status=published或offline | 200资源详情 |
| GET /api/resources | 登录；page>=1、page_size=1..100，可选q/title搜索、category_code、resource_type、status | items、total、page、page_size |
| GET /api/resources/{id} | 学习者仅published，管理员可看draft/published/offline | 200详情；不可见或不存在统一404 |

列表默认published，管理员可显式status=draft/offline/all；学习者请求扩大状态范围返回403。deleted不出现在任何列表/详情，无删除入口。未登录统一401。列表按id倒序稳定分页，q支持字面子串搜索（转义LIKE通配符），暂不做全文检索；列表不返回大正文。

## 数据与校验

可编辑字段：title、resource_type、category_code、tags、difficulty、summary、content、content_url、source_name、license_note。PUT完整替换，省略可选字段重置为默认/NULL；不支持部分字段PUT。title/summary去首尾空白且不能为空；长度依照数据库，正文最多100000字符。

类型document/course/exercise；difficulty严格整数1..3。标签复用用户模块受控字典，严格字符串数组、最多10项、无重复/未知值；草稿允许空标签与无内容，发布要求至少一标签以及非空正文或有效HTTP/HTTPS地址。

分类受控字典：python-basics、java-basics、databases、data-engineering、machine-learning、web-development、algorithms。其中data-engineering兼容已存在验收资源。地址最多1000字符，仅HTTP/HTTPS，禁止用户凭据、fragment和localhost/私有IP/本机路径；不主动访问网址，不承诺外链可达或内容合法。域名解析及重定向可达性不属于本阶段验证。

拒绝额外字段，防止created_by/status/version_no等注入。API响应白名单均仅资源字段，不返回用户隐私或凭据。

## 状态与版本

允许draft→published、published→offline、offline→published；同状态published/offline重复操作无变化成功，不刷新时间/版本。draft→offline拒绝409；向draft/deleted或未知状态请求422。deleted为数据库预留终态，本阶段不提供进入/离开的API。

首次发布写published_at，此后重新上架保持原时间。任何实际可编辑字段变化或状态变化version_no+1，updated_at写UTC；无变化请求不递增。修改已发布资源仍必须满足发布条件。version_no溢出返回409，不改变数据。

## 架构与事务

schemas/resources.py定义严格输入和白名单输出；services/resources.py负责查询、可见性、发布校验及事务；api/resources.py复用用户JWT/current_user/require_admin。同步路由适配已有同步Session。

写操作统一先锁当前管理员users行并重新检查角色/状态，再锁目标resources行，遵循后续行为设计的用户→资源锁顺序。事务提交后refresh资源，返回数据库持久化值以对齐DATETIME(3)精度；异常由既有去敏处理及Session关闭回滚。悲观锁保证资源版本不会并发丢增，但完整PUT仍是后到请求覆盖前值；不宣称实现乐观冲突检测。

## 验收方案

真实MySQL上的临时管理员/学习者与临时资源，验证创建、修改、列表分页搜索、上下架、权限、非法状态和发布完整性、版本及首次发布时间；清理仅本轮确切ID。检查学习进度/收藏/事件无写入，回归用户模块及基础启动。文档/测试结果保存outputs，完成停止等待确认。
