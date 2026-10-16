"""Recognize only the direct scissor and plain-pattern cleanup successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_view_scissor_setup as source

AFTER=dict(elf='e55313bd3b69da1c98f17c45778811d89858dd4a72de76472341e140607a164a',
    frustum_owner='30ce53fba2c41eadc615386767884af64cc890b48ac3b18bf10e3a8ffc88ee20',
    makefile='a8f91bbdc80128b602170332dd53c435be15869bdfe9d8a059008bc4df2ee06c')
PATHS={source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data=(root/source.BUILD/(stage+'-'+key)).read_bytes()
    wanted=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest()==wanted,'Changed scissor fixture: '+key
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
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected scissor successor: '+key
        target=root/source.BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        assert fixture(root,'after',key)==data
