import importlib.util
from pathlib import Path
import pytest
from app.core.ai_config import AISettings

spec=importlib.util.spec_from_file_location('runtime_config_tests',Path(__file__).resolve().parents[2]/'scripts/runtime_config.py')
runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)


@pytest.mark.parametrize('environment,ids,allowed,wildcard',[
    ('development','*',[1,1071,123456],True),
    ('production','1071,1072',[1071,1072],False),
    ('development','1071',[1071],False),
    ('production','',[],False),('development','',[],False),
])
def test_resource_policy(monkeypatch,environment,ids,allowed,wildcard):
    monkeypatch.setenv('AI_ASSISTANT_ENABLED','true');monkeypatch.setenv('APP_ENV',environment)
    monkeypatch.setenv('AI_ALLOWED_RESOURCE_IDS',ids)
    settings=AISettings.from_environment()
    assert settings.allow_all_resources==wildcard
    assert all(settings.allows_resource(i) for i in allowed)
    if not wildcard:assert not settings.allows_resource(99999)


@pytest.mark.parametrize('environment,ids',[('production','*'),('staging','*'),('development','*,1071'),
                                         ('production','-1'),('production','18446744073709551616')])
def test_invalid_policy_fail_closed(monkeypatch,environment,ids):
    monkeypatch.setenv('AI_ASSISTANT_ENABLED','true');monkeypatch.setenv('APP_ENV',environment)
    monkeypatch.setenv('AI_ALLOWED_RESOURCE_IDS',ids)
    with pytest.raises(RuntimeError,match='configuration unavailable'):AISettings.from_environment()


def test_unspecified_environment_is_production(monkeypatch):
    monkeypatch.setenv('AI_ASSISTANT_ENABLED','true');monkeypatch.delenv('APP_ENV',raising=False)
    monkeypatch.setenv('AI_ALLOWED_RESOURCE_IDS','*')
    with pytest.raises(RuntimeError):AISettings.from_environment()


def test_runtime_local_file_and_environment_override(tmp_path):
    path=tmp_path/'runtime.local.env';path.write_text('APP_ENV=development\nAI_ALLOWED_RESOURCE_IDS=*\n')
    assert runtime.load_runtime(path,{})=={'APP_ENV':'development','AI_ALLOWED_RESOURCE_IDS':'*'}
    env={'APP_ENV':'production','AI_ALLOWED_RESOURCE_IDS':'1071'}
    assert runtime.load_runtime(path,env)==env


def test_missing_runtime_file_is_default_deny(tmp_path):
    assert runtime.load_runtime(tmp_path/'absent',{})=={'APP_ENV':'production','AI_ALLOWED_RESOURCE_IDS':''}


def test_runtime_rejects_unrelated_or_executable_fields(tmp_path):
    path=tmp_path/'bad';path.write_text('AGNES_API_KEY=placeholder\n')
    with pytest.raises(SystemExit):runtime.load_runtime(path,{})


def test_empty_environment_whitelist_is_not_overridden(tmp_path):
    path=tmp_path/'policy';path.write_text('APP_ENV=development\nAI_ALLOWED_RESOURCE_IDS=*\n')
    assert runtime.load_runtime(path,{'AI_ALLOWED_RESOURCE_IDS':''})['AI_ALLOWED_RESOURCE_IDS']==''


@pytest.mark.parametrize('environment,user,global_limit', [('production',20,100),('development',100,1000)])
def test_quota_environment_defaults(monkeypatch,environment,user,global_limit):
    monkeypatch.setenv('AI_ASSISTANT_ENABLED','true');monkeypatch.setenv('APP_ENV',environment)
    monkeypatch.setenv('AI_ALLOWED_RESOURCE_IDS','')
    for name in ('AI_USER_DAILY_REQUEST_LIMIT','AI_GLOBAL_DAILY_REQUEST_LIMIT'):monkeypatch.delenv(name,raising=False)
    settings=AISettings.from_environment()
    assert (settings.user_limit,settings.global_limit,settings.concurrency)==(user,global_limit,2)


def test_explicit_development_quota_stays_authoritative(monkeypatch):
    monkeypatch.setenv('AI_ASSISTANT_ENABLED','true');monkeypatch.setenv('APP_ENV','development')
    monkeypatch.setenv('AI_ALLOWED_RESOURCE_IDS','*');monkeypatch.setenv('AI_USER_DAILY_REQUEST_LIMIT','3')
    monkeypatch.setenv('AI_GLOBAL_DAILY_REQUEST_LIMIT','7')
    settings=AISettings.from_environment();assert (settings.user_limit,settings.global_limit)==(3,7)
