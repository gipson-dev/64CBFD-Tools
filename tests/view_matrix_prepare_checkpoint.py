"""Recognize only the directly matched matrix-preparation successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_view_matrix_prepare as source

AFTER = dict(elf='c0f62994f2c5778483cbc1159b7972694b2bdc5431874ddaf8339e27c185a628',
    packet_owner='ee0b950eea15592bcbf9f9ecb7d4c449156d072959cbf3a807409bdf692b22ab')
PATHS = {source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data = (root/source.BUILD/(stage+'-'+key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == expected, 'Changed matrix preparation fixture: '+key
    return data


def previous_input(current,path,root):
    relative = Path(path).as_posix()
    prefix = Path(root).as_posix()+'/'
    if relative.startswith(prefix):
        relative = relative[len(prefix):]
    key = PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest() == AFTER[key]:
        return fixture(root,'before',key)
    return current


def freeze_after(root):
    for relative,key in PATHS.items():
        data = (root/relative).read_bytes()
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected matrix preparation successor: '+key
        target = root/source.BUILD/('after-'+key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root,'after',key) == data
