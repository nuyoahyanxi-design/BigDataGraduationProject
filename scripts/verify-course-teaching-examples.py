"""Execute only the authored synthetic lesson examples in an isolated local Spark."""
import contextlib
import io
import json
from pathlib import Path
from pyspark.sql import SparkSession

root = Path(__file__).resolve().parents[1]
seed = json.loads((root / 'database/seeds/course-teaching-content.json').read_text(encoding='utf-8'))
spark = SparkSession.builder.master('local[2]').appName('TeachingExampleAcceptance').config('spark.sql.shuffle.partitions', '2').getOrCreate()
spark.sparkContext.setLogLevel('ERROR')
results = []
try:
    for course in seed:
        for chapter in course['chapters']:
            output = io.StringIO()
            try:
                with contextlib.redirect_stdout(output):
                    exec(compile(chapter['example_code'], f'lesson-{chapter["position"]}', 'exec'), {'spark': spark})
                results.append({'course': course['title'], 'chapter': chapter['title'], 'passed': True,
                                'synthetic_output_characters': len(output.getvalue())})
            except Exception as error:
                results.append({'course': course['title'], 'chapter': chapter['title'], 'passed': False, 'error_type': type(error).__name__})
finally:
    spark.stop()
(root / 'outputs/course-teaching-example-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'total': len(results), 'passed': sum(item['passed'] for item in results)}))
if not all(item['passed'] for item in results): raise SystemExit(1)
