"""Accept only the independently predicted constructor source/image successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_fixed_transition_constructor as source
from tools.experiments.game_fixed_transition_installation import BUILD

AFTER = dict(elf='9ff7f89b5a621b216a65e6018c4df1485c18cb4c4e92485bb5c94c53eb3592b4',
    tile_owner='645d71e6cf77a1f7f2940e27c983c0c79a53f0ca9d292a15d296b6bf56dcf328')
PATHS = {source.PATHS[key]:key for key in AFTER}


def fixture(root,stage,key):
    data=(Path(root)/BUILD/(stage+'-'+key)).read_bytes()
    if hashlib.sha256(data).hexdigest()!=(source.BASELINE if stage=='before' else AFTER)[key]:
        raise AssertionError('Changed transition constructor fixture: '+key)
    return data


def previous_input(current,path,root):
    relative=Path(path).as_posix(); prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix):
        relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest()==AFTER[key]:
        if fixture(root,'after',key)!=current:
            raise AssertionError('Changed transition constructor successor')
        return fixture(root,'before',key)
    return current


def freeze_after(root):
    for relative,key in PATHS.items():
        data=(root/relative).read_bytes()
        if hashlib.sha256(data).hexdigest()!=AFTER[key]:
            raise ValueError('Unexpected transition constructor successor: '+key)
        path=root/BUILD/('after-'+key)
        if not path.exists():
            path.write_bytes(data)
        if fixture(root,'after',key)!=data:
            raise ValueError('Changed transition constructor successor fixture: '+key)
