# 正式演示账号创建方案

日期：2026-10-05。仅准备student_demo（learner）与admin_demo（admin），不启动浏览器联调、不改dbstage_user_*、不删数据、不改表或直接写密码哈希。

## 认证与初始化方式

现有POST /api/auth/register固定创建learner，不接受role参数；没有公开管理员创建接口。保留这一权限边界，不新增可公开提权接口或SQL密码迁移。

本机初始化工具backend/tools/setup_demo_accounts.py先通过正式HTTP注册接口分别注册两个名字，然后使用正式登录和GET /api/users/me确认身份。密码由用户在本机交互终端通过getpass输入两遍，8–128字符，输入不显示字符；非交互终端拒绝运行。密码只在本进程和本机HTTP请求中使用，不写脚本、参数、环境变量、文件、日志或Git。用户应自行保存到个人密码管理器，工具不生成密码。

admin_demo注册后仍是learner。工具只针对已通过正式登录验证的admin_demo ID，在本地MySQL事务中锁定该行，将role从learner设为admin并更新updated_at；其他字段尤其password_hash不赋值、不更新。不修改任何dbstage记录。提交后重新通过正式登录获得反映admin身份的新JWT，调用/me及管理员只读接口验证。普通student_demo访问管理员接口应403。

管理员授权属于用户本次明确要求创建admin_demo的本机初始化操作，只放在tools目录，不挂载FastAPI路由。服务只连接固定127.0.0.1:8000，HTTP客户端禁用环境代理与重定向；数据库限定bigdata_graduation。不用于公网生产部署。

## 重跑与失败处理

若指定名字不存在才注册；若已存在，必须用用户输入的密码正式登录并核对ID、用户名及active状态，绝不覆盖或重设密码。student_demo必须是learner；admin_demo只能是learner或admin。用户输入错误则停止，不猜测。

两次注册属于独立API事务，不假装跨HTTP原子；中途失败可能已留下一个新账号，报告如实保留，不删除数据。重新运行可用相同用户已掌握的口令验证后续步骤；不能通过覆盖密码“修复”。管理员角色事务失败整体回滚。网络或校验失败只显示去敏说明，不打印请求体、响应Token、异常局部变量或密码。

## 用户手工执行

工具先提供只读--check，显示目标账号是否已存在及后端可达。正式创建需先启动已有后端；密码输入窗口不进行日志转录。

```bash
source /mnt/d/BigDataGraduationProject/environments/activate-bigdata.sh
cd /mnt/d/BigDataGraduationProject
PYTHONPATH=backend python backend/tools/setup_demo_accounts.py --check
PYTHONPATH=backend python backend/tools/setup_demo_accounts.py
```

按提示为student_demo输入两遍密码，再为admin_demo输入两遍密码。不要将密码发到聊天。完成后终端显示成功或明确阶段错误；证据保存outputs/demo-account-setup-evidence.json，包含账号ID、角色、HTTP验证状态及原dbstage完整性，不含密码、哈希或Token。

## 验收与阶段边界

检查两账号role/status、正式注册/登录/me、管理员200/学习者403，以及原dbstage所有字段保持一致。设计和工具准备不等于账号已创建；实际创建状态以outputs/demo-account-setup-report.md和证据JSON为准。用户完成手工输入前不得宣称创建成功。完成后停止，不执行资源学习操作或Spark重算。
