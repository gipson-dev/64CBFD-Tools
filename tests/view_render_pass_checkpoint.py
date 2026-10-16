"""Recognize only the qualified 215-word view-render successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_view_render_pass as source

AFTER=dict(elf='9ae138139ba63fab29b532ad2aa3c4303447629661226f9e7b375ba4b5018ef4',
    dispatch_owner='b43d27b1ad8040f7d91c92153377b687dac0884cbb3b0975d6d14390b5fcb248',
    guards='0ecf98bd9a0098f3bc8b40ecdbf069b7f801f26b0dc326b1c5f5d098bbac23f3')
PATHS={source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data=(root/source.BUILD/(stage+'-'+key)).read_bytes()
    expected=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest()==expected,'Changed view-render fixture: '+key
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
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected view-render successor: '+key
        target=root/source.BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        assert fixture(root,'after',key)==data
