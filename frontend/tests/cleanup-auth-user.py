"""Remove only the temporary frontend-auth learner created by the test API."""
import sys
from sqlalchemy import select, delete
from app.core.config import Settings
from app.database.session import build_engine
from app.models import User

username = sys.argv[1]
if not username.startswith('fa_') or len(username) != 35:
    raise SystemExit('Unexpected fixture identity')
engine = build_engine(Settings.from_environment())
with engine.begin() as connection:
    user = connection.execute(select(User.id, User.role).where(User.username == username)).first()
    if user is not None:
        if user.role != 'learner':
            raise SystemExit('Fixture role mismatch')
        connection.execute(delete(User).where(User.id == user.id, User.username == username))
    remaining = connection.execute(select(User.id).where(User.username == username)).first()
    if remaining is not None:
        raise SystemExit('Fixture cleanup failed')
engine.dispose()
print('Temporary frontend-auth learner removed')
