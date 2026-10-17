"""Accept only the independently predicted overlay-reset source/image successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_overlay_defaults as source
from tools.experiments.game_overlay_defaults_installation import BUILD

AFTER = dict(elf='1d600586b847f1c38aaf0c7a8f62bc8c3465542601c754447be48f6ecac41519',
    color_owner='f2bd090d216aa39c0a553b3cab3e1d8d18eb26263dc2620a4daf6ade8c045e14')
PATHS = {source.PATHS[k]:k for k in AFTER}


def fixture(root, stage, key):
    data = (Path(root)/BUILD/(stage+'-'+key)).read_bytes()
    if hashlib.sha256(data).hexdigest() != (source.BASELINE if stage == 'before' else AFTER)[key]:
        raise AssertionError('Changed overlay reset fixture: '+key)
    return data


def previous_input(current, path, root):
    from tools.tests import scrolling_tile_checkpoint as installed
    current = installed.previous_input(current,path,root)
    relative = Path(path).as_posix()
    prefix = Path(root).as_posix()+'/'
    if relative.startswith(prefix):
        relative = relative[len(prefix):]
    key = PATHS.get(relative)
    if key in AFTER and hashlib.sha256(current).hexdigest() == AFTER[key]:
        return fixture(root, 'before', key)
    return current


def freeze_after(root):
    for relative, key in PATHS.items():
        data = (root/relative).read_bytes()
        from tools.tests import scrolling_tile_checkpoint as installed
        data = installed.previous_input(data,relative,root)
        if hashlib.sha256(data).hexdigest() != AFTER[key]:
            raise ValueError('Unexpected overlay reset successor: '+key)
        path = root/BUILD/('after-'+key)
        if not path.exists():
            path.write_bytes(data)
        if fixture(root, 'after', key) != data:
            raise ValueError('Changed overlay reset successor fixture: '+key)
