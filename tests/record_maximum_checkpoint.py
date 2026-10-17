"""Recognize only the first predicted record-maximum source/guard/image successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_record_maximum_scan as source

AFTER = dict(elf='15a46ab59454790f0c2685d986f38d7ee5193ebc4d4dc7b9b987c439a15e6245',
    view_list_caller_owner='acf2dfaa4a818c738e557f33015211331bfc9b7a497a7771ec8c443b63e5e9c0',
    guards='9c2663db21c4bc173b12fe41b5d6d17346d7d5edd785531232fbb2c8babb8572')
PATHS = {source.PATHS[k]:k for k in AFTER}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    wanted = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == wanted, 'Changed record maximum fixture: ' + key
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
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected record maximum successor: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists(): target.write_bytes(data)
        assert fixture(root, 'after', key) == data
