"""Exact-input inverse of the qualified pending-view queue installation."""
import hashlib
from pathlib import Path

from tools.experiments import game_view_pending_queue as source

AFTER = {
    'elf': '307dae852b172a633730646ad73f4b406274b853a1ca86a7487b2ccfdc1721b7',
    'owner': '659475afe8ecfb244117e32317c4414964d3015db90794f62eff9d9b6682101c',
    'guards': '6e4e9e1850ceec25de5a319001682796fe19da44f494eb070bbbe08cad793576',
}
PATHS = {source.PATHS[key]: key for key in AFTER}


def fixture(root, stage, key):
    data = (root/source.BUILD/(stage+'-'+key)).read_bytes()
    digest = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == digest, 'Modified pending queue fixture: '+key
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
        data = (root/path).read_bytes()
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected installed pending queue input: '+key
        target = root/source.BUILD/('after-'+key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root, 'after', key) == data
