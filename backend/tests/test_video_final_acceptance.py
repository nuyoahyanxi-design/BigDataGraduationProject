"""Acceptance orchestration tests; decoder output is simulated, no video generation."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parents[1] / 'tools'))
import accept_course_videos as tool
from test_video_auto_import import catalog, put


def test_empty_is_not_accepted(tmp_path):
    result = tool.accept(tmp_path, catalog())
    assert result['missing'] == 25 and result['passed'] == 0
    assert not result['accepted']


def populate(root):
    for row in catalog()['chapters']:
        put(root, row['resource_id'], row['chapter_id'])


def test_missing_decoder_fails_closed(tmp_path):
    populate(tmp_path)
    result = tool.accept(tmp_path, catalog())
    assert result['missing'] == 0 and result['passed'] == 0
    assert all(r['reason'] == 'decoder_unavailable' for r in result['chapters'])


def test_all_pass_and_duration_rejection(tmp_path, monkeypatch):
    populate(tmp_path)
    monkeypatch.setattr(tool, 'decode', lambda *a: {'passed': True, 'reason': 'decoded', 'duration_seconds': 240})
    assert tool.accept(tmp_path, catalog(), 'fake')['accepted']
    result = tool.accept(tmp_path, catalog(), 'fake', maximum=200)
    assert result['passed'] == 0 and result['anomalies'] == 25


def test_wrong_mapping_and_extra_file(tmp_path, monkeypatch):
    populate(tmp_path)
    put(tmp_path, 1069, 999)
    data = catalog()
    data['chapters'][0]['resource_id'] = 1069
    monkeypatch.setattr(tool, 'decode', lambda *a: {'passed': True, 'reason': 'decoded', 'duration_seconds': 240})
    result = tool.accept(tmp_path, data, 'fake')
    assert not result['accepted']
    assert result['chapters'][0]['reason'] == 'chapter_missing_or_wrong_course'
    assert result['unexpected_files']


def test_decode_full_command_and_failure(monkeypatch, tmp_path):
    commands = []
    def run(command, **kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=0, stdout='frame=7200\nout_time_us=240000000\nprogress=end\n')
    monkeypatch.setattr(tool.subprocess, 'run', run)
    assert tool.decode(tmp_path / 'x.mp4', 'ffmpeg', 1)['duration_seconds'] == 240
    assert '-xerror' in commands[0] and commands[0][-2:] == ['null', '-']
    monkeypatch.setattr(tool.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=1, stdout=''))
    assert tool.decode(tmp_path / 'x.mp4', 'ffmpeg', 1)['reason'] == 'decode_failed'


def test_timeout_and_file_change(tmp_path, monkeypatch):
    def timeout(*a, **k):
        raise tool.subprocess.TimeoutExpired('ffmpeg', 1)
    monkeypatch.setattr(tool.subprocess, 'run', timeout)
    assert tool.decode(tmp_path / 'x.mp4', 'ffmpeg', 1)['reason'] == 'decode_timeout'
    path = put(tmp_path)
    def changed(*args):
        path.write_bytes(path.read_bytes() + b'changed')
        return {'passed': True, 'reason': 'decoded', 'duration_seconds': 240}
    monkeypatch.setattr(tool, 'decode', changed)
    result = tool.accept(tmp_path, catalog(), 'fake')
    assert next(r for r in result['chapters'] if r['chapter_id'] == 6)['reason'] == 'file_changed_during_acceptance'
