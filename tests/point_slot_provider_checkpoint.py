"""Recognize only the qualified point-slot provider successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_point_slot_provider as source

AFTER = {
    'elf': '931955c4a1beee4e093894ea1cb87602f7177a1dc064165aafd28159ae2390fa',
    'packet_owner': 'd6e245b869f60915b84d4a7c22da60dbe96f018635238aea7bde6bc8929897c3',
    'guards': '6d409b75d30f2d5d7db243a5220aaa97011ed8a59054445693761ed1f25df465',
}
PATHS = {source.PATHS[k]:k for k in AFTER}


def fixture(root, stage, key):
    data = (root/source.BUILD/(stage+'-'+key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == expected, 'Changed point-slot fixture: '+key
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
    for relative, key in PATHS.items():
        data = (root/relative).read_bytes()
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected point-slot successor: '+key
        target = root/source.BUILD/('after-'+key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root, 'after', key) == data
