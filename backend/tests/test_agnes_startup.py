"""Exercise launcher without sockets, backend startup, DB, or real credentials."""
import os
from pathlib import Path
import runpy
import pytest

LAUNCHER = Path(__file__).resolve().parents[2] / 'outputs' / 'start-ai-real-model-secure.py'
run_launcher = runpy.run_path


@pytest.mark.parametrize('model,key', [
    ('agnes-3.0-flash', 'nonsecret-test-placeholder'),
    (None, None), (None, 'nonsecret-test-placeholder'), ('agnes-3.0-flash', None),
    ('  ', '  '),
    (' agnes-3.0-flash ', ' nonsecret-test-placeholder '),
])
def test_environment_first_or_hidden_input(monkeypatch, capsys, tmp_path, model, key):
    monkeypatch.setenv('APP_ENV','production')
    monkeypatch.setenv('AI_ALLOWED_RESOURCE_IDS','')
    monkeypatch.syspath_prepend(str(LAUNCHER.parents[1] / 'scripts'))
    import local_ai_config
    monkeypatch.setattr(local_ai_config, 'ROOT', tmp_path)
    for name, value in [('AGNES_MODEL_ID', model), ('AGNES_API_KEY', key)]:
        if value is None:
            monkeypatch.setenv(name, '')  # Track original absence for restoration.
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    # Ensure the legacy variable cannot mask the new requested input path.
    monkeypatch.delenv('AGNES_MODEL', raising=False)
    for name in ('AI_ASSISTANT_ENABLED', 'AGNES_BASE_URL'):
        monkeypatch.setenv(name, 'placeholder')  # Restore launcher changes after test.
    calls = []
    def model_input(prompt):
        calls.append(('model', prompt))
        return 'agnes-3.0-flash'
    def key_input(prompt):
        calls.append(('hidden-key', prompt))
        return 'nonsecret-test-placeholder'
    monkeypatch.setattr('builtins.input', model_input)
    monkeypatch.setattr('getpass.getpass', key_input)
    class FreeSocket:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def settimeout(self, value): pass
        def connect_ex(self, address): return 1
    monkeypatch.setattr('socket.socket', lambda: FreeSocket())
    started = []
    monkeypatch.setattr(runpy, 'run_path', lambda path, **kwargs: started.append(Path(path).name))
    run_launcher(str(LAUNCHER), run_name='__main__')
    assert [name for name, _ in calls] == (
        ([] if model and model.strip() else ['model']) + ([] if key and key.strip() else ['hidden-key']))
    assert all('model ID' in prompt if name == 'model' else 'hidden input' in prompt for name, prompt in calls)
    assert os.environ['AGNES_MODEL'] == 'agnes-3.0-flash'
    assert os.environ['AGNES_API_KEY'] == 'nonsecret-test-placeholder'
    assert os.environ['AI_ASSISTANT_ENABLED'] == 'true'
    assert started == ['start-real-browser-precheck-backend.py']
    assert 'nonsecret-test-placeholder' not in capsys.readouterr().out


def test_missing_input_aborts_without_start_or_secret_output(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv('APP_ENV','production')
    monkeypatch.setenv('AI_ALLOWED_RESOURCE_IDS','')
    monkeypatch.syspath_prepend(str(LAUNCHER.parents[1] / 'scripts'))
    import local_ai_config
    monkeypatch.setattr(local_ai_config, 'ROOT', tmp_path)
    monkeypatch.delenv('AGNES_MODEL', raising=False)
    monkeypatch.delenv('AGNES_MODEL_ID', raising=False)
    monkeypatch.delenv('AGNES_API_KEY', raising=False)
    monkeypatch.setattr('builtins.input', lambda prompt: '')
    monkeypatch.setattr('getpass.getpass', lambda prompt: '')
    started = []
    monkeypatch.setattr(runpy, 'run_path', lambda *args, **kwargs: started.append(True))
    with pytest.raises(SystemExit, match='Missing model or key'):
        run_launcher(str(LAUNCHER), run_name='__main__')
    assert not started and not (tmp_path / '.env.local').exists()
    assert 'AGNES_API_KEY' in capsys.readouterr().out
