"""Recognize only the first predicted reset/source/caller/guard image successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_sequence_state_reset as source

AFTER = dict(elf='17e327a95fcf43c50ac2611a19461980ad1d44664a3c3a218d593f35e26cd4ab',
    view_list_caller_owner='98dd8f293ebdd3b47ced8a41c093f4ce5665bd3341fdf351699ebb37a22c0045',
    view_init_caller_owner='b4dc09551e47e04e7f9fc80430b953050a0ccd74d899ab14e4bb3edb6e361e9a',
    guards='2e182911b8f362b3dc5fcf8e690b2fdb3d69ea2aa9ce0c459beb95bbcad79302')
PATHS = {source.PATHS[k]:k for k in AFTER}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    wanted = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == wanted, 'Changed sequence reset fixture: ' + key
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
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected sequence reset successor: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists(): target.write_bytes(data)
        assert fixture(root, 'after', key) == data
