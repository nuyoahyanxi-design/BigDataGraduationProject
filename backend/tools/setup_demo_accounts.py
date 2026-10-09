"""Local bootstrap through real auth APIs. Passwords entered by the user only."""
import argparse
import getpass
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import httpx
from sqlalchemy import select
from app.core.config import Settings
from app.database.session import build_engine, build_session_factory
from app.models import User

ROOT=Path(__file__).resolve().parents[2]
NAMES=('student_demo','admin_demo')


class SetupError(Exception):
    pass


def write_evidence(evidence):
    evidence['updated_at_utc']=datetime.now(timezone.utc).isoformat()
    path=ROOT/'outputs/demo-account-setup-evidence.json'
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temporary.replace(path)


def password_input(username):
    if not sys.stdin.isatty(): raise SetupError('Interactive terminal required; password input was not attempted')
    while True:
        first=getpass.getpass(f'{username} password (8-128 characters, hidden): ')
        second=getpass.getpass(f'{username} confirm password (hidden): ')
        if first!=second:
            print('Passwords differ. Please enter them again.'); continue
        if not 8<=len(first)<=128:
            print('Password must contain 8-128 characters.'); continue
        return first


def api(client,method,path,expected,**kwargs):
    try: response=client.request(method,path,**kwargs)
    except httpx.HTTPError: raise SetupError('Local API connection failed; no request details logged') from None
    if response.status_code!=expected:
        raise SetupError(f'API {method} {path} returned {response.status_code}; stopped without password changes')
    try: return response.json()
    except ValueError: raise SetupError('Invalid API response') from None


def identity(client,username,password):
    login=api(client,'POST','/api/auth/login',200,json={'username':username,'password':password})
    headers={'Authorization':'Bearer '+login['access_token']}
    me=api(client,'GET','/api/users/me',200,headers=headers)
    if me['username']!=username or me['status']!='active': raise SetupError('Unexpected account identity')
    return me,headers


def promote_admin(db,identity_id):
    account=db.scalar(select(User).where(User.id==identity_id).with_for_update())
    if account is None or account.username!='admin_demo' or account.status!='active' or account.role not in ('learner','admin'):
        raise SetupError('Administrator bootstrap identity guard failed')
    if account.role=='learner':
        account.role='admin'; account.updated_at=datetime.now(timezone.utc).replace(tzinfo=None)


def run(check_only=False):
    settings=Settings.from_environment()
    if settings.database!='bigdata_graduation': raise SetupError('Unexpected database; stopped')
    engine=build_engine(settings); factory=build_session_factory(engine)
    evidence={'status':'pending_user_input','accounts':{},'password_storage':'user input only; not persisted',
              'method':'real localhost HTTP register/login/me plus guarded local admin role transaction'}
    try:
        with factory() as db:
            existing={u.username:{'id':u.id,'role':u.role,'status':u.status} for u in db.scalars(select(User).where(User.username.in_(NAMES)))}
            protected=db.execute(select(User.__table__).where(User.username.startswith('dbstage_user_',autoescape=True)).order_by(User.id)).all()
        with httpx.Client(base_url='http://127.0.0.1:8000',timeout=15,follow_redirects=False,trust_env=False) as client:
            metadata=api(client,'GET','/openapi.json',200)
            if metadata.get('info',{}).get('title')!='Spark Learning Backend': raise SetupError('Unexpected backend')
            if check_only:
                print(json.dumps({'backend':'reachable','target_accounts':existing,'missing':[n for n in NAMES if n not in existing]},ensure_ascii=False))
                return
            # Collect both passwords before the first write. Nothing is randomly generated.
            write_evidence(evidence)
            passwords={name:password_input(name) for name in NAMES}
            try:
                for name in NAMES:
                    evidence['accounts'][name]={'stage':'login_pending','created_this_run':False}
                    if name not in existing:
                        registration=api(client,'POST','/api/auth/register',201,json={'username':name,'password':passwords[name],'interest_tags':['python','spark'] if name=='student_demo' else []})
                        evidence['accounts'][name].update(id=registration['id'],created_this_run=True,register_status=201)
                        write_evidence(evidence)
                    me,_=identity(client,name,passwords[name])
                    if name=='student_demo' and me['role']!='learner': raise SetupError('student_demo must be a learner')
                    if name=='admin_demo' and me['role'] not in ('learner','admin'): raise SetupError('Unexpected admin_demo role')
                    evidence['accounts'][name].update(id=me['id'],role=me['role'],status=me['status'],stage='login_verified',login_status=200,me_status=200)
                    write_evidence(evidence)
                with factory.begin() as db:
                    promote_admin(db,evidence['accounts']['admin_demo']['id'])
                for name,expected in [('student_demo',403),('admin_demo',200)]:
                    me,headers=identity(client,name,passwords[name])
                    if me['role']!=('learner' if name=='student_demo' else 'admin'): raise SetupError('Final role mismatch')
                    api(client,'GET','/api/admin/users',expected,headers=headers)
                    evidence['accounts'][name].update(role=me['role'],stage='verified',admin_endpoint_status=expected)
                with factory() as db:
                    current=db.execute(select(User.__table__).where(User.username.startswith('dbstage_user_',autoescape=True)).order_by(User.id)).all()
                    if current!=protected: raise SetupError('Protected baseline changed; manual investigation required')
                evidence.update(status='completed',dbstage_records_unchanged=True,password_hash_direct_writes=False)
                write_evidence(evidence)
                print('Completed: student_demo learner and admin_demo admin; formal login verified; old fixtures unchanged.')
            finally:
                passwords.clear()
    except Exception as error:
        evidence.update(status='incomplete',error_type=type(error).__name__)
        write_evidence(evidence)
        if isinstance(error,SetupError): print(str(error),file=sys.stderr)
        else: print('Setup stopped; inspect non-sensitive stage evidence. No credentials logged.',file=sys.stderr)
        raise SystemExit(1) from None
    finally:
        engine.dispose()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    run(args.check)
