"""Exact-input successor for the directly matched actor-type preset."""
import hashlib
from pathlib import Path

from tools.experiments import game_actor_type_preset as source

AFTER = {
    'elf': 'e76ef88fa8f2d6f5442ce88c79dc512034b6cc1c6ca7d754bb6be13c321708f6',
    'preset_owner': 'cc04c9783d3a8a313ae0e2a440cb75df76c90d859c9b5f234cab10b96117bb99',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    payload = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(payload).hexdigest() == expected, 'Modified actor-preset fixture: ' + key
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
        assert hashlib.sha256(payload).hexdigest() == AFTER[key], 'Unexpected actor-preset input: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(payload)
        assert fixture(root, 'after', key) == payload
