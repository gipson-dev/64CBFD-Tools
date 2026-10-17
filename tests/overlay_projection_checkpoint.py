"""Recognize only the first projection image/source/scoped pool-binding successor."""
import hashlib
from pathlib import Path
from tools.experiments import game_overlay_projection as source
from tools.experiments.game_overlay_projection_installation import BUILD

AFTER=dict(elf='5dace9c4eedc9095056502b70a98d16ad615706dacc3ff2576d01fb6c05abcc7',
    color_owner='1874f2f029edf42198bc24884d2aa69ffdbdc28041d00eb3c037b3585e38dea5',
    makefile='4458ac99ecbe044a54930d5ec79f6a72d33b2ee06acc871d61dde60f32582ef3')
PATHS={source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data=(Path(root)/BUILD/(stage+'-'+key)).read_bytes()
    if hashlib.sha256(data).hexdigest()!=(source.BASELINE if stage=='before' else AFTER)[key]:raise AssertionError('Changed projection fixture: '+key)
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
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected projection successor: '+key
        path=root/BUILD/('after-'+key)
        if not path.exists():path.write_bytes(data)
        assert fixture(root,'after',key)==data
