"""Strict four-counter successor for subsequent Game recoveries."""
import hashlib
from pathlib import Path

from tools.experiments import game_four_byte_saturation as source

AFTER = {
    'elf': '1186370e78964af1417bcdf165ab7d24a41f9d8e02fd3fffcbda1e1c63c412de',
    'preset_owner': 'eaae6546b8b83a9791e64029926f2d54dbc386fce1f1cc5d2fa39bbe55229358',
}
PATHS = {source.PATHS[k]: k for k in AFTER}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage+'-'+key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == expected, 'Changed four-counter fixture: '+key
    return data


def previous_input(current, path, root):
    relative = Path(path).as_posix()
    prefix = Path(root).as_posix()+'/'
    if relative.startswith(prefix):
        relative = relative[len(prefix):]
    key = PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest() == AFTER[key]:
        return fixture(root, 'before', key)
    return current


def freeze_after(root):
    for path, key in PATHS.items():
        data = (root / path).read_bytes()
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected four-counter successor: '+key
        target = root / source.BUILD / ('after-'+key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root, 'after', key) == data
