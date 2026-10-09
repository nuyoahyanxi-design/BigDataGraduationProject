"""WSL developer launcher: loads signing key privately from Windows vault."""
import os
import subprocess
import sys

if not os.environ.get('JWT_SECRET'):
    command = '''import sys,secrets
sys.path.insert(0,r'D:\\BigDataGraduationProject\\environments\\mysql-admin-tools')
from keyring.backends.Windows import WinVaultKeyring
vault=WinVaultKeyring()
key=vault.get_password('BigDataGraduationProject/JWT','backend')
if key is None:
    key=secrets.token_urlsafe(48)
    vault.set_password('BigDataGraduationProject/JWT','backend',key)
print(key)
'''
    result=subprocess.run(['/mnt/c/Program Files/Python312/python.exe','-c',command],
                          capture_output=True,text=True)
    if result.returncode or not result.stdout.strip():
        raise SystemExit('JWT credential loading failed; check Windows Credential Manager')
    os.environ['JWT_SECRET']=result.stdout.strip()
    del result

if __name__=='__main__':
    import uvicorn
    uvicorn.run('app.main:app',host='127.0.0.1',port=8000)
