# 开发环境说明

日期：2026-10-04。环境验收与业务验收分开记录。

## 本轮检查

| 项目 | 实测结果 |
|---|---|
| Ubuntu WSL2 | Ubuntu-22.04开发发行版可正常执行命令 |
| Java/javac | 17.0.20.1，Linux JDK |
| JAVA_HOME | /usr/lib/jvm/java-17-openjdk-amd64 |
| Python | 3.11.17，独立bigdata-graduation-env |
| PySpark | 3.5.7，可导入；运行时验证结果见初始化报告 |
| Node/npm | 22.22.2 / 10.9.7 |
| Git | 2.34.1，沿用已确认身份 |
| pip check | 无依赖冲突 |

Python位于/home/nuyoah/.venvs/bigdata-graduation-env/bin/python。本轮不安装或升级依赖。

MySQL、Parquet和VS Code完整验收见outputs/local-development-environment-acceptance-report.md；这些已有记录不冒充本轮重复执行的检查。MySQL已有验收版本8.0.45，本轮未修改服务、账号或数据。

## 使用

```bash
source /mnt/d/BigDataGraduationProject/environments/activate-bigdata.sh
cd /mnt/d/BigDataGraduationProject
python --version
python -m pip check
node --version
npm --version
java -version
javac -version
python -c "import pyspark; print(pyspark.__version__)"
```

请在WSL内开发。Windows默认Java/Python独立保留。正式源码分别位于frontend、backend、spark、database。

已有快捷方式仍打开code空目录，本轮不改动。正式开发时在WSL窗口打开项目根目录或对应模块。

## 安全与状态

environments、wsl、spark-experiments本轮不修改，并整体忽略。凭据通过Windows安全存储和进程环境变量加载，不写入源码、日志、报告或.env；不要打印全部环境变量。

本轮没有业务启动命令、数据库迁移或Spark任务。后续工程依赖在各模块初始化时锁定。
