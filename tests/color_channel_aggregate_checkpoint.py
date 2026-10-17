"""Recognize only the first aggregate image/source successor and exact fixtures."""
import hashlib
from pathlib import Path

from tools.experiments import game_color_channel_aggregate as source
from tools.experiments.game_color_channel_aggregate_installation import BUILD

AFTER=dict(elf='a94062b3a07a3d0c03571a2e8e4f647d6a4ad4e9325db9309e9adc0c61862a4d',
    color_owner='f3b7927450fa6f9f6f768346eeacdac837dece59e8ff69c177d10670d4c70cf8')
PATHS={source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data=(root/BUILD/(stage+'-'+key)).read_bytes();wanted=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest()==wanted,'Changed aggregate fixture: '+key
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
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected aggregate successor: '+key
        target=root/BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        assert fixture(root,'after',key)==data
