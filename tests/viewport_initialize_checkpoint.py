"""Only the pinned direct viewport initializer is an accepted successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_viewport_initialize_lifetimes as source

AFTER = dict(elf='1e37e75c0cd1215a3e8a2fc9ae4c0b9ed38a56d59a6b5e2d1c5ef03334632096',
    frustum_owner='67b0a4150c68cdea5ffb076231703f799925d0955a7e5fc6f2eabfefc852fff3')
PATHS = {source.PATHS[k]:k for k in ('elf', 'frustum_owner')}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    wanted = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == wanted, 'Changed viewport initializer fixture: ' + key
    return data


def previous_input(current, path, root):
    relative = Path(path).as_posix(); prefix = Path(root).as_posix() + '/'
    if relative.startswith(prefix): relative = relative[len(prefix):]
    key = PATHS.get(relative)
    if key in AFTER and hashlib.sha256(current).hexdigest() == AFTER[key]: return fixture(root, 'before', key)
    return current


def freeze_after(root):
    for relative, key in PATHS.items():
        data = (root / relative).read_bytes()
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected viewport initializer successor: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists(): target.write_bytes(data)
        assert fixture(root, 'after', key) == data
