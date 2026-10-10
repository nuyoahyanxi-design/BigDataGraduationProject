"""Read-only local video serving; independent of database and learning events."""
import os
import re
from pathlib import Path

from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles


DEFAULT_VIDEO_ROOT = Path(__file__).resolve().parents[3] / 'frontend' / 'public' / 'videos'


class VideoFiles(StaticFiles):
    async def get_response(self, path, scope):
        if not re.fullmatch(r'[a-zA-Z0-9_/-]+\.(mp4|webm)', path) or '..' in path:
            raise HTTPException(404)
        return await super().get_response(path, scope)


def video_root():
    root = Path(os.environ.get('COURSE_VIDEO_ROOT') or DEFAULT_VIDEO_ROOT).expanduser().resolve()
    if not root.is_dir():
        raise RuntimeError('COURSE_VIDEO_ROOT must point to an existing local video directory')
    return root


def build_video_files():
    root = video_root()
    return VideoFiles(directory=str(root), html=False, follow_symlink=False)
