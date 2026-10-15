"""Exact-input inverse of the two qualified clipping-command installations."""
import hashlib
from pathlib import Path

from tools.experiments import game_view_clipping_commands as source

AFTER={
    'elf':'6c21a585574499c927f22707b735110ff34323dfb3bba084e75ba3bc66f1e340',
    'owner':'7f3d9a7a4fb00d58842ddee5e232fa13a62e89574ddaebad17fd80805f4927cc',
    'guards':'8bfcaa60e5503ffa4f80436b7b9f3251003c0389cfcc41351cfe8372dd61eb37',
}
PATHS={source.PATHS[key]:key for key in AFTER}


def fixture(root,stage,key):
    data=(root/source.BUILD/(stage+'-'+key)).read_bytes()
    digest=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest()==digest,'Modified clipping command fixture: '+key
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
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected installed clipping command input: '+key
        target=root/source.BUILD/('after-'+key)
        if not target.exists():
            target.write_bytes(data)
        assert fixture(root,'after',key)==data
