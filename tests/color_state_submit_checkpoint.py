"""Recognize only the first direct color-helper image and three source successors."""
import hashlib
from pathlib import Path

from tools.experiments import game_color_state_submit as source
from tools.experiments.game_color_state_submit_installation import BUILD

AFTER=dict(elf='ae0e0b359077e8a6a85a465b173b4d8bf4de55f395e51e77a02464ef9602f014',
    color_owner='b8f159e15a63d7dcd69eb9fd972a98cab9055ed69fceff0ad103e955628498e2',
    view_list_caller_owner='62d13a9969d88b5ecb7fbeddc96183d998ecc9cb9a881b43c527021591fec6c0',
    color_pair_caller_owner='a5413407febf40c4dbcfd968bd6671425c1c972a173ef57677c2a4002ae10948')
PATHS={source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data=(root/BUILD/(stage+'-'+key)).read_bytes();wanted=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest()==wanted,'Changed color submit fixture: '+key
    return data


def previous_input(current,path,root):
    relative=Path(path).as_posix();prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix):relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key in AFTER and hashlib.sha256(current).hexdigest()==AFTER[key]:return fixture(root,'before',key)
    return current


def freeze_after(root):
    for relative,key in PATHS.items():
        data=(root/relative).read_bytes()
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected color submit successor: '+key
        target=root/BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        assert fixture(root,'after',key)==data
