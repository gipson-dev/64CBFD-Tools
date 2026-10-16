"""Recognize only the pinned source/caller/guard/image successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_graphics_task_submit as source

AFTER = dict(elf='5ae0082dd77652314c8e63569a43439a330d133b749907fa5db2d5b76fe41d9e',
    view_list_caller_owner='3e02c9bf76ce42ee32ab9ea3be3783175a6e82472d08818797e166496c6d899d',
    dispatch_owner='de6b587a3966b174777e1d038378db6da3a918e77ba4151a3d54058185d6a012',
    guards='51b90c3096acac693bec4d4bd249154d8429c8d2045cb767c02e87318b280bb7')
PATHS = {source.PATHS[k]:k for k in ('elf', 'view_list_caller_owner', 'dispatch_owner', 'guards')}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    wanted = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == wanted, 'Changed graphics submission fixture: ' + key
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
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected graphics submission successor: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists(): target.write_bytes(data)
        assert fixture(root, 'after', key) == data
