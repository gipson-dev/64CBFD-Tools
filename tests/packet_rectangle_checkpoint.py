"""Strict semantic checkpoint; func_15095D34 still needs retail word matching."""
import hashlib
from pathlib import Path

from tools.experiments import game_packet_rectangle as source

AFTER={
    'elf':'05c247fb22b1ef93a931bf8dc4068a334c19ab6b4b1ea1fc64f6ea3befde655c',
    'packet_owner':'d80e8a78be87de9517c88eef652832e843c37d0dd5091f0b43a0be25bf24b357',
}
PATHS={source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data=(root/source.BUILD/(stage+'-'+key)).read_bytes()
    expected=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest()==expected,'Changed packet-rectangle fixture: '+key
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
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected packet-rectangle successor: '+key
        target=root/source.BUILD/('after-'+key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root,'after',key)==data
