# Windows一键启动设计

仅新增启动工具和文档，不改业务、数据库、API或Spark。根目录bat通过Windows PowerShell调度WSL Ubuntu-22.04，在独立可见终端执行既有安全后端启动与Vite。复用现有环境激活脚本，不创建新虚拟环境、不安装依赖。

后端使用PYTHONPATH=backend python outputs/start-ai-real-model-secure.py，前端使用npm run dev并显式设置本机代理目标。保留Key环境变量优先及getpass隐藏输入；不记录服务输出，不写Key文件。

MySQL未运行则报错，端口被异常服务占用则报错；不自动提权或终止现有进程。已就绪服务复用，等待OpenAPI、前端页面与/api/auth/login空请求的422参数校验响应就绪才打开浏览器，默认等待300秒。脚本不改变PowerShell执行策略，当前Windows PowerShell已有策略允许本地脚本。

另一个WSL终端的临时export不能由新窗口自动继承；冷启动可能需要手动输入模型和Key。执行时发现前后端均未运行，实际验证两个服务窗口启动及用户手动安全输入，再验证重复运行复用。未停止MySQL或修改已有Key管理方式。

