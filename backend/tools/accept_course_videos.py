"""Read-only final acceptance for the frozen five-course video release."""
import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from scan_course_videos import ROOT, database_catalog, scan, video_root

BASELINE = {1068: list(range(1, 6)), 1069: list(range(6, 11)),
            1070: list(range(59, 64)), 1071: list(range(54, 59)),
            1072: list(range(11, 16))}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def decode(path, executable, timeout):
    if not executable:
        return {'passed': False, 'reason': 'decoder_unavailable'}
    try:
        result = subprocess.run([str(executable), '-nostdin', '-hide_banner', '-v', 'error',
                                 '-xerror', '-err_detect', 'explode', '-i', str(path),
                                 '-map', '0:v:0', '-map', '0:a?', '-progress', 'pipe:1',
                                 '-f', 'null', '-'], capture_output=True, text=True,
                                errors='replace', timeout=timeout)
        times = [int(value) / 1_000_000 for value in
                 re.findall(r'^out_time_us=(\d+)$', result.stdout, re.MULTILINE)]
        duration = max(times, default=0)
        frames = [int(value) for value in re.findall(r'^frame=(\d+)$', result.stdout, re.MULTILINE)]
        passed = (result.returncode == 0 and 'progress=end' in result.stdout
                  and duration > 0 and max(frames, default=0) > 0)
        return {'passed': passed, 'reason': 'decoded' if passed else 'decode_failed',
                'duration_seconds': duration, 'decoded_frames': max(frames, default=0),
                'exit_code': result.returncode}
    except subprocess.TimeoutExpired:
        return {'passed': False, 'reason': 'decode_timeout'}
    except OSError:
        return {'passed': False, 'reason': 'decoder_unavailable'}


def accept(root, catalog, executable=None, minimum=180, maximum=300, timeout=1800):
    root = Path(root).resolve()
    inventory = scan(root, catalog)
    resources = {int(r['id']): r for r in catalog['resources']}
    chapters = {int(r['chapter_id']): r for r in catalog['chapters']}
    checks = {(int(r['resource_id']), int(r['chapter_id'])): r for r in inventory['chapters']}
    issues, rows = [], []
    for course_id, chapter_ids in BASELINE.items():
        course = resources.get(course_id)
        if not course or course['status'] != 'published':
            issues.append({'course_id': course_id, 'reason': 'course_missing_or_unpublished'})
        if not (root / f'course_{course_id}').is_dir():
            issues.append({'course_id': course_id, 'reason': 'course_directory_missing'})
        for chapter_id in chapter_ids:
            relative = f'course_{course_id}/chapter_{chapter_id:03d}.mp4'
            row = {'course_id': course_id, 'chapter_id': chapter_id, 'file': relative,
                   'expected_url': '/videos/' + relative, 'passed': False}
            chapter = chapters.get(chapter_id)
            if not chapter or int(chapter['resource_id']) != course_id:
                row['reason'] = 'chapter_missing_or_wrong_course'
            elif (course_id, chapter_id) not in checks:
                row['reason'] = 'course_not_in_published_catalog'
            else:
                check = checks[(course_id, chapter_id)]
                row.update({key: check[key] for key in ('reason', 'sha256', 'size_bytes') if key in check})
                if check['usable']:
                    path = root / relative
                    before = path.stat()
                    decoded = decode(path, executable, timeout)
                    row['decode'] = decoded
                    row['reason'] = decoded['reason']
                    if decoded['passed']:
                        duration = decoded['duration_seconds']
                        row['passed'] = math.isfinite(duration) and minimum <= duration <= maximum
                        row['reason'] = 'passed' if row['passed'] else 'duration_out_of_range'
                    after = path.stat()
                    if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                            after.st_size, after.st_mtime_ns, after.st_ctime_ns) or sha256(path) != check['sha256']:
                        row.update(passed=False, reason='file_changed_during_acceptance')
            rows.append(row)
    missing = sum(row['reason'] == 'missing' for row in rows)
    passed = sum(row['passed'] for row in rows)
    anomalies = len(rows) - missing - passed + len(issues) + inventory['anomalies']
    return {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'root': str(root),
            'catalog_source': catalog.get('source', 'offline_catalog'),
            'total_courses': 5, 'total_chapters': 25,
            'video_count': sum(1 for p in root.rglob('*') if p.is_file() and p.suffix.lower() == '.mp4'),
            'missing': missing, 'anomalies': anomalies, 'passed': passed,
            'accepted': passed == 25 and anomalies == 0,
            'duration_range_seconds': [minimum, maximum], 'decoder': str(executable) if executable else None,
            'anomaly_count_definition': 'failed non-missing chapters plus course/directory issues plus unexpected files',
            'chapters': rows, 'catalog_and_directory_issues': issues,
            'unexpected_files': inventory['unexpected_files']}


def markdown(report):
    lines = ['# AI课程视频正式验收报告', '',
             f"验收结论：{'通过' if report['accepted'] else '未通过'}", '',
             f"总课程数：{report['total_courses']}", f"总章节数：{report['total_chapters']}",
             f"视频总数：{report['video_count']}", f"缺失数量：{report['missing']}",
             f"异常数量：{report['anomalies']}", f"通过数量：{report['passed']}", '',
             '异常数量包含章节失败、课程/目录问题及额外文件，可能大于章节数。',
             '只读规则映射与完整解码检查；教学内容、浏览器兼容和事件写入需另行人工验收。', '',
             '| 课程 | 章节 | 结果 | 解码时长（秒） |', '| --- | --- | --- | --- |']
    lines += [f"| {r['course_id']} | {r['chapter_id']} | {r['reason']} | {r.get('decode', {}).get('duration_seconds', '')} |" for r in report['chapters']]
    lines += ['', '## 课程与目录异常', '', json.dumps(report['catalog_and_directory_issues'], ensure_ascii=False),
              '', '## 额外文件异常', '', json.dumps(report['unexpected_files'], ensure_ascii=False)]
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--catalog', type=Path)
    parser.add_argument('--ffmpeg', type=Path)
    parser.add_argument('--min-seconds', type=float, default=180)
    parser.add_argument('--max-seconds', type=float, default=300)
    parser.add_argument('--timeout', type=float, default=1800)
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs' / 'course-video-acceptance')
    args = parser.parse_args()
    try:
        if not (0 < args.min_seconds <= args.max_seconds < math.inf and 0 < args.timeout < math.inf):
            raise ValueError('Invalid limits')
        catalog = json.loads(args.catalog.read_text(encoding='utf-8-sig')) if args.catalog else database_catalog()
        report = accept(args.root or video_root(), catalog, args.ffmpeg or shutil.which('ffmpeg'),
                        args.min_seconds, args.max_seconds, args.timeout)
        args.output.mkdir(parents=True, exist_ok=True)
        base = args.output / ('acceptance-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        files = [base.with_suffix('.json'), base.with_suffix('.md')]
        files[0].write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        files[1].write_text(markdown(report), encoding='utf-8')
        base.with_suffix('.sha256').write_text('\n'.join(f'{sha256(p)}  {p.name}' for p in files) + '\n', encoding='utf-8')
        print(json.dumps({k: report[k] for k in ('total_courses', 'total_chapters', 'video_count', 'missing', 'anomalies', 'passed', 'accepted')}, ensure_ascii=False))
        print('Report: ' + str(files[1]))
        return 0 if report['accepted'] else 2
    except Exception:
        print('Acceptance failed: check directory, catalog, decoder and read-only connection; credentials omitted.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
