"""Reverse only the first predicted direct-reveal successor for archived fixtures."""
import hashlib
from pathlib import Path
from tools.experiments import game_text_reveal_renderer as source

BUILD='conker/build/game-text-reveal-install'
AFTER={
    'elf':'9c99acc828faf468f59ae765bf58c849f1a5d1d0aaa254ed2d1ee09ac05c60f3',
    'tile_owner':'221907821b83727c3d2fb9de8a5c5d040c58f3c2ea71174c59929532037e2112',
    'constructor_checkpoint':'ff2a6503b86ad29ad915b1cc20bc4dca8d2b5052aeb116a94eaae515a1979908',
    'constructor_tests':'868fcadf5827e1c67c95fa631a063b8bcac6cce3516d52740134bb4beca91dc9',
}
PATHS={source.PATHS[key]:key for key in AFTER}


def fixture(root,stage,key):
    if stage not in ('before','after') or key not in AFTER:raise AssertionError('Unknown text reveal checkpoint member')
    data=(Path(root)/BUILD/(stage+'-'+key)).read_bytes()
    if hashlib.sha256(data).hexdigest()!=(source.BASELINE if stage=='before' else AFTER)[key]:
        raise AssertionError('Changed text reveal checkpoint fixture: '+key)
    return data


def previous_input(current,path,root):
    relative=Path(path).as_posix();prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix):relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest()==AFTER[key]:
        if fixture(root,'after',key)!=current:raise AssertionError('Changed text reveal successor')
        return fixture(root,'before',key)
    return current


def freeze_after(root):
    if set(AFTER)!={'elf','tile_owner','constructor_checkpoint','constructor_tests'}:raise ValueError('Unknown first reveal prediction')
    for path,key in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=AFTER[key]:raise ValueError('Unexpected text reveal successor: '+key)
        target=root/BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        if fixture(root,'after',key)!=data:raise ValueError('Changed text reveal successor fixture')
