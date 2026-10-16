"""Strict single-function packed-point transform checkpoint."""
import hashlib
from pathlib import Path

from tools.experiments import game_packed_point_transform as source

AFTER={
    'elf':'fee3933f88d705e9f424ef7ffce1d914f806bdb78a260e86cafb770bb1629796',
    'packet_owner':'57ff978c80acf2972ac16c211abf7aefc38047b947b7aeb8d67d20e92149b71b',
    'guards':'795d726ce98edecbc1b2666efec10628dfe4d0cf1621499f737ce76f3eef2aec',
}
PATHS={source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data=(root/source.BUILD/(stage+'-'+key)).read_bytes()
    expected=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest()==expected,'Changed packed-point fixture: '+key
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
    for relative,key in PATHS.items():
        data=(root/relative).read_bytes()
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected packed-point successor: '+key
        target=root/source.BUILD/('after-'+key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root,'after',key)==data
