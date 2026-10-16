"""Strict two-function projection/draw successor for the next Game recovery."""
import hashlib
from pathlib import Path

from tools.experiments import game_projected_packet_draw as source

AFTER = {
    'elf': '69c218a15ca4353aecda5233b8258f1f36da39a56b788a82375a0d7ffdb4e333',
    'packet_owner': '8228375aead0d0dafd047760f476ec09f4c6ef375af7b95bf0ac128e3ffa02ff',
    'guards': '420648a53d79abb7b62309f862d41a7fc28aa531f36663b545cefd4a55af2c60',
}
PATHS = {source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data=(root/source.BUILD/(stage+'-'+key)).read_bytes()
    expected=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest()==expected,'Changed projected-pair fixture: '+key
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
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected projected-pair successor: '+key
        target=root/source.BUILD/('after-'+key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root,'after',key)==data
