"""Exact-input successor for the packed fade/scale callback's three changed inputs."""
import hashlib
from pathlib import Path

from tools.experiments import game_packed_record_scale as source

AFTER = {
    'elf': '3cda1ab024db3e37886dd08677ad6adfca63b2bdcee416a41de4f794f3e87615',
    'preset_owner': 'e36a92072fa2bbbfde29af0110c8bc2206848dc803569e40927656ac49a98eb1',
    'guards': 'e48ca462691e03b724b1dfae8542e4a592826157a755bd4dcc62851a00830491',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    payload = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(payload).hexdigest() == expected, 'Modified packed-scale fixture: ' + key
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
        assert hashlib.sha256(payload).hexdigest() == AFTER[key], 'Unexpected packed-scale input: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(payload)
        assert fixture(root, 'after', key) == payload
