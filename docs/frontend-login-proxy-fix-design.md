# 登录请求404修复设计

目标：仅恢复前端至现有/api/auth/login的代理链路，不修改认证、数据库、密码或权限。

现状：本项目无src/services/auth.ts，实际登录入口为src/api/auth.ts，url=/auth/login；Axios默认baseURL=/api。Network名称login不等于请求地址/login。Vite仅当API_PROXY_TARGET存在才启用代理，项目只有.env.example；上次前端重启未继承旧启动进程的代理变量，因此5173的/api/auth/login返回404。

方案：Vite默认代理至本机http://127.0.0.1:8000，仍优先环境变量和配置文件覆盖，不重写/api路径。添加请求最终URI和代理默认值/覆盖回归测试。重启前端后使用空请求体验证请求进入后端参数校验，不使用真实密码。
