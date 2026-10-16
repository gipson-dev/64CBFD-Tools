"""Strict packet-visibility successor for later Game matching work."""
import hashlib
from pathlib import Path

from tools.experiments import game_packet_visibility as source

AFTER={
    'elf':'a7e8634c178f315ca4b42dabb3c4d348b84101cfa7d338e7c6de44ac6e4bdc51',
    'packet_owner':'6e9a02f95eabb630214749833ad581a47a7a823ba0259362abd56fe6abf866f8',
    'guards':'197a60801a08f0db3ed2afa2461b3d692bd215cf21f78870609589fb06df9c41',
}
PATHS={source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data=(root/source.BUILD/(stage+'-'+key)).read_bytes()
    expected=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest()==expected,'Changed packet-visibility fixture: '+key
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
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected packet-visibility successor: '+key
        target=root/source.BUILD/('after-'+key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root,'after',key)==data
