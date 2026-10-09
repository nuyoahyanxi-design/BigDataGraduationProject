# Vue3 前端基础架构设计

日期：2026-10-05。本阶段授权范围为工程初始化及两个占位页，交付验收报告后停止。

## 设计目标与技术方案

使用现有 WSL Ubuntu 的 Node 22.22.2、npm 10.9.7，不新增运行环境。采用 Vue 3.5、TypeScript 5.9、Vite 7、Element Plus 2、Pinia 3、Vue Router 4、Axios 1、ECharts 6。直接依赖固定版本，package-lock.json 固定完整依赖树，后续可用 npm ci 复现。

Vite 7 支持现有 Node 版本，版本要求见 https://vite.dev/guide/ 。Element Plus 使用组件显式导入及统一样式，不额外引入自动导入插件，见 https://element-plus.org/en-US/guide/quickstart 。ECharts 仅准备依赖和类型，本阶段不创建业务图表。

## 目录与架构

| 路径 | 作用 |
| --- | --- |
| frontend/src/main.ts、App.vue | 应用启动、注册路由和状态容器、页面出口 |
| src/components | 通用应用外壳，后续放可复用组件 |
| src/views | 首页与登录占位页 |
| src/router | 页面路由及懒加载 |
| src/stores | Pinia 实例及应用基础状态 |
| src/api | Axios 实例、泛型请求函数、统一错误类型 |
| src/types | 环境变量与图表类型 |
| src/styles | 基础响应式样式 |

路由为 `/` 与 `/login`，未知路由回到首页。使用 HTML5 history，正式部署需配置服务端回退到 index.html。页面 → 通用组件；页面未来通过 api 请求服务端，状态由 stores 管理。不提前建立认证守卫或业务状态。

## 配置与数据模型

本阶段不修改数据库、不定义新的业务数据模型。Pinia 仅保存应用名称及阶段说明。API 请求函数使用泛型保留后续响应类型约束；错误仅包含状态码和公共提示，不记录请求体、凭据或原始响应。

`.env.example` 提供 VITE_API_BASE_URL（默认相对路径 /api）、VITE_API_TIMEOUT_MS 和 API_PROXY_TARGET。前两个变量会进入浏览器，禁止放密码或令牌。API_PROXY_TARGET 只由 Vite 服务端读取，用于开发代理，并保留 /api 路径。后端地址由环境变量提供，无源码地址常量。未配置代理时，前端仍可启动，但访问 API 需部署同源服务或自行配置代理。本阶段占位页不发送业务请求。

## 实现与验证方案

先生成本设计，再创建工程文件。通过 npm install 安装固定依赖；npm run build 先执行 vue-tsc 类型检查再构建；启动开发服务器并检查首页、登录路径和模块响应。使用现有 npm 镜像，官方仓库在 WSL 直连超时，不修改全局网络配置。

WSL 执行目录：`/mnt/d/BigDataGraduationProject/frontend`。命令：`npm install`、`npm run build`、`npm run dev -- --host 127.0.0.1 --port 5173 --strictPort`。需要代理时复制 `.env.example` 为 `.env.local` 并修改目标地址；该文件被 Git 忽略。安装目录为本工程 node_modules，构建输出为 dist，二者不提交。

## 阶段边界

登录页不实现登录表单、Token 或账号校验。首页不展示资源或推荐数据。无资源、推荐、后台页面；不修改后端、Spark、数据库以及 environments、wsl、spark-experiments。实际验证结果在 outputs/frontend-foundation-acceptance-report.md 中记录。
