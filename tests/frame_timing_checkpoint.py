"""Recognize only the measured unguarded frame-timing successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_frame_timing_update as source

AFTER=dict(elf='44fa0f9f11ce36d6aad05a9214d8b025c687e54bb6dbf9e857386e2f47f3ebd3',
    dispatch_owner='d4884ed725cb96ba56e9a19ab0cb060682e527963579983a45b299a3e9383416')
PATHS={source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data=(root/source.BUILD/(stage+'-'+key)).read_bytes()
    expected=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest()==expected,'Changed frame-timing fixture: '+key
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
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected frame-timing successor: '+key
        target=root/source.BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        assert fixture(root,'after',key)==data
