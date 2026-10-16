"""Strict inner-flag-capture checkpoint; 18 retail words remain different."""
import hashlib
from pathlib import Path

from tools.experiments import game_packet_rectangle_flip_capture as source

AFTER={
    'elf':'8b0b0f94df971019ca6b5123825abf9fcd7d180a76f9572d705b67ae28e6353b',
    'packet_owner':'b440f70a5dbec0f68e036ee2fc181f4b77fd50b3cd32cae894389cd4e1bdc90d',
}
PATHS={source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data=(root/source.BUILD/(stage+'-'+key)).read_bytes()
    expected=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest()==expected,'Changed rectangle-capture fixture: '+key
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
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected rectangle-capture successor: '+key
        target=root/source.BUILD/('after-'+key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root,'after',key)==data
