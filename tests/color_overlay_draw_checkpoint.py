"""Accept only the first exact overlay image and three typed source successors."""
import hashlib
from pathlib import Path
from tools.experiments import game_color_overlay_draw as source
from tools.experiments.game_color_overlay_draw_installation import BUILD

AFTER=dict(elf='cab895122f114cbfe41572410c714d016d6b75244bd3434fb6d26c453d60c1c1',
    color_owner='4cef4ff1b1cb1f393a391225a9d6dbebfafee3d2f73873c831ef273d455b43de',
    overlay_gray_owner='ed0fdab2c81a5f3c17dca256cf55a0c46056526122375a9042651808dcd094bf',
    overlay_mode_owner='4a614a105b01975d0dbfe6ef6752e1763ffe79ac6a872d24b1fa53c286a0a7aa')
PATHS={source.PATHS[k]:k for k in AFTER}


def fixture(root,stage,key):
    data=(root/BUILD/(stage+'-'+key)).read_bytes();wanted=(source.BASELINE if stage=='before' else AFTER)[key]
    assert hashlib.sha256(data).hexdigest()==wanted,'Changed overlay fixture: '+key
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
        assert hashlib.sha256(data).hexdigest()==AFTER[key],'Unexpected overlay successor: '+key
        target=root/BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        assert fixture(root,'after',key)==data
