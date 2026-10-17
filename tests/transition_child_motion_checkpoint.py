"""Accept only the independently predicted child-motion source/image/guard successor."""
import hashlib
from pathlib import Path
from tools.experiments import game_transition_child_motion as source
from tools.experiments.game_transition_child_motion_installation import BUILD

AFTER={
    'elf':'c8b6937388a52c546239100bfbef8ef676ba5d8cdf9f08e9cf8c94638d1d00f5',
    'tile_owner':'83826e31bf955ea31ecbd0f61f8ef25236c896fe136902b0d62beab8656e6e2f',
    'guards':'1d3539f53bcdea24a4ccdb2f0b3ccb5e09052e330aca62c4e5dc92d5be0a112d',
    'burst_predecessor_screen':'ff0232de7039772473e7226cb96f391392b1bbbc46dedd60aee2e53dc97ce2a1',
}
PATHS={source.PATHS[key]:key for key in AFTER}


def fixture(root,stage,key):
    data=(Path(root)/BUILD/(stage+'-'+key)).read_bytes()
    if hashlib.sha256(data).hexdigest()!=(source.BASELINE if stage=='before' else AFTER)[key]:
        raise AssertionError('Changed child motion fixture: '+key)
    return data


def previous_input(current,path,root):
    relative=Path(path).as_posix(); prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix): relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest()==AFTER[key]:
        if fixture(root,'after',key)!=current: raise AssertionError('Changed child motion successor')
        return fixture(root,'before',key)
    return current


def freeze_after(root):
    if set(AFTER)!={'elf','tile_owner','guards','burst_predecessor_screen'}:
        raise ValueError('Child motion first prediction is not banked')
    for relative,key in PATHS.items():
        data=(root/relative).read_bytes()
        if hashlib.sha256(data).hexdigest()!=AFTER[key]: raise ValueError('Unexpected child motion successor: '+key)
        path=root/BUILD/('after-'+key)
        if not path.exists(): path.write_bytes(data)
        if fixture(root,'after',key)!=data: raise ValueError('Changed child motion successor fixture')
