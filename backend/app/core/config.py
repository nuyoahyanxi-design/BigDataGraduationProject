"""Configuration from process environment only; never persist credentials."""
import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    database: str
    user: str
    password: str = field(repr=False)
    charset: str = 'utf8mb4'

    @classmethod
    def from_environment(cls):
        required = ('MYSQL_HOST', 'MYSQL_DATABASE', 'MYSQL_USER', 'MYSQL_PASSWORD')
        if any(not os.environ.get(key) for key in required):
            raise RuntimeError('Missing required MYSQL configuration variables')
        try:
            port = int(os.environ.get('MYSQL_PORT', '3306'))
        except ValueError:
            raise RuntimeError('MYSQL_PORT must be an integer') from None
        if not 1 <= port <= 65535:
            raise RuntimeError('MYSQL_PORT outside valid range')
        charset = os.environ.get('MYSQL_CHARSET', 'utf8mb4')
        if charset != 'utf8mb4':
            raise RuntimeError('MYSQL_CHARSET must be utf8mb4')
        return cls(os.environ['MYSQL_HOST'], port, os.environ['MYSQL_DATABASE'],
                   os.environ['MYSQL_USER'], os.environ['MYSQL_PASSWORD'], charset)
