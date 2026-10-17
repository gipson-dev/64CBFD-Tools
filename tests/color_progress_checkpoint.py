"""Accept only the first exact signed-progress source and image successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_color_progress as source
from tools.experiments.game_color_progress_installation import BUILD

AFTER=dict(elf='a60f00d845f899cba20f347ad139c9d7232460d28f0e7ca8a730e2a5d16efe07',
    color_owner='334e3ca5a98e9483199d71812028c0b26fdcb4e36c014c724a499957b88ed799')
PATHS={source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data=(root/BUILD/(stage+'-'+key)).read_bytes();wanted=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest()==wanted,'Changed progress fixture: '+key
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
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected progress successor: '+key
        target=root/BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        assert fixture(root,'after',key)==data
