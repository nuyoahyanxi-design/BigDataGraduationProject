# 答辩本机启动说明

更新日期：2026-10-13。当前发行版Ubuntu-22.04-Recovered；项目D:\BigDataGraduationProject。技术栈与验证边界见[当前状态](defense-current-state.md)。本次只写说明，未启动或重启服务。

优先复用正在运行的MySQL80、后端8000及前端5173。实际验收地址为http://127.0.0.1:5173/login和http://127.0.0.1:8000/openapi.json。正常服务无需重复启动。

若服务未运行，使用已有Windows入口`start-project.bat`或分别在WSL项目根目录执行：

```bash
cd /mnt/d/BigDataGraduationProject
bash scripts/start-project-service.sh backend
```

另一个WSL终端：

```bash
cd /mnt/d/BigDataGraduationProject
bash scripts/start-project-service.sh frontend
```

服务脚本激活已有Python环境、安全加载数据库/JWT配置和现有.env.local，不要求重新安装依赖。配置缺失时先记录异常，不打印凭据、不自动补写配置。MySQL未运行时由Windows服务管理器启动已有MySQL80，不重新初始化数据库。停止服务使用所属终端Ctrl+C；演示期间不要关闭WSL。

本轮仅验收已运行进程的日志、页面和接口，不是重新执行冷启动或双击启动测试。阅读历史启动报告时以原日期为准，旧localhost/旧WSL发行版说明不覆盖上述已验收入口。

账号使用已有student_demo/admin_demo；密码由用户保管，不放PPT、报告或屏幕录制。课程详情/视频正常操作会新增事件，AI会新增问答；不点击完成、收藏、课程保存、发布等会改变已有状态的操作。要求数据库零新增时只展示已有截图/结果。

现场推荐顺序：学生登录→首页→搜索正式课程→详情→第2章视频10–15秒→既有学习状态→画像推荐→管理员用户/课程/批次→看板→可选AI成功历史。最新Spark为离线结果，本次演示不运行处理任务；需要重算须另行明确授权。不能声称刷新页面会执行Spark。
