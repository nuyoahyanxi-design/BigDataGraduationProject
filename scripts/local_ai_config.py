"""Local launcher configuration. Never log credentials or evaluate dotenv text."""
import getpass
import os
import re
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('AGNES_MODEL', 'AGNES_API_KEY')


def read_local(path):
    if not path.exists():
        return {}
    try:
        lines = path.read_text(encoding='utf-8-sig').splitlines()
    except (OSError, UnicodeError):
        raise SystemExit('Cannot read .env.local; check file access and UTF-8 encoding.') from None
    values = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        name, separator, value = line.partition('=')
        if not separator or name.strip() not in NAMES or name.strip() in values:
            raise SystemExit('Invalid .env.local format; use unique AGNES_MODEL and AGNES_API_KEY lines.')
        values[name.strip()] = value.strip()
    return values


def validate(values):
    model, key = values['AGNES_MODEL'], values['AGNES_API_KEY']
    if not model or not key:
        raise SystemExit('Missing model or key: AGNES_MODEL and AGNES_API_KEY must not be empty.')
    if not re.fullmatch(r'[a-z0-9._-]{1,100}', model) or model == 'your-model-name':
        raise SystemExit('Invalid AGNES_MODEL; enter the actual provider model ID.')
    if any(ord(c) < 33 or ord(c) == 127 for c in key) or len(key) > 4096 or key in ('your-api-key', 'your-api-key-here'):
        raise SystemExit('Invalid AGNES_API_KEY; use a nonempty single-line provider Key, not a template value.')


def load_config(path=None, environ=None, prompt=None, secret_prompt=None):
    path = Path(path) if path is not None else ROOT / '.env.local'
    if path.is_symlink():
        raise SystemExit('Refusing a symlink .env.local; use a local regular file.')
    environ = os.environ if environ is None else environ
    prompt = input if prompt is None else prompt
    secret_prompt = getpass.getpass if secret_prompt is None else secret_prompt
    exists = path.exists()
    local = read_local(path)
    values = {
        'AGNES_MODEL': (environ.get('AGNES_MODEL', '').strip() or environ.get('AGNES_MODEL_ID', '').strip() or local.get('AGNES_MODEL', '')),
        'AGNES_API_KEY': (environ.get('AGNES_API_KEY', '').strip() or local.get('AGNES_API_KEY', '')),
    }
    if not exists:
        print('.env.local not found. First-time configuration; missing values will be requested securely.')
    for name in NAMES:
        if not values[name]:
            print(f'{name} is empty or missing; input is required.')
            try:
                values[name] = (prompt('Agnes text model ID (AGNES_MODEL): ') if name == 'AGNES_MODEL'
                                else secret_prompt('Agnes API Key (hidden input): ')).strip()
            except (EOFError, KeyboardInterrupt):
                raise SystemExit('Configuration cancelled; no credentials saved.') from None
    validate(values)
    # Preserve existing local values, even when overridden by environment variables.
    saved = {name: local.get(name) or values[name] for name in NAMES}
    validate(saved)
    if not exists or saved != local:
        try:
            # Only repair missing local fields; never rewrite populated fields from env.
            text = ''.join(f'{name}={saved[name]}\n' for name in NAMES)
            if exists:
                fd, temp_name = tempfile.mkstemp(prefix='.agnes-config-', suffix='.tmp', dir=path.parent)
                try:
                    with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as file:
                        file.write(text)
                    os.replace(temp_name, path)
                finally:
                    if os.path.exists(temp_name):
                        os.unlink(temp_name)
            else:
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as file:
                    file.write(text)
        except OSError:
            raise SystemExit('Cannot save .env.local; check local directory permissions. No backend started.') from None
        print('Local configuration saved to .env.local (Git ignored). Key is not displayed.')
    else:
        print('Configuration loaded from environment/local file; no interactive input required.')
    return values


if __name__ == '__main__':
    load_config()
