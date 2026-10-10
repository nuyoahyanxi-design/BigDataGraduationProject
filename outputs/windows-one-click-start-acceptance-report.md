# Windows一键启动验收报告

日期：2026-10-05

## 目标与实际交付
双击Windows入口启动WSL前后端，等待就绪后打开localhost:5173；不改业务、数据库、API或Key管理。

新增start-project.bat、scripts/start-project.ps1、scripts/start-project-service.sh、scripts/test-start-project.ps1。README增加使用、停止、超时及安全输入说明；设计文档为docs/windows-one-click-start-design.md。

## 实际执行结果
1. 检查时MySQL80为Running，WSL Ubuntu-22.04可用；Windows根目录正确映射/mnt/d/BigDataGraduationProject。实际启动测试前发现前后端服务均未运行，没有主动停止它们。
2. 从cmd执行start-project.bat -NoPause，实际打开两个可见Windows PowerShell窗口，经WSL激活既有环境后启动后端安全脚本及Vite。用户在后端窗口完成模型与Key输入，回复“已输入”；输入未读取、截图、输出或保存到本次文件。
3. 初版就绪探针使用需要认证的capabilities，返回401，导致等待未结束。改用/api/auth/login空JSON请求的422验证代理，不改接口或权限；Windows PowerShell本地HTTP探针使用5秒请求期限，替换不够可靠的2秒期限。这不是Agnes模型调用timeout修改。
4. 后端OpenAPI与首页返回正常；前端代理的空登录请求返回后端422。启动入口最终执行成功，退出码0，并调用Start-Process打开默认浏览器http://localhost:5173。不声称完成浏览器账号登录或AI真实问答。
5. 再运行CheckOnly：Backend ready=True、frontend and proxy ready=True，退出码0。正常启动入口重复运行复用现有FastAPI与Vite，不开启重复服务；主入口可以关闭，服务独立运行。
6. 两个服务目前保留运行；未停止MySQL/WSL，未执行迁移或Spark任务。

## 测试
- Windows PowerShell语法解析通过；实际Windows PowerShell入口执行通过。
- Bash -n scripts/start-project-service.sh通过；环境激活和两个实际服务启动通过。
- scripts/test-start-project.ps1：7项全部通过，覆盖后端身份、无关后端、页面加422代理正常、代理404、后端502、意外401和无关前端。
- 实际CheckOnly与正常复用入口均退出0。
- 本次不改前端/后端业务源码，未重复运行业务全量npm测试或构建。

证据：outputs/windows-one-click-start-tests.log、outputs/windows-one-click-start-live.log。独立后端终端输出未重定向或存档，避免记录秘密。

## 安全与限制
仅使用既有安全输入机制，不写Key、不读取其他进程的环境、不修改用户密码。新窗口不自动继承另一WSL终端的临时环境变量，因此新后端启动可能需要手动输入model/Key。已经运行的后端直接复用，不自动切换其AI配置。端口占用而服务不正常时明确失败，不终止他人进程。

默认等待300秒，HTTP就绪探针5秒、轮询间隔2秒；真实总等待可能因WSL唤醒和探针耗时略超过设置值。不会改变Windows执行策略，无管理员提权。缺失依赖、MySQL未运行或凭据配置失败需要按服务终端提示处理，启动器不自动安装或修改数据库。

完成本阶段后停止，等待下一步指令。
