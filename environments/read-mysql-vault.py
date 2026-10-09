"""Private IPC helper: callers must capture stdout and never log it."""
import json
import sys
sys.path.insert(0, r'D:\BigDataGraduationProject\environments\mysql-admin-tools')
from keyring.backends.Windows import WinVaultKeyring
password = WinVaultKeyring().get_password('BigDataGraduationProject/MySQL', 'bigdata_dev')
if password is None:
    sys.exit(2)
print(json.dumps({'password': password}))
