"""Recognize only the first clipped-rectangle image and source successor."""
import hashlib
from pathlib import Path
from tools.experiments import game_clipped_rectangle as source
from tools.experiments.game_clipped_rectangle_installation import BUILD

AFTER=dict(elf='90fba53a4f9927a2528e5d77aee1076e1e5b05a2ab71b184f2425ec487fcaa3e',
    color_owner='9d7f84a8a678832a89a3ac29a92bcc01ba63ca7222757148ed8b799c077d91db')
PATHS={source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data=(Path(root)/BUILD/(stage+'-'+key)).read_bytes()
    if hashlib.sha256(data).hexdigest()!=(source.BASELINE if stage=='before' else AFTER)[key]:raise AssertionError('Changed rectangle fixture: '+key)
    return data


def previous_input(current,path,root):
    relative=Path(path).as_posix();prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix):relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key in AFTER and hashlib.sha256(current).hexdigest()==AFTER[key]:return fixture(root,'before',key)
    return current


def freeze_after(root):
    for relative,key in PATHS.items():
        data=(root/relative).read_bytes()
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected rectangle successor: '+key
        path=root/BUILD/('after-'+key)
        if not path.exists():path.write_bytes(data)
        assert fixture(root,'after',key)==data
