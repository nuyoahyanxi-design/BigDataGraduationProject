# Recovered development environment plan — 2026-10-09

> 历史资料说明（2026-10-13补注）：下文设计、数量、失败与未验收结论属于原记录日期，不代表当前版本；保留原始证据，不将当时未执行的测试改写为通过。 当前技术栈、视频播放证据和各数据口径统一见[答辩当前状态说明](defense-current-state.md)；本次仅修订文档，没有重新验收或运行Spark。

Reuse Ubuntu-22.04-Recovered, nuyoah, existing Python 3.11.17 venv, Java17, PySpark3.5.7 and Node22.22.2.
Checks completed: pip check passed, frontend dependencies present, default user root, WSL NAT cannot reach Windows loopback MySQL, legacy credential loader requires absent Windows Python312.
Authorized changes: default Linux user nuyoah; mirrored WSL networking; append Spark environment paths; replace Windows-Python-dependent credential export with a Windows Credential Manager helper; update launcher distro name.
Keep before-change copies. Preserve business source and database contents. Validate DB reads, FastAPI/Vite readiness, and Spark local computation without business batch publication. No software reinstalls or dependency upgrades.
