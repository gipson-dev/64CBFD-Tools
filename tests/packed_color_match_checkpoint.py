"""Exact-input successor for the qualified packed RGB callback installation."""
import hashlib
from pathlib import Path

from tools.experiments import game_packed_color_match as source

AFTER = {
    'elf': '66f7281e1f839b43c2987ed1fbca4e28a4044936b4544e3df1589023ba7741b3',
    'preset_owner': '1b4d3bb3ee8990540c119fd51a1145e93efe95eac53cfa588a93b646d5fe0b9d',
    'guards': '2b2d5139c4d138257f5e0c4ce2d169a2f248aa00d524261167fe8a38ccd9a978',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    payload = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(payload).hexdigest() == expected, 'Modified packed-color fixture: ' + key
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
        assert hashlib.sha256(payload).hexdigest() == AFTER[key], 'Unexpected packed-color input: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists():
            target.write_bytes(payload)
        assert fixture(root, 'after', key) == payload
