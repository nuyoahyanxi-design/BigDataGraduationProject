"""Environment/local-file/hidden-input launcher; never prints credentials."""
import getpass
import os
import runpy
import socket
import time
from pathlib import Path
from app.core.ai_config import AISettings

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from local_ai_config import load_config
from runtime_config import load_runtime
load_runtime()
values = load_config()
model, key = values['AGNES_MODEL'], values['AGNES_API_KEY']
del values
os.environ['AI_ASSISTANT_ENABLED'] = 'true'
os.environ['AGNES_MODEL'] = model
os.environ['AGNES_API_KEY'] = key
os.environ['AGNES_BASE_URL'] = 'https://apihub.agnes-ai.com/v1'
del key
try:
    settings = AISettings.from_environment()
    if not settings.ready:
        raise RuntimeError()
except RuntimeError:
    raise SystemExit('Invalid configuration; nothing saved, existing service unchanged.') from None
print('Configuration loaded securely. Waiting for port 8000 to become available.')
print('Keep this service window open. Local configuration is excluded from Git.')
while True:
    with socket.socket() as sock:
        sock.settimeout(0.5)
        busy = sock.connect_ex(('127.0.0.1', 8000)) == 0
    if not busy:
        break
    time.sleep(1)
print('Starting existing FastAPI with AI enabled. Keep this window open during acceptance.')
runpy.run_path(str(Path(__file__).with_name('start-real-browser-precheck-backend.py')), run_name='__main__')
