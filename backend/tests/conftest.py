import os
import secrets

# Ephemeral test signing key in memory; never persist or print it.
os.environ.setdefault('JWT_SECRET', secrets.token_urlsafe(48))


class SafeTestContext(dict):
    def __repr__(self):
        return '<test context: credentials redacted>'
