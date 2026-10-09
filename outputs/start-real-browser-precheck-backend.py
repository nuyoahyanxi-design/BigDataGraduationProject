"""Start the existing service with read-only credential retrieval."""
import os
import subprocess
from pathlib import Path
if not os.environ.get('JWT_SECRET'):
    source="""import sys
sys.path.insert(0,r'D:\BigDataGraduationProject\environments\mysql-admin-tools')
from keyring.backends.Windows import WinVaultKeyring
value=WinVaultKeyring().get_password('BigDataGraduationProject/JWT','backend')
if value is None: raise SystemExit(2)
print(value)
"""
    result=subprocess.run(['/mnt/c/Program Files/Python312/python.exe','-c',source],capture_output=True,text=True)
    if result.returncode or not result.stdout.strip(): raise SystemExit('Existing JWT credential unavailable; no credential was created')
    os.environ['JWT_SECRET']=result.stdout.strip()
    del result
os.chdir(Path(__file__).resolve().parents[1]/'backend')
import uvicorn
uvicorn.run('app.main:app',host='127.0.0.1',port=8000)
