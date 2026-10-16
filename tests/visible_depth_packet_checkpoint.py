"""Strict visible-depth successor for the next bounded Game recovery."""
import hashlib
from pathlib import Path

from tools.experiments import game_visible_depth_packet as source

AFTER={
    'elf':'0896a6bb14a5780fe6c88d04cd7ece72fa460336afa8d4dbd3f739af0d079f66',
    'packet_owner':'ea844704626b560ae270459e7bee5469474d0f50c3c9c09a67e3094f5a409aea',
    'guards':'e41413f066e143b17c98ae0254dbec2f1419d8e3479d332ec3d278a73603bc90',
}
PATHS={source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data=(root/source.BUILD/(stage+'-'+key)).read_bytes()
    expected=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest()==expected,'Changed visible-depth fixture: '+key
    return data


def previous_input(current,path,root):
    relative=Path(path).as_posix()
    prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix):
        relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest()==AFTER[key]:
        return fixture(root,'before',key)
    return current


def freeze_after(root):
    for path,key in PATHS.items():
        data=(root/path).read_bytes()
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected visible-depth successor: '+key
        target=root/source.BUILD/('after-'+key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root,'after',key)==data
