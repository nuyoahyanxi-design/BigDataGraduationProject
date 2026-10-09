import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class MysqlSettings:
    host: str
    port: int
    database: str
    user: str
    password: str=field(repr=False)

    @classmethod
    def from_environment(cls):
        names=['MYSQL_HOST','MYSQL_DATABASE','MYSQL_USER','MYSQL_PASSWORD']
        if any(not os.environ.get(key) for key in names):
            raise RuntimeError('Missing MYSQL environment configuration')
        port=int(os.environ.get('MYSQL_PORT','3306'))
        if not 1<=port<=65535 or not re.fullmatch(r'[A-Za-z0-9.:-]+',os.environ['MYSQL_HOST']) or not re.fullmatch(r'[A-Za-z0-9_]+',os.environ['MYSQL_DATABASE']):
            raise RuntimeError('Invalid database location configuration')
        if os.environ.get('MYSQL_CHARSET','utf8mb4')!='utf8mb4':
            raise RuntimeError('MYSQL_CHARSET must be utf8mb4')
        return cls(os.environ['MYSQL_HOST'],port,os.environ['MYSQL_DATABASE'],os.environ['MYSQL_USER'],os.environ['MYSQL_PASSWORD'])


def pipeline_config():
    return json.loads((ROOT/'spark/configs/pipeline.json').read_text(encoding='utf-8'))
