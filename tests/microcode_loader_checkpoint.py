"""Recognize only the first predicted microcode-loader source/guard/image successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_microcode_loader as source

BUILD = 'conker/build/game-microcode-loader-installation'
AFTER = dict(elf='d32f3bfa87f40838eccd6a087afbaf0e199c438932cf5cd56703b6bf22315a89',
    view_list_caller_owner='04b1a7d3944b4bc2874524b9f9e1833a28fad5356dd926aca64688c7db031431',
    guards='a66f4a4c85152fb6c8629c16b44fc8ee9272d0a39324c6e8c1373cbba8df50b5')
PATHS = {source.PATHS[k]:k for k in ('elf', 'view_list_caller_owner', 'guards')}


def fixture(root, stage, key):
    data = (root / BUILD / (stage + '-' + key)).read_bytes()
    wanted = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == wanted, 'Changed microcode loader fixture: ' + key
    return data


def previous_input(current, path, root):
    from tools.tests import record_maximum_checkpoint as successor
    current = successor.previous_input(current, path, root)
    relative = Path(path).as_posix(); prefix = Path(root).as_posix() + '/'
    if relative.startswith(prefix): relative = relative[len(prefix):]
    key = PATHS.get(relative)
    if key in AFTER and hashlib.sha256(current).hexdigest() == AFTER[key]: return fixture(root, 'before', key)
    return current


def freeze_after(root):
    from tools.tests import record_maximum_checkpoint as successor
    for relative, key in PATHS.items():
        data = successor.previous_input((root / relative).read_bytes(), relative, root)
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected microcode loader successor: ' + key
        target = root / BUILD / ('after-' + key)
        if not target.exists(): target.write_bytes(data)
        assert fixture(root, 'after', key) == data
