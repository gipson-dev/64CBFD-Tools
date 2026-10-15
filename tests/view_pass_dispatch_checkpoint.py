"""Exact-input inverse of the direct selected-view render-pass checkpoint."""
import hashlib
from pathlib import Path

from tools.experiments import game_view_pass_dispatch as source

AFTER={
    'elf':'f3a09d0a11e36aceab1f2124653c63091ef14d4033c4953e983bbeb014397e75',
    'dispatch_owner':'ab29cb86056b155f135ca77b1735613c8f694904def3e215e7dad9d37744e597',
}
PATHS={source.PATHS[key]:key for key in AFTER}


def fixture(root,stage,key):
    payload=(root/source.BUILD/(stage+'-'+key)).read_bytes()
    expected=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(payload).hexdigest()==expected,'Modified view dispatch fixture: '+key
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
        assert hashlib.sha256(payload).hexdigest()==AFTER[key],'Unexpected installed view dispatch input: '+key
        target=root/source.BUILD/('after-'+key)
        if not target.exists():
            target.write_bytes(payload)
        assert fixture(root,'after',key)==payload
