"""Only the independently predicted scrolling-tile source/image successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_scrolling_tile_windows as source
from tools.experiments.game_scrolling_tile_installation import BUILD

AFTER = dict(elf='db9a07f4e5fc3278dfbb357c401fe5d314653f40b41bced82425a32a8c3ba58c',
    tile_owner='d4862cd0a6f2803bbdc8da758cbde092ed8e437846b96532fc55f09d1e66b21f')
PATHS = {source.PATHS[key]:key for key in AFTER}


def fixture(root,stage,key):
    data = (Path(root)/BUILD/(stage+'-'+key)).read_bytes()
    if hashlib.sha256(data).hexdigest()!=(source.BASELINE if stage=='before' else AFTER)[key]:
        raise AssertionError('Changed scrolling tile fixture: '+key)
    return data


def previous_input(current,path,root):
    relative = Path(path).as_posix()
    prefix = Path(root).as_posix()+'/'
    if relative.startswith(prefix):
        relative = relative[len(prefix):]
    key = PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest()==AFTER[key]:
        if fixture(root,'after',key)!=current:
            raise AssertionError('Changed scrolling tile successor')
        return fixture(root,'before',key)
    return current


def freeze_after(root):
    for relative,key in PATHS.items():
        data = (root/relative).read_bytes()
        if hashlib.sha256(data).hexdigest()!=AFTER[key]:
            raise ValueError('Unexpected scrolling tile successor: '+key)
        path = root/BUILD/('after-'+key)
        if not path.exists():
            path.write_bytes(data)
        if fixture(root,'after',key)!=data:
            raise ValueError('Changed scrolling tile successor fixture: '+key)
