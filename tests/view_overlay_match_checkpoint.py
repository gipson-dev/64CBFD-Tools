"""Recognize only the complete guarded view-overlay match successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_view_overlay_match as source

AFTER=dict(elf='088cddcb3aaf1085034a492241d590ed1542344da71d608ec5a7c510937330a0',
    dispatch_owner='bc4ea6e920cb471bdc9d17f336deffa4d0a464ca66c50920379e2c2b329428e9',
    guards='e09a6696c524fad38b6c2cbefdb4c8249e012efdd59b6a14cc51ac5958939239')
PATHS={source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data=(root/source.BUILD/(stage+'-'+key)).read_bytes()
    expected=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest()==expected,'Changed view-overlay match fixture: '+key
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
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected view-overlay match successor: '+key
        target=root/source.BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        assert fixture(root,'after',key)==data
