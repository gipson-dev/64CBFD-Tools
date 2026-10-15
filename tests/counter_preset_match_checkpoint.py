"""Exact-input successor for the guarded counter-preset match."""
import hashlib
from pathlib import Path

from tools.experiments import game_counter_preset_match as source

AFTER = {
    'elf': 'f518dfd60ad98bd67a7eb72b5b92f29178586f207c0bf8b97656853b6f62b863',
    'preset_owner': 'ebe9a969fed7f6c9221332825d93709d2c70c0f8ce541c585161b5fe06738059',
    'guards': '2a06a351699d625848c5022a68442a34333fc2f67c24409bd5fc465f38c996ff',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    payload = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(payload).hexdigest() == expected, 'Modified counter-match fixture: ' + key
    return payload


def previous_input(current, path, root):
    relative = Path(path).as_posix()
    prefix = Path(root).as_posix() + '/'
    if relative.startswith(prefix):
        relative = relative[len(prefix):]
    key = PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest() == AFTER[key]:
        return fixture(root, 'before', key)
    return current


def freeze_after(root):
    for path, key in PATHS.items():
        payload = (root / path).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == AFTER[key], 'Unexpected counter-match input: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(payload)
        assert fixture(root, 'after', key) == payload
