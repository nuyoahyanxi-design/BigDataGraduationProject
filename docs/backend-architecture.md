# FastAPI 后端基础架构

日期：2026-10-04。范围：工程基础、连接和五表 ORM；用户已授权本阶段实施，沿用已确认数据库设计。

## 目录与职责

backend/app/main.py 为应用入口；core/config.py 读取和校验环境变量；database/base.py 为声明式基类，database/session.py 为引擎与会话；models/core.py 映射五张现有表；schemas、services、api 预留为空包；backend/tests 为基础验收测试。后续业务设计确认后再实现接口与服务。

## 技术选型

使用已有 WSL Python 3.11 虚拟环境 bigdata-graduation-env；FastAPI 0.115.12、SQLAlchemy 2.0.40、PyMySQL 1.1.1。采用同步 SQLAlchemy Session，未来同步数据库接口使用普通 def，避免同步调用阻塞异步事件循环。本阶段不引入异步驱动、任务队列或 Spark 依赖。

## 数据库连接

MYSQL_HOST、MYSQL_PORT、MYSQL_DATABASE、MYSQL_USER、MYSQL_PASSWORD、MYSQL_CHARSET 来自进程环境变量。复用 environments/activate-bigdata.sh 的现有凭据加载，不修改该目录；.env.example 仅为配置参考，不自动加载，也不保存实际密码。使用 URL.create 处理密码特殊字符，禁止打印连接 URL、密码或原始连接错误。连接池 pre_ping；每个新连接设置 UTC。Session 关闭负责释放资源，事务提交由未来业务服务明确控制。

## ORM 原则

五表全部 51 字段及已有主键、索引、外键、CHECK、数据库默认值映射，不增加字段。MySQL unsigned、JSON、DATETIME(3) 与 ascii_bin 精确保留；不调用 create_all、drop_all，不自动执行迁移。暂不定义跨表 relationship 或序列化 schemas，避免无授权业务扩展及密码哈希意外暴露。

## 生命周期与实施方案

应用启动时读取配置、创建引擎并 SELECT 1 检查连接，失败使用不含凭据的统一错误；关闭时 dispose。仅 FastAPI 自动文档路由，无登录、资源、行为或健康业务端点。基础测试通过 TestClient 和真实 Uvicorn HTTP 启动检查，ORM 只读五表、对照数据库列与索引；不写入测试业务数据。

依赖版本记录到 backend/requirements.txt，测试依赖单独记录。执行必须先 source 现有激活脚本，再从 backend 启动 uvicorn app.main:app。版本、实际命令与测试证据保存在 outputs/backend-foundation-acceptance-report.md。

参考：[SQLAlchemy 引擎及 URL 配置](https://docs.sqlalchemy.org/en/20/core/engines.html)、[FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/)。
