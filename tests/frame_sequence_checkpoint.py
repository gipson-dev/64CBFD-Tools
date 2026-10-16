"""Recognize only the qualified frame coordinator successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_frame_sequence as source

AFTER = dict(elf='c67f8312dad8796dfc0a49a2f0896639b9561b1ddd0b127fe69b6352fa7d0894',
    dispatch_owner='43c2eff427f2727668e82bfe1c70200588a500991e47abeae0af30a0471eccfa')
PATHS = {source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data = (root/source.BUILD/(stage+'-'+key)).read_bytes()
    expected = (source.BASELINE if stage == 'before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest() == expected, 'Changed frame sequence fixture: '+key
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
        assert hashlib.sha256(data).hexdigest() == AFTER[key], 'Unexpected frame sequence successor: '+key
        target = root/source.BUILD/('after-'+key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root,'after',key) == data
