import os
import secrets

# Ephemeral test signing key in memory; never persist or print it.
os.environ.setdefault('JWT_SECRET', secrets.token_urlsafe(48))


class SafeTestContext(dict):
    def __repr__(self):
        return '<test context: credentials redacted>'

# Existing database integration fixtures use direct API credentials; guarded flows
# are exercised with captcha_required=True in isolated auth-experience tests.
os.environ.setdefault('AUTH_CAPTCHA_REQUIRED', 'false')
