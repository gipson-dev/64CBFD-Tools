"""Strict completed-owner successor for the next Game recovery."""
import hashlib
from pathlib import Path

from tools.experiments import game_actor_effect_dispatch as source

AFTER = {
    'elf': 'acbf49495584a4d1f9b4917596f9cbea3e5a16535ea09d183e480223c8629c44',
    'edge_wrapper_owner': '0ea4c5fbafeb1f192de22cd173a17ca82a4b5a396bc270fd923e032f0a24f2b6',
}
PATHS = {source.PATHS[k]: k for k in AFTER}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage+'-'+key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == expected, 'Changed actor-effect fixture: '+key
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
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected actor-effect successor: '+key
        target = root / source.BUILD / ('after-'+key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root, 'after', key) == data
