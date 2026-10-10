"""Synthetic MP4 container fixtures, not playable videos; no MySQL connection."""
import json
import struct
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.core.video_catalog import discovered_url, inspect_video, relative_video
from app.models import Resource, CourseChapter, ChapterProgress, LearningProgress, LearningEvent, ChapterEvent, User
from app.schemas.courses import ChapterAction
from app.services import courses

# Import the read-only scanner without starting the full application.
import importlib.util
spec = importlib.util.spec_from_file_location('video_scanner', Path(__file__).parents[1] / 'tools' / 'scan_course_videos.py')
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)


def box(kind, payload):
    return struct.pack('>I4s', len(payload) + 8, kind) + payload


def structural_fixture():
    handler = box(b'hdlr', b'\0' * 8 + b'vide' + b'\0' * 8)
    movie = box(b'moov', box(b'trak', box(b'mdia', handler)))
    return box(b'ftyp', b'isom\0\0\0\0isom') + movie + box(b'mdat', b'NOT_DECODEABLE_MEDIA' * 100)


def put(root, resource_id=1069, chapter_id=6):
    path = root / relative_video(resource_id, chapter_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(structural_fixture())
    return path


def catalog():
    groups = {1068: range(1, 6), 1069: range(6, 11), 1070: range(59, 64),
              1071: range(54, 59), 1072: range(11, 16)}
    return {'resources': [{'id': rid, 'title': 'course', 'status': 'published'} for rid in groups],
            'chapters': [{'chapter_id': cid, 'resource_id': rid, 'title': 'chapter', 'video_url': '/demo/video.mp4'}
                         for rid, ids in groups.items() for cid in ids]}


def test_empty_current_25_and_future_course(tmp_path):
    before = catalog()
    report = scanner.scan(tmp_path, before)
    assert (report['total_chapters'], report['auto_bound'], report['missing'], report['anomalies']) == (25, 0, 25, 0)
    assert before == catalog()
    before['resources'].append({'id': 2000, 'title': 'future', 'status': 'published'})
    before['chapters'].append({'chapter_id': 1001, 'resource_id': 2000, 'title': 'new', 'video_url': None})
    put(tmp_path, 2000, 1001)
    report = scanner.scan(tmp_path, before)
    assert (report['total_chapters'], report['auto_bound'], report['missing']) == (26, 1, 25)


def test_all_25_rules_and_structure_not_decode(tmp_path):
    for row in catalog()['chapters']:
        put(tmp_path, row['resource_id'], row['chapter_id'])
    report = scanner.scan(tmp_path, catalog())
    assert (report['auto_bound'], report['missing'], report['anomalies']) == (25, 0, 0)
    assert report['playback_verified'] == 0
    assert all(not row['playback_verified'] and len(row['sha256']) == 64 for row in report['chapters'])


@pytest.mark.parametrize('payload,reason', [(b'', 'too_small'), (b'x' * 2048, 'invalid_mp4_structure'),
                                          (box(b'ftyp', b'isom\0\0\0\0') + box(b'mdat', b'x'*2048), 'missing_mp4_boxes')])
def test_invalid_mp4_not_bound(tmp_path, payload, reason):
    path = put(tmp_path)
    path.write_bytes(payload)
    assert inspect_video(path, tmp_path)['reason'] == reason
    assert discovered_url(1069, 6, tmp_path) is None


def test_course_chapter_ownership_and_naming(tmp_path):
    put(tmp_path, 9999, 6)
    put(tmp_path, 1069, 9999)
    put(tmp_path, 1069, 1)
    path = tmp_path / 'course_1069' / 'chapter_0006.mp4'
    path.write_bytes(structural_fixture())
    reasons = {r['reason'] for r in scanner.scan(tmp_path, catalog())['unexpected_files']}
    assert reasons == {'unknown_course', 'unknown_chapter', 'chapter_course_mismatch', 'noncanonical_id_padding'}


def test_escape_and_replacement(tmp_path):
    root = tmp_path / 'videos'; root.mkdir()
    outside = tmp_path / 'private.mp4'; outside.write_bytes(structural_fixture())
    path = root / relative_video(1069, 6); path.parent.mkdir(); path.symlink_to(outside)
    assert inspect_video(path, root)['reason'] == 'unsafe_path'
    path.unlink(); path.write_bytes(structural_fixture())
    assert discovered_url(1069, 6, root)
    path.write_bytes(b'bad')
    assert discovered_url(1069, 6, root) is None


class ReadDB:
    def __init__(self, chapter):
        self.chapter = chapter
        self.resource = Resource(id=1069, title='course', content='text', status='published')
        self.reads = iter([[chapter], []])
    def get(self, model, identity):
        return self.resource if model is Resource else None
    def scalars(self, query):
        class Rows(list):
            def all(self): return list(self)
        return Rows(next(self.reads))


def test_student_read_mapping_admin_edit_preserved(tmp_path, monkeypatch):
    monkeypatch.setenv('COURSE_VIDEO_ROOT', str(tmp_path))
    chapter = CourseChapter(id=6, resource_id=1069, title='chapter', position=1,
                            video_url='/demo/video.mp4', video_duration_seconds=999)
    original = chapter.video_url
    assert courses.read_course(ReadDB(chapter), 1069, SimpleNamespace(id=1, role='learner'))['chapters'][0]['video_url'] == original
    put(tmp_path)
    response = courses.read_course(ReadDB(chapter), 1069, SimpleNamespace(id=1, role='learner'))['chapters'][0]
    assert response['video_url'] == '/videos/course_1069/chapter_006.mp4'
    assert response['video_duration_seconds'] is None
    assert chapter.video_url == original and chapter.video_duration_seconds == 999
    assert courses.read_course(ReadDB(chapter), 1069, SimpleNamespace(id=1, role='admin'))['chapters'][0]['video_url'] == original


class ActionDB:
    """Session adapter for unchanged transaction/event routines; no database writes."""
    def __init__(self, chapter, total=2, completed=0, existing=None):
        self.added = []
        stamp = courses.learning.event_time()
        user = User(id=1, role='learner', status='active')
        resource = Resource(id=1069, status='published', version_no=2)
        self.responses = iter([user, existing, resource, total, completed])
        self.progress = LearningProgress(user_id=1, resource_id=1069, status='in_progress', updated_at=stamp)
        self.cp = ChapterProgress(user_id=1, chapter_id=6, first_started_at=stamp)
        self.chapter = chapter
    def scalar(self, query): return next(self.responses)
    def get(self, model, identity):
        return {CourseChapter: self.chapter, LearningProgress: self.progress, ChapterProgress: self.cp}[model]
    def add(self, obj): self.added.append(obj)
    def flush(self): pass
    def rollback(self): pass
    def commit(self): pass


def test_unstored_auto_video_play_and_completion_semantics(tmp_path, monkeypatch):
    monkeypatch.setenv('COURSE_VIDEO_ROOT', str(tmp_path)); put(tmp_path)
    chapter = CourseChapter(id=6, resource_id=1069, video_url=None)
    db = ActionDB(chapter)
    payload = ChapterAction(event_uuid=uuid4(), event_type='video_play', playback_seconds=3.5)
    result = courses.act(db, 1, 1069, 6, payload, courses.learning.event_time())
    assert result['event_type'] == 'video_play' and not result['chapter_completed']
    assert db.cp.completed_at is None and db.progress.status == 'in_progress'
    assert [type(row) for row in db.added] == [ChapterEvent]
    assert db.added[0].playback_seconds == 3.5
    replay = ActionDB(chapter, existing=db.added[0])
    assert courses.act(replay, 1, 1069, 6, payload, courses.learning.event_time()) == result
    assert replay.added == []
    complete = ActionDB(chapter, total=1, completed=1)
    receipt = courses.act(complete, 1, 1069, 6, ChapterAction(event_uuid=uuid4(), event_type='chapter_complete'), courses.learning.event_time())
    assert receipt['chapter_completed'] and receipt['course_status'] == 'completed'
    bridge = next(row for row in complete.added if isinstance(row, LearningEvent))
    assert bridge.event_type == 'learning_complete' and UUID(bridge.event_uuid).version == 5


def test_no_file_with_null_url_still_rejects_play(tmp_path, monkeypatch):
    monkeypatch.setenv('COURSE_VIDEO_ROOT', str(tmp_path))
    chapter = CourseChapter(id=6, resource_id=1069, video_url=None)
    db = ActionDB(chapter)
    with pytest.raises(HTTPException) as failure:
        courses.act(db, 1, 1069, 6, ChapterAction(event_uuid=uuid4(), event_type='video_play'), courses.learning.event_time())
    assert failure.value.status_code == 409 and db.added == []


def test_first_chapter_browsing_keeps_start_bridge(tmp_path, monkeypatch):
    monkeypatch.setenv('COURSE_VIDEO_ROOT', str(tmp_path))
    chapter = CourseChapter(id=6, resource_id=1069, video_url='/demo/video.mp4')
    db = ActionDB(chapter)
    db.progress = None
    db.cp = None
    receipt = courses.act(db, 1, 1069, 6, ChapterAction(event_uuid=uuid4(), event_type='chapter_view'), courses.learning.event_time())
    bridge = next(row for row in db.added if isinstance(row, LearningEvent))
    assert bridge.event_type == 'learning_start' and UUID(bridge.event_uuid).version == 5
    assert not receipt['chapter_completed']
    assert next(row for row in db.added if isinstance(row, ChapterEvent)).event_type == 'chapter_view'
