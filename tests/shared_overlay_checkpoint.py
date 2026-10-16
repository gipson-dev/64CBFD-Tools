"""Recognize only the qualified shared-overlay successor."""
import hashlib
from pathlib import Path

from tools.experiments import game_shared_overlay_pass as source

AFTER=dict(elf='5711ff13c02d9267df983aa9a23e7f47db4a6363c409dc8fde05ff1e002b4aa8',
    dispatch_owner='ef6b3c5ea8ebb03d5e6b9704e8cbc517b264773a9c97413e5a258c8e1e2d4556',
    guards='0d03d88454cbbf2b26690ca5639320bae5672b16b2beb3381854e7d75a257577')
PATHS={source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data=(root/source.BUILD/(stage+'-'+key)).read_bytes()
    expected=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest()==expected,'Changed shared-overlay fixture: '+key
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
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected shared-overlay successor: '+key
        target=root/source.BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        assert fixture(root,'after',key)==data
