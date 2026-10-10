"""HTTP byte fixtures only; no playable media or database writes."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.media import build_video_files


@pytest.fixture
def client(tmp_path, monkeypatch):
    root = tmp_path / 'videos'
    course = root / 'course_1069'
    course.mkdir(parents=True)
    (course / 'chapter_006.mp4').write_bytes(b'HTTP byte fixture, not a generated video')
    (root / 'README.md').write_text('not public media')
    outside = tmp_path / 'private.mp4'
    outside.write_bytes(b'outside media root')
    (root / 'escape.mp4').symlink_to(outside)
    monkeypatch.setenv('COURSE_VIDEO_ROOT', str(root))
    app = FastAPI()
    app.mount('/videos', build_video_files())
    @app.get('/api/check')
    def check():
        return {'ok': True}
    with TestClient(app) as transport:
        yield transport


def test_local_media_and_api(client):
    response = client.get('/videos/course_1069/chapter_006.mp4')
    assert response.status_code == 200
    assert response.headers['content-type'] == 'video/mp4'
    assert response.content == b'HTTP byte fixture, not a generated video'
    assert client.head('/videos/course_1069/chapter_006.mp4').content == b''
    assert client.get('/api/check').json() == {'ok': True}


def test_range_and_missing(client):
    response = client.get('/videos/course_1069/chapter_006.mp4', headers={'Range': 'bytes=0-3'})
    assert response.status_code == 206
    assert response.content == b'HTTP'
    assert response.headers['content-range'].startswith('bytes 0-3/')
    assert client.get('/videos/course_1069/chapter_007.mp4').status_code == 404


@pytest.mark.parametrize('path', ['README.md', 'escape.mp4', '%2e%2e/private.mp4', 'course_1069/chapter_006.mp4/extra'])
def test_only_safe_media_files(client, path):
    assert client.get('/videos/' + path).status_code == 404


def test_invalid_config_fails(tmp_path, monkeypatch):
    monkeypatch.setenv('COURSE_VIDEO_ROOT', str(tmp_path / 'missing'))
    with pytest.raises(RuntimeError, match='COURSE_VIDEO_ROOT'):
        build_video_files()
