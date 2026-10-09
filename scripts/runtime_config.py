"""Load non-secret runtime policy without shell evaluation or credential access."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('APP_ENV', 'AI_ALLOWED_RESOURCE_IDS')


def load_runtime(path=None, environ=None):
    path = Path(path) if path is not None else ROOT/'configs/runtime.local.env'
    environ = os.environ if environ is None else environ
    local = {}
    if path.exists():
        try:
            for line in path.read_text(encoding='utf-8-sig').splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                name, separator, value = line.partition('=')
                name = name.strip()
                if not separator or name not in NAMES or name in local:
                    raise ValueError()
                local[name] = value.strip()
        except (ValueError, OSError, UnicodeError):
            raise SystemExit('Invalid configs/runtime.local.env; only APP_ENV and AI_ALLOWED_RESOURCE_IDS are allowed.') from None
    for name, default in [('APP_ENV', 'production'), ('AI_ALLOWED_RESOURCE_IDS', '')]:
        environ.setdefault(name, local.get(name, default))
    return {name: environ[name] for name in NAMES}
