"""Recognize only the qualified scheduler frame-driver successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_frame_driver as source

AFTER=dict(elf='65e765cc9fdd7ae385522f739f4e4c8acc4d15b9a894ed68e0a968253eccf48a',
    dispatch_owner='759db490285d4b5ea0eaa9ed68fadcfe20401b9ab6b7e38b932deefd077fe8ed',
    guards='afb6b1c22543a1d74a309185ca4fe2978614bb43b1e288a4f7e844b4912a14ca')
PATHS={source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data=(root/source.BUILD/(stage+'-'+key)).read_bytes()
    expected=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest()==expected,'Changed frame driver fixture: '+key
    return data


def previous_input(current,path,root):
    relative=Path(path).as_posix()
    prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix):relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest()==AFTER[key]:return fixture(root,'before',key)
    return current


def freeze_after(root):
    for relative,key in PATHS.items():
        data=(root/relative).read_bytes()
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected frame driver successor: '+key
        target=root/source.BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        assert fixture(root,'after',key)==data
