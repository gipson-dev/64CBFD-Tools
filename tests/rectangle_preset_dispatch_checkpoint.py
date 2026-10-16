"""Strict rectangle-dispatch source and complete linked-image successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_rectangle_preset_dispatch as source

AFTER = {
    'elf': '5877233ddf6a78bc55b80b102f47d8736e8678351e5937e3ba1b3e77066a8533',
    'edge_wrapper_owner': '7a985b3eadfe194efac55d5b42f0401cbb09e6694d6e05936f6bf20bae3fec08',
}
PATHS = {source.PATHS[k]: k for k in AFTER}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage+'-'+key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == expected, 'Changed rectangle-dispatch fixture: '+key
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
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected rectangle-dispatch successor: '+key
        target = root / source.BUILD / ('after-'+key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root, 'after', key) == data
