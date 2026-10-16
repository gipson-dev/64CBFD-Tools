"""Recognize only the direct point-projection source/image successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_view_point_projection as source

AFTER = dict(elf='23d5ee08fc033c461872a1e3382969e6cd5587791ff3b4108c1350c08c9962cf',
    frustum_owner='6caa0dcc8c1ceaac1b96be30cbbc3d3f50dbc7ae61445c24641a81f036a0a61b')
PATHS = {source.PATHS[k]:k for k in AFTER}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    wanted = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == wanted, 'Changed point-projection fixture: ' + key
    return data


def previous_input(current, path, root):
    relative = Path(path).as_posix(); prefix = Path(root).as_posix() + '/'
    if relative.startswith(prefix): relative = relative[len(prefix):]
    key = PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest() == AFTER[key]: return fixture(root, 'before', key)
    return current


def freeze_after(root):
    for relative, key in PATHS.items():
        data = (root / relative).read_bytes()
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected point-projection successor: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists(): target.write_bytes(data)
        assert fixture(root, 'after', key) == data
