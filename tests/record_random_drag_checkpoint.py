"""Immutable predecessor/successor of the callback-6 guarded match."""
import hashlib
from pathlib import Path

from tools.experiments import game_record_random_drag as source

AFTER = {
    'elf': 'ee728f280d139c4460bae5a35f2bf8e49a3de36d7a41b313973ca17756ad07b7',
    'preset_owner': '43ef53688e7c6b7332f94524c29a3c4146474e3a3b44c41a6ed2a264e9cb90be',
    'guards': '868ebf291c1ed092b1fda8220baea72fe34a41f17c93411e714567741289b840',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    payload = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(payload).hexdigest() == expected, 'Modified random-drag fixture: ' + key
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
        assert hashlib.sha256(payload).hexdigest() == AFTER[key], 'Unexpected random-drag successor: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(payload)
        assert fixture(root, 'after', key) == payload
