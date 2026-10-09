# 前端基础工程

在 WSL Ubuntu 中进入 `/mnt/d/BigDataGraduationProject/frontend`：

```bash
npm install
npm run build
npm run dev
```

后续复现依赖使用 `npm ci`。当前包含登录、个人账户、资源列表 `/resources`、详情 `/resources/:id` 和推荐 `/recommendations`；支持学习、收藏及离线推荐查看。

需要开发代理时复制 `.env.example` 为 `.env.local`，设置 API_PROXY_TARGET；VITE_API_BASE_URL 为浏览器请求前缀。勿将密码放入任何 VITE_ 变量。详细设计见 ../docs/frontend-architecture.md。

认证设计见 ../docs/frontend-auth-design.md。会话使用 sessionStorage，刷新后通过后端重新验证身份；关闭标签页结束会话。`npm test` 默认执行单元测试并跳过需要真实后端的集成测试。真实联调先启动现有后端，再在加载既有数据库环境变量的 WSL 终端执行：

```bash
AUTH_API_TARGET=http://127.0.0.1:8000/api AUTH_TEST_PYTHON=/home/nuyoah/.venvs/bigdata-graduation-env/bin/python PYTHONPATH=/mnt/d/BigDataGraduationProject/backend npm test
```

该测试通过正式注册 API 创建临时学习者，随机密码只在内存中，测试结束清理该临时用户。不要使用真实用户账号替代测试身份。

资源学习设计见 ../docs/frontend-resource-module-design.md。资源集成测试复用已发布资源，只清理临时测试用户的事件、进度及收藏，不删除已有资源。`/tests/resource-ui.html` 是独立模拟组件测试入口，显著标记模拟数据，不连接数据库，不被生产 index.html 或构建入口引用。

推荐展示设计见 ../docs/recommendation-display-design.md。推荐页面只读取已发布结果与同批次画像，新用户尚未批处理时显示待生成提示。`/tests/recommendation-ui.html` 及 `?empty=1` 是模拟组件验证入口，不连接数据库、不进入生产构建。
# 管理员后台

管理员入口 `/admin`：用户只读分页、资源搜索/新增/编辑/发布/下架、Spark最近发布批次查看。匿名跳转登录，学习者显示403页；服务端接口同时校验JWT和管理员角色。状态变更有确认对话框，新增先保存草稿。资源修改不会自动刷新离线统计结果。

`/tests/admin-ui.html` 为隔离模拟组件验证入口；支持 `?learner=1`、`?anonymous=1`、`?empty=1` 场景，不连接数据库，不属于生产构建入口。不能用该入口作为真实管理员登录验收。
