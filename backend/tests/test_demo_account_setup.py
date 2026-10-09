from types import SimpleNamespace
import httpx
import pytest
from tools import setup_demo_accounts as setup


def test_admin_role_guard_changes_only_role_and_timestamp():
    row=SimpleNamespace(id=10,username='admin_demo',status='active',role='learner',updated_at=None,password_hash=object())
    old_hash=row.password_hash
    setup.promote_admin(SimpleNamespace(scalar=lambda statement:row),10)
    assert row.role=='admin' and row.updated_at is not None and row.password_hash is old_hash


@pytest.mark.parametrize('username,status',[('dbstage_user_0','active'),('student_demo','active'),('admin_demo','disabled')])
def test_unrelated_or_disabled_accounts_cannot_be_promoted(username,status):
    row=SimpleNamespace(username=username,status=status,role='learner')
    with pytest.raises(setup.SetupError): setup.promote_admin(SimpleNamespace(scalar=lambda statement:row),10)
    assert row.role=='learner'


def test_noninteractive_input_never_falls_back_to_echo(monkeypatch):
    monkeypatch.setattr(setup.sys,'stdin',SimpleNamespace(isatty=lambda:False))
    with pytest.raises(setup.SetupError,match='Interactive'): setup.password_input('student_demo')


def test_api_error_does_not_expose_response_body():
    with httpx.Client(base_url='http://127.0.0.1:8000',transport=httpx.MockTransport(lambda request:httpx.Response(409,json={'detail':'sensitive-response-placeholder'}))) as client:
        with pytest.raises(setup.SetupError) as error: setup.api(client,'POST','/api/auth/register',201)
    assert '409' in str(error.value) and 'sensitive-response-placeholder' not in str(error.value)
