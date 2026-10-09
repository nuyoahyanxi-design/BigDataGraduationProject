# 数据库实施方案

项目：基于 Spark 的学习行为分析与个性化资源推荐系统设计与实现。日期：2026-10-04。阶段：数据库实施。

## 目标与范围

依据 database-design.md V1.0 创建五张核心表，字段不增减。仅进行数据库迁移、少量固定测试数据和数据库级验证，不创建前后端或 Spark 业务代码。

## 技术与架构

复用 Windows MySQL 8.0.45，数据库 bigdata_graduation，专用账号通过 Windows 凭据管理器读取密码。Python 3.12 仅作为已有 Windows 数据库管理工具运行时，不改变项目 Python 3.11 环境。InnoDB、utf8mb4_unicode_ci、UTC DATETIME(3)。ASCII 标识使用 ascii_bin。

迁移位于 database/migrations/001_create_core_tables.sql，数据库测试位于 database/verify_core_database.py。不增加迁移记录表，迁移摘要及实际执行结果保存到验收报告。

## 数据模型

users 9 字段、resources 17 字段、learning_progress 6 字段、favorites 3 字段、learning_events 16 字段，共 51 字段。主键、唯一索引、普通索引和 RESTRICT 外键严格依照设计。CHECK 覆盖状态值域、时间一致性及事件状态组合。

标签字典、UUID 格式、指纹语义、管理员权限、资源可用性、跨表事件一致性不由数据库 CHECK 完整承担；后续服务阶段仍需实现。事件表的不可变性是业务接口约定，本阶段不添加触发器或修改账号权限。

## 实施与验证方案

执行前确认目标数据库为空；迁移不使用 IF NOT EXISTS 掩盖旧表差异。数据库可已存在，但必须检查字符集。MySQL DDL 隐式提交，因此失败不能宣称整个迁移自动回滚，应检查已创建对象后人工处理。

创建 4 个专用测试用户（1 管理员、3 学习者）和 6 个自编测试资源。随机测试口令仅存安全哈希，不记录口令。脚本用固定前缀定位样本，不更改其他数据，已有样本时停止。

通过直接数据库事务演示浏览、开始、完成、收藏、取消收藏五类事件；检查 UUID 唯一约束、外键、CHECK 和事务失败回滚。测试脚本不是后端接口；不以它证明未来 HTTP 鉴权、客户端重试或并发服务正确性。

真实执行结果、元数据和剩余限制见 outputs/database-implementation-acceptance-report.md。阶段完成后停止，等待用户确认。
