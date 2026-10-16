"""Recognize only the measured unguarded view-overlay successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_view_overlay_pass as source

AFTER=dict(elf='132fce9cd5b0394cc37ad6909381a5ddf06f95407054387f8270a1060c77b131',
    dispatch_owner='fb6e0f93f93502e9fdcfdaf5e441a6e9492d684cf93ef7e51c66b8ccdc123c11')
PATHS={source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data=(root/source.BUILD/(stage+'-'+key)).read_bytes()
    expected=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest()==expected,'Changed view-overlay fixture: '+key
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
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected view-overlay successor: '+key
        target=root/source.BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        assert fixture(root,'after',key)==data
