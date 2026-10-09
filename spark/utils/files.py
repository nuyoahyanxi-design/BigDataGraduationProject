import hashlib
import json
from pathlib import Path


def write_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    temporary.replace(path)


def parquet_files(directory):
    directory=Path(directory)
    return [{'path':str(p.relative_to(directory)),'bytes':p.stat().st_size,
             'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(directory.rglob('*.parquet'))]


def validate_hashes(directory,records):
    directory=Path(directory)
    for record in records:
        path=directory/record['path']
        if directory.resolve() not in path.resolve().parents:
            raise RuntimeError('Checksum record escapes snapshot directory')
    expected={record['path'] for record in records}
    observed={str(path.relative_to(directory)) for path in directory.rglob('*.parquet')}
    if len(expected)!=len(records) or expected!=observed:
        raise RuntimeError('Parquet snapshot file inventory mismatch')
    for record in records:
        path=directory/record['path']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:
            raise RuntimeError('Parquet snapshot checksum mismatch')
