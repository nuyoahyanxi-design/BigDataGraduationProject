# Recovered development environment plan — 2026-10-09
Reuse Ubuntu-22.04-Recovered, nuyoah, existing Python 3.11.17 venv, Java17, PySpark3.5.7 and Node22.22.2.
Checks completed: pip check passed, frontend dependencies present, default user root, WSL NAT cannot reach Windows loopback MySQL, legacy credential loader requires absent Windows Python312.
Authorized changes: default Linux user nuyoah; mirrored WSL networking; append Spark environment paths; replace Windows-Python-dependent credential export with a Windows Credential Manager helper; update launcher distro name.
Keep before-change copies. Preserve business source and database contents. Validate DB reads, FastAPI/Vite readiness, and Spark local computation without business batch publication. No software reinstalls or dependency upgrades.
