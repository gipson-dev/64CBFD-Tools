"""Exact-input inverse of the matrix pass and original product restoration."""
import hashlib
from pathlib import Path

from tools.experiments import game_view_matrix_pass as source

AFTER={
    'elf':'2131709f14152d266636cf97c684b5d71225c547b32d126c2024bcb7e93696a0',
    'owner':'4296bc1df7c67483fc8cdb6dab3704b722b25cc395e7a2bffd990a1d4d4b47c1',
    'multiply_owner':'68fb4b7b0106aa77100dfdbc354871c48b4944462d657e61122168d5b6496f38',
    'guards':'93812256a8a182bd882a3fe1012a8019929537c3031b28d4c8eb1dc8ffd467dc',
    'progress':'3ad7466c067bdb27e92248b8b237fb3dff392097ef3cd5d9a337d8268fbda091',
}
ASSEMBLY='52b23fa885eac1ccc956d01c4f75c0d2a316b59e5539a82aa0bc3c26248c90aa'
PATHS={source.PATHS[key]:key for key in AFTER}


def fixture(root,stage,key):
    data=(root/source.BUILD/(stage+'-'+key)).read_bytes()
    digest=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest()==digest,'Modified matrix pass fixture: '+key
    return data


def check_assembly(root):
    assert hashlib.sha256((root/source.ASSEMBLY).read_bytes()).hexdigest()==ASSEMBLY,\
        'Unexpected installed matrix product assembly'


def previous_input(current,path,root):
    relative=Path(path).as_posix()
    prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix):
        relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest()==AFTER[key]:
        check_assembly(root)
        return fixture(root,'before',key)
    return current


def freeze_after(root):
    check_assembly(root)
    for path,key in PATHS.items():
        data=(root/path).read_bytes()
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected installed matrix pass input: '+key
        target=root/source.BUILD/('after-'+key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root,'after',key)==data
