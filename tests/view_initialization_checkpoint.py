"""Recognize only the measured view initializer and eight-guard successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_view_initialization as source

AFTER = dict(elf='c25f1fbae94e8c9b8d29e63636728c7d0b5fdb46028ab3549edd44fea03632b2',
    frustum_owner='69db5ff05c0681c0630ddf75b7796811e33771e59dea087469000a85df227d03',
    guards='3da8509dd73834cbbce061e4ba26f5341bd9140ea073241083e5d078c9dbd02e')
PATHS = {source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data=(root/source.BUILD/(stage+'-'+key)).read_bytes()
    wanted=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest()==wanted,'Changed view-initialization fixture: '+key
    return data


def previous_input(current,path,root):
    relative=Path(path).as_posix();prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix):relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest()==AFTER[key]:return fixture(root,'before',key)
    return current


def freeze_after(root):
    for relative,key in PATHS.items():
        data=(root/relative).read_bytes()
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected view-initialization successor: '+key
        target=root/source.BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        assert fixture(root,'after',key)==data
