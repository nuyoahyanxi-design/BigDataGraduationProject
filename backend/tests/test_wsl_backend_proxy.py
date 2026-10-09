import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
from wsl_backend_proxy import configure


def test_dynamic_host_and_local_exclusions():
    changes, _ = configure({'APP_ENV':'development','WINDOWS_PROXY_PORT':'7890'}, lambda:'172.28.80.1', lambda h,p: h=='172.28.80.1' and p==7890)
    assert changes['HTTPS_PROXY']=='http://172.28.80.1:7890'
    assert changes['HTTP_PROXY']==changes['HTTPS_PROXY']
    assert 'localhost' in changes['NO_PROXY']
    changed, _ = configure({'APP_ENV':'development','WINDOWS_PROXY_PORT':'7890'}, lambda:'172.30.16.1', lambda h,p:True)
    assert '172.30.16.1' in changed['HTTPS_PROXY']


def test_unreachable_listener_not_faked():
    changes, message = configure({'APP_ENV':'development','WINDOWS_PROXY_PORT':'7890'}, lambda:'172.28.80.1', lambda h,p:False)
    assert changes=={} and 'unreachable' in message


def test_no_proxy_and_production_preserved():
    assert configure({'APP_ENV':'development'})[0]=={}
    assert configure({'APP_ENV':'production','WINDOWS_PROXY_PORT':'7890'})[0]=={}


def test_explicit_proxy_and_secret_not_logged():
    env={'APP_ENV':'development','HTTPS_PROXY':'http://username:secret@proxy.invalid:8080'}
    changes,message=configure(env)
    assert changes=={} and 'secret' not in message and 'username' not in message


def test_windows_loopback_replaced_only_after_probe():
    changes,_=configure({'APP_ENV':'development','HTTPS_PROXY':'http://127.0.0.1:7890'},lambda:'172.28.80.1',lambda h,p:True)
    assert changes['HTTPS_PROXY']=='http://172.28.80.1:7890'
    changes,_=configure({'APP_ENV':'development','HTTPS_PROXY':'http://127.0.0.1:7890'},lambda:'172.28.80.1',lambda h,p:False)
    assert changes['HTTPS_PROXY']=='' and changes['HTTP_PROXY']==''
