"""Recognize only the predicted setup, two callers and exact guard successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_sequence_record_setup_installation as source

AFTER = dict(elf='6f52c4154a4aca1cdecdbb5a0043d1332b89c4a928b6cb7d96354a19e43cf458',
    view_list_caller_owner='8de78d8035bd112e32b9bcd54425b86f6e7323bef06cefe686abc56f3f10fb80',
    guards='bb20ecd3785ed2e3fe949d7c9a4bfa8f6648b78e5f9eb1712af941c38faf415b',
    view_init_caller_owner='67bdf8b2ad041fbf891c8c83bf87e9b83398ac8d198dd5fec0ddd97ddc784d1b',
    scene_caller_owner='91c7ba768274a1783570e0c4b40c3080f591a865ecabbe84cf52d19cabea1b7e')
PATHS = {source.PATHS[k]:k for k in AFTER}


def fixture(root, stage, key):
    data = (root / source.BUILD / (stage + '-' + key)).read_bytes()
    wanted = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == wanted, 'Changed record setup fixture: ' + key
    return data


def previous_input(current, path, root):
    from tools.tests import sequence_event_scan_checkpoint as successor
    current = successor.previous_input(current,path,root)
    relative = Path(path).as_posix(); prefix = Path(root).as_posix() + '/'
    if relative.startswith(prefix): relative = relative[len(prefix):]
    key = PATHS.get(relative)
    if key in AFTER and hashlib.sha256(current).hexdigest() == AFTER[key]: return fixture(root, 'before', key)
    return current


def freeze_after(root):
    from tools.tests import sequence_event_scan_checkpoint as successor
    for relative, key in PATHS.items():
        data = successor.previous_input((root / relative).read_bytes(),relative,root)
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected record setup successor: ' + key
        target = root / source.BUILD / ('after-' + key)
        if not target.exists(): target.write_bytes(data)
        assert fixture(root, 'after', key) == data
