"""Exact-input inverse for the guarded capture-request installation."""
import hashlib
from pathlib import Path

from tools.experiments import game_capture_request_slot as source

AFTER={
    'elf':'d8f985cd62b1d83946febd871d4ecd69cf9e04056af69a829f5d6e91e720e4be',
    'request_owner':'906ccdc2252430514d32633ad18b578a9b921f01d346466fe8ac5963b7bda4bb',
    'guards':'3a3d12fba783a0085fec398e04591e898df3268bc5a708ade0d741e990553571',
}
PATHS={source.PATHS[key]:key for key in AFTER}
BUILD=source.BUILD+'/match'


def fixture(root,stage,key):
    directory=source.BUILD if stage=='before' else BUILD
    payload=(root/directory/(stage+'-'+key)).read_bytes()
    expected=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(payload).hexdigest()==expected,'Modified capture request match fixture: '+key
    return payload


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
        payload=(root/path).read_bytes()
        assert hashlib.sha256(payload).hexdigest()==AFTER[key],'Unexpected installed capture request input: '+key
        target=root/BUILD/('after-'+key)
        if not target.exists():
            target.write_bytes(payload)
        assert fixture(root,'after',key)==payload
