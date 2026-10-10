"""Canonical, read-only media discovery; no ORM mutation or event writes."""
import hashlib
import os
import struct
from functools import lru_cache
from pathlib import Path

from app.core.media import video_root


def relative_video(resource_id, chapter_id):
    return f'course_{int(resource_id)}/chapter_{int(chapter_id):03d}.mp4'


def boxes(stream, start, end):
    count = 0
    while start < end:
        count += 1
        if count > 4096:
            raise ValueError('Too many boxes')
        if end - start < 8:
            raise ValueError('Truncated box')
        stream.seek(start)
        size, kind = struct.unpack('>I4s', stream.read(8))
        header = 8
        if size == 1:
            size = struct.unpack('>Q', stream.read(8))[0]
            header = 16
        elif size == 0:
            size = end - start
        if size < header or start + size > end:
            raise ValueError('Invalid box size')
        yield kind, start + header, start + size
        start += size


def has_video_track(stream, movie):
    for kind, start, end in boxes(stream, *movie):
        if kind != b'trak':
            continue
        for child, child_start, child_end in boxes(stream, start, end):
            if child != b'mdia':
                continue
            for field, field_start, field_end in boxes(stream, child_start, child_end):
                if field == b'hdlr' and field_end - field_start >= 12:
                    stream.seek(field_start + 8)
                    if stream.read(4) == b'vide':
                        return True
    return False


@lru_cache(maxsize=128)
def inspect_structure(path, size, modified_ns, changed_ns, min_bytes):
    result = {'usable': False, 'size_bytes': size, 'validation': 'mp4_structure_only',
              'playback_verified': False}
    if size < min_bytes:
        return {**result, 'reason': 'too_small'}
    if size > 2 * 1024 ** 3:
        return {**result, 'reason': 'too_large'}
    try:
        with open(path, 'rb') as stream:
            found = list(boxes(stream, 0, size))
            types = {kind for kind, _, _ in found}
            if not {b'ftyp', b'moov', b'mdat'} <= types:
                return {**result, 'reason': 'missing_mp4_boxes'}
            for kind, start, end in found:
                if kind == b'ftyp' and end - start < 8:
                    return {**result, 'reason': 'invalid_ftyp'}
            if not any(end > start for kind, start, end in found if kind == b'mdat'):
                return {**result, 'reason': 'empty_media_data'}
            if not any(has_video_track(stream, (start, end)) for kind, start, end in found if kind == b'moov'):
                return {**result, 'reason': 'no_video_track'}
        return {**result, 'usable': True, 'reason': 'structurally_valid'}
    except (OSError, ValueError, struct.error):
        return {**result, 'reason': 'invalid_mp4_structure'}


def inspect_video(path, root, checksum=False):
    path, root = Path(path), Path(root).resolve()
    try:
        resolved = path.resolve()
        if not resolved.is_relative_to(root) or path.is_symlink():
            return {'usable': False, 'reason': 'unsafe_path', 'playback_verified': False}
        if not path.is_file():
            return {'usable': False, 'reason': 'missing', 'playback_verified': False}
        if path.suffix != '.mp4':
            return {'usable': False, 'reason': 'not_mp4', 'playback_verified': False}
        stat = path.stat()
        minimum = int(os.environ.get('COURSE_VIDEO_MIN_BYTES', '1024'))
        if minimum < 1:
            raise ValueError('Invalid minimum')
        result = dict(inspect_structure(str(resolved), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, minimum))
        if checksum:
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
            result['sha256'] = digest.hexdigest()
        return result
    except (OSError, ValueError):
        return {'usable': False, 'reason': 'unreadable_or_invalid_config', 'playback_verified': False}


def discovered_url(resource_id, chapter_id, root=None):
    try:
        root = Path(root) if root is not None else video_root()
        relative = relative_video(resource_id, chapter_id)
        if inspect_video(root / relative, root)['usable']:
            return '/videos/' + relative
    except (OSError, RuntimeError):
        pass
    return None


def playback_chapter(chapter, discover=True):
    result = {column.name: getattr(chapter, column.name) for column in chapter.__table__.columns}
    url = discovered_url(chapter.resource_id, chapter.id) if discover else None
    if url:
        result.update(video_url=url, video_duration_seconds=None)
    return result
