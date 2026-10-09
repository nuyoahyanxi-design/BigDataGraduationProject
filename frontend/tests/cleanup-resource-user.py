"""Clean only the temporary resource UI test user's learning records."""
import json
import sys
from pathlib import Path
from sqlalchemy import select, delete, func
from app.core.config import Settings
from app.database.session import build_engine
from app.models import User, Resource, LearningEvent, LearningProgress, Favorite

username = sys.argv[1]
if not username.startswith('fr_') or len(username) != 35:
    raise SystemExit('Unexpected fixture identity')
engine = build_engine(Settings.from_environment())
with engine.begin() as connection:
    user = connection.execute(select(User.id, User.role).where(User.username == username)).first()
    if user is None or user.role != 'learner':
        raise SystemExit('Fixture identity mismatch')
    models = [LearningEvent, Favorite, LearningProgress]
    counts = {model.__tablename__: connection.scalar(select(func.count()).select_from(model).where(model.user_id == user.id)) for model in models}
    for model in models:
        connection.execute(delete(model).where(model.user_id == user.id))
    connection.execute(delete(User).where(User.id == user.id, User.username == username))
    if connection.scalar(select(func.count()).select_from(User).where(User.username == username)):
        raise SystemExit('Cleanup failed')
    remaining = {model.__tablename__: connection.scalar(select(func.count()).select_from(model).where(model.user_id == user.id)) for model in models}
engine.dispose()
Path('../outputs/frontend-resource-fixture-verification.json').write_text(json.dumps({'temporary_learners': 1, 'created_resources': 0, 'test_rows_before_cleanup': counts, 'test_rows_after_cleanup': remaining, 'cleanup': 'passed'}, indent=2) + '\n')
print('Temporary learner and learning records removed')
