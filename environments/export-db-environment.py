"""Emit captured shell assignments from Windows Credential Manager; never display."""
import base64
import json
import shlex
import subprocess
from pathlib import Path

helper = Path(__file__).with_name('windows-runtime-vault.ps1')
windows_helper = subprocess.check_output(['wslpath', '-w', str(helper)], text=True).strip()
command = "& ([scriptblock]::Create([IO.File]::ReadAllText('" + windows_helper.replace("'", "''") + "'))) -Mode Read"
result = subprocess.run(['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe',
                         '-NoProfile', '-NonInteractive', '-Command', command],
                        capture_output=True, text=True)
if result.returncode:
    raise SystemExit('Runtime credential loading failed; run the Windows provisioning window')
credential = json.loads(result.stdout)
values = dict(MYSQL_HOST='127.0.0.1', MYSQL_PORT='3306', MYSQL_DATABASE='bigdata_graduation',
              MYSQL_USER='bigdata_dev', MYSQL_CHARSET='utf8mb4',
              MYSQL_PASSWORD=base64.b64decode(credential['password_b64']).decode('utf-8'),
              JWT_SECRET=base64.b64decode(credential['jwt_b64']).decode('utf-8'))
for name, value in values.items():
    print('export ' + name + '=' + shlex.quote(value))
credential.clear()
values.clear()
