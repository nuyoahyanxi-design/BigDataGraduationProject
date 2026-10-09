"""Configuration tests use disposable directories and fake credentials only."""
import importlib.util
from pathlib import Path
import subprocess
import pytest

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts' / 'local_ai_config.py'
spec = importlib.util.spec_from_file_location('local_config_test', SCRIPT)
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)
MODEL = 'agnes-3.0-flash'
KEY = 'nonsecret-test-placeholder'


def no_input(prompt):
    raise AssertionError('Interactive input should not be called')


def test_first_start_and_reuse(tmp_path, capsys):
    path = tmp_path / '.env.local'
    prompts = []
    values = config.load_config(path, {}, lambda p: prompts.append(p) or MODEL,
                                lambda p: prompts.append(p) or KEY)
    assert len(prompts) == 2 and 'hidden input' in prompts[1]
    assert values == {'AGNES_MODEL': MODEL, 'AGNES_API_KEY': KEY}
    assert path.read_text() == f'AGNES_MODEL={MODEL}\nAGNES_API_KEY={KEY}\n'
    assert config.load_config(path, {}, no_input, no_input) == values
    assert KEY not in capsys.readouterr().out


def test_environment_overrides_without_changing_file(tmp_path):
    path = tmp_path / '.env.local'
    original = f'AGNES_MODEL={MODEL}\nAGNES_API_KEY={KEY}\n'
    path.write_text(original)
    values = config.load_config(path, {'AGNES_MODEL': 'environment-model', 'AGNES_MODEL_ID': 'alias-model',
                                      'AGNES_API_KEY': 'environment-placeholder'}, no_input, no_input)
    assert values == {'AGNES_MODEL': 'environment-model', 'AGNES_API_KEY': 'environment-placeholder'}
    assert path.read_text() == original


def test_environment_only_creates_file_without_input(tmp_path):
    values = {'AGNES_MODEL_ID': MODEL, 'AGNES_API_KEY': KEY}
    path = tmp_path / '.env.local'
    assert config.load_config(path, values, no_input, no_input)['AGNES_MODEL'] == MODEL
    assert path.exists()


def test_partial_file_repaired_with_hidden_input(tmp_path):
    path = tmp_path / '.env.local'
    path.write_text(f'AGNES_MODEL={MODEL}\nAGNES_API_KEY=\n')
    config.load_config(path, {}, no_input, lambda p: KEY)
    assert config.read_local(path)['AGNES_API_KEY'] == KEY


@pytest.mark.parametrize('model,key', [('', KEY), (MODEL, ''), ('your-model-name', KEY),
                                      (MODEL, 'your-api-key-here'), ('bad/model', KEY), (MODEL, 'secret\nline')])
def test_invalid_input_never_saved(tmp_path, model, key):
    path = tmp_path / '.env.local'
    with pytest.raises(SystemExit):
        config.load_config(path, {}, lambda p: model, lambda p: key)
    assert not path.exists()


def test_invalid_file_error_does_not_echo_secret(tmp_path, capsys):
    path = tmp_path / '.env.local'
    path.write_text(f'AGNES_API_KEY={KEY}\nexport TOKEN={KEY}\n')
    with pytest.raises(SystemExit) as error:
        config.load_config(path, {}, no_input, no_input)
    assert KEY not in str(error.value) + capsys.readouterr().out


def test_cancel_does_not_save(tmp_path):
    def cancel(prompt): raise EOFError()
    with pytest.raises(SystemExit, match='cancelled'):
        config.load_config(tmp_path / '.env.local', {}, cancel, no_input)
    assert not (tmp_path / '.env.local').exists()


def test_project_git_ignore(tmp_path):
    # Test the actual ignore file in a disposable repository, never real secrets.
    root = SCRIPT.parents[1]
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    (tmp_path / '.gitignore').write_bytes((root / '.gitignore').read_bytes())
    for name in ('.env.local', '.env', '.env.local.example'):
        (tmp_path / name).write_text('placeholder-only')
    for name in ('.env.local', '.env'):
        result = subprocess.run(['git', '-C', str(tmp_path), 'check-ignore', '-q', name])
        assert result.returncode == 0
    assert subprocess.run(['git', '-C', str(tmp_path), 'check-ignore', '-q', '.env.local.example']).returncode == 1
    status = subprocess.run(['git', '-C', str(tmp_path), 'status', '--porcelain', '--untracked-files=all'],
                            check=True, capture_output=True, text=True).stdout.splitlines()
    assert '?? .env.local' not in status and '?? .env' not in status
    assert '?? .env.local.example' in status
