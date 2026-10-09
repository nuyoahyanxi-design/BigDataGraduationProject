"""Development-only process proxy discovery. Never changes listeners/firewall."""
import ipaddress
import os
import shlex
import socket
import subprocess
import sys
from urllib.parse import urlsplit

from runtime_config import load_runtime


def host_address():
    try:
        mode = subprocess.check_output(['wslinfo', '--networking-mode'], text=True).strip()
        if mode == 'mirrored':
            return '127.0.0.1'
    except (OSError, subprocess.SubprocessError):
        pass
    route = subprocess.check_output(['ip', '-4', 'route', 'show', 'default'], text=True)
    words = route.split()
    return str(ipaddress.ip_address(words[words.index('via')+1]))


def reachable(host, port):
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


def configure(environ, host_fn=host_address, probe=reachable):
    if environ.get('APP_ENV', 'production') != 'development':
        return {}, 'Production: automatic local proxy discovery disabled.'
    explicit = environ.get('HTTPS_PROXY') or environ.get('https_proxy') or environ.get('HTTP_PROXY') or environ.get('http_proxy')
    if explicit:
        parsed = urlsplit(explicit)
        if parsed.username or parsed.password or parsed.scheme not in ('http', 'https') or not parsed.hostname:
            return {}, 'Explicit proxy retained; automatic discovery skipped.'
        if parsed.hostname not in ('localhost', '127.0.0.1', '::1'):
            return {}, 'Explicit process proxy retained.'
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        scheme = parsed.scheme
    else:
        try:
            port = int(environ.get('WINDOWS_PROXY_PORT', '0'))
        except ValueError:
            return {}, 'Invalid Windows proxy port; no proxy was changed.'
        scheme = 'http'
    if not 1 <= port <= 65535:
        return {}, 'No Windows proxy detected; original no-proxy startup retained.'
    try:
        host = host_fn()
        if not probe(host, port):
            changes = {name:'' for name in ('HTTP_PROXY','HTTPS_PROXY','http_proxy','https_proxy')} if explicit else {}
            return changes, 'Windows host proxy is unreachable from WSL; unusable inherited loopback proxy disabled for this process. A loopback-only listener cannot serve the WSL host address.'
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return {}, 'Cannot discover WSL host; proxy not changed.'
    proxy = f'{scheme}://{host}:{port}'
    exclusions = [v.strip() for v in (environ.get('NO_PROXY') or environ.get('no_proxy') or '').split(',') if v.strip()]
    exclusions += ['localhost', '127.0.0.1', '::1', host]
    exclusions = ','.join(dict.fromkeys(exclusions))
    return {'HTTP_PROXY':proxy, 'HTTPS_PROXY':proxy, 'http_proxy':proxy, 'https_proxy':proxy,
            'NO_PROXY':exclusions, 'no_proxy':exclusions}, 'Reachable Windows host proxy configured for this backend process.'


if __name__ == '__main__':
    load_runtime()
    changes, message = configure(os.environ)
    print(message, file=sys.stderr)
    for name, value in changes.items():
        print(f'export {name}={shlex.quote(value)}')
