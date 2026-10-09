#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source ./environments/activate-bigdata.sh
case "${1:-}" in
  configure)
    exec python scripts/local_ai_config.py
    ;;
  backend)
    _backend_proxy_exports="$(python scripts/wsl_backend_proxy.py)"
    eval "$_backend_proxy_exports"
    unset _backend_proxy_exports
    export PYTHONPATH="$PWD/backend${PYTHONPATH:+:$PYTHONPATH}"
    exec python outputs/start-ai-real-model-secure.py
    ;;
  frontend)
    export API_PROXY_TARGET="${API_PROXY_TARGET:-http://127.0.0.1:8000}"
    cd frontend
    exec npm run dev -- --host 0.0.0.0
    ;;
  *) echo 'Expected backend, frontend, or configure.' >&2; exit 2 ;;
esac
