"""Read-only inventory; never bind media by writing to the database."""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.core.media import video_root
from app.core.video_catalog import inspect_video, relative_video


def database_catalog():
    import pymysql
    from app.core.config import Settings
    settings = Settings.from_environment()
    conn = pymysql.connect(host=settings.host, port=settings.port, user=settings.user,
                           password=settings.password, database=settings.database,
                           charset='utf8mb4', autocommit=False,
                           cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cursor:
            cursor.execute('START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY')
            cursor.execute('SELECT id,title,status FROM resources')
            resources = cursor.fetchall()
            cursor.execute('SELECT id AS chapter_id,resource_id,title,video_url FROM course_chapters')
            chapters = cursor.fetchall()
        return {'resources': resources, 'chapters': chapters, 'source': 'mysql_read_only_snapshot'}
    finally:
        conn.rollback()
        conn.close()


def scan(root, catalog):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('Video root does not exist')
    resources = {int(row['id']): row for row in catalog['resources']}
    chapters = {int(row['chapter_id']): row for row in catalog['chapters']}
    expected = [row for row in chapters.values()
                if resources[int(row['resource_id'])]['status'] == 'published'
                and int(row['resource_id']) != 406]
    expected_paths = {relative_video(row['resource_id'], row['chapter_id']): row for row in expected}
    results = []
    anomalies = []
    for relative, row in sorted(expected_paths.items()):
        check = inspect_video(root / relative, root, checksum=True)
        results.append({'resource_id': row['resource_id'], 'chapter_id': row['chapter_id'],
                        'title': row['title'], 'stored_video_url': row['video_url'],
                        'expected_url': '/videos/' + relative, **check})
    for path in sorted(root.rglob('*')):
        if path.is_dir() or path.name in ('.gitkeep', 'README.md'):
            continue
        relative = path.relative_to(root).as_posix()
        if relative in expected_paths:
            continue
        match = re.fullmatch(r'course_([1-9][0-9]*)/chapter_([0-9]{3,})\.mp4', relative)
        reason = 'noncanonical_filename_or_format'
        if match:
            resource_id, chapter_id = map(int, match.groups())
            if relative != relative_video(resource_id, chapter_id):
                reason = 'noncanonical_id_padding'
            elif resource_id not in resources:
                reason = 'unknown_course'
            elif chapter_id not in chapters:
                reason = 'unknown_chapter'
            elif int(chapters[chapter_id]['resource_id']) != resource_id:
                reason = 'chapter_course_mismatch'
            else:
                reason = 'course_not_visible_or_published'
        anomalies.append({'file': relative, 'reason': reason})
    bound = sum(row['usable'] for row in results)
    missing = sum(row['reason'] == 'missing' for row in results)
    invalid = len(results) - bound - missing
    return {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'root': str(root),
            'catalog_source': catalog.get('source', 'offline_catalog'),
            'binding_mode': 'read_only_student_response', 'total_chapters': len(expected),
            'auto_bound': bound, 'missing': missing, 'invalid_expected_files': invalid,
            'anomalies': len(anomalies), 'playback_verified': 0,
            'validation': 'MP4 container and video handler checks; decoding not verified',
            'chapters': results, 'unexpected_files': anomalies}


def markdown(report):
    text = ['# 视频资源检查报告', '',
            f"总章节：{report['total_chapters']}", f"可自动绑定（结构检查）：{report['auto_bound']}",
            f"缺失：{report['missing']}",
            f"异常：{report['invalid_expected_files'] + report['anomalies']}",
            '真实播放验收：未执行，不以结构检查代替解码', '',
            '| 课程 | 章节 | 检查结果 | 预期URL |', '| --- | --- | --- | --- |']
    text.extend(f"| {r['resource_id']} | {r['chapter_id']} | {r['reason']} | {r['expected_url']} |"
                for r in report['chapters'])
    text += ['', '## 其他异常文件', '']
    text.extend(f"- {r['file']}：{r['reason']}" for r in report['unexpected_files'])
    return '\n'.join(text) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--catalog', type=Path, help='Offline JSON catalog; otherwise read-only MySQL')
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs' / 'course-video-scan')
    args = parser.parse_args()
    try:
        catalog = json.loads(args.catalog.read_text(encoding='utf-8-sig')) if args.catalog else database_catalog()
        report = scan(args.root or video_root(), catalog)
        args.output.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        base = args.output / ('scan-' + stamp)
        base.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        base.with_suffix('.md').write_text(markdown(report), encoding='utf-8')
        print(json.dumps({key: report[key] for key in ('total_chapters', 'auto_bound', 'missing',
                                                      'invalid_expected_files', 'anomalies')}, ensure_ascii=False))
        print('Report: ' + str(base.with_suffix('.md')))
        return 2 if report['missing'] or report['invalid_expected_files'] or report['anomalies'] else 0
    except Exception:
        print('Scan failed: verify the local directory, catalog or read-only database configuration; credentials omitted.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
