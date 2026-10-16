"""Strict extent/lifetime fitting checkpoint; 71 retail words remain different."""
import hashlib
from pathlib import Path

from tools.experiments import game_packet_rectangle_fitting as source

AFTER={
    'elf':'cfa4611d4151c21bc820ea5a16ec2bfcf91d0daf897259469a8a314a0e80791f',
    'packet_owner':'b145ca1b2ddd80f63ae8ea7113cf738e0758d7cf0fbc69a399622d39ed6ef90b',
}
PATHS={source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data=(root/source.BUILD/(stage+'-'+key)).read_bytes()
    expected=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest()==expected,'Changed rectangle-fitting fixture: '+key
    return data


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
        data=(root/path).read_bytes()
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected rectangle-fitting successor: '+key
        target=root/source.BUILD/('after-'+key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root,'after',key)==data
