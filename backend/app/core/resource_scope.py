"""Pure resource policy shared with offline processing. No database writes."""
HIDDEN_IDS=frozenset({406})
VALIDATION_SOURCE='本项目测试'
VALIDATION_LICENSE='仅供开发验收'
SCOPE_RULE='formal-course-v1: published, not hidden/validation, has chapters'
SCOPE_LABEL='正式课程'

def visible_metadata(resource):
    return resource.id not in HIDDEN_IDS and not (resource.source_name==VALIDATION_SOURCE and resource.license_note==VALIDATION_LICENSE)
