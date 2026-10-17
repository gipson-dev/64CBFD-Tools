"""Reverse only the first predicted direct fixed-sine successor."""
import hashlib
from pathlib import Path
from tools.experiments import game_fixed_sine_update as source

BUILD='conker/build/game-fixed-sine-update-install'
AFTER={
    'elf':'73e16cc1c51f1ee12f996b964ad73d1c0864cc0d93f87dad2c40f609a44b9dee',
    'fixed_owner':'c37a43a41ca1bc48862aef32603fbf44ea495fc1e263f758c5e19c16fd5cb508',
    'phase_checkpoint':'f294221ff0729653f885ef7fa820a270d0d089db9d521d2b6c94d8e560ebcd57',
    'phase_tests':'aece4b12c66af8e66294238bb16dd9e0bb93d5ea1441697e6ecfcbd4ce0d287d',
}
PATHS={source.PATHS[key]:key for key in AFTER}


def fixture(root,stage,key):
    if stage not in ('before','after') or key not in AFTER:raise AssertionError('Unknown fixed-sine checkpoint member')
    data=(Path(root)/BUILD/(stage+'-'+key)).read_bytes()
    if hashlib.sha256(data).hexdigest()!=(source.BASELINE if stage=='before' else AFTER)[key]:
        raise AssertionError('Changed fixed-sine checkpoint fixture: '+key)
    return data


def previous_input(current,path,root):
    from tools.tests import selector_point_checkpoint as latest
    current=latest.previous_input(current,path,root)
    relative=Path(path).as_posix();prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix):relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest()==AFTER[key]:
        if fixture(root,'after',key)!=current:raise AssertionError('Changed fixed-sine successor')
        return fixture(root,'before',key)
    return current


def freeze_after(root):
    if set(AFTER)!={'elf','fixed_owner','phase_checkpoint','phase_tests'}:
        raise ValueError('Unknown first fixed-sine prediction')
    for path,key in PATHS.items():
        data=(root/path).read_bytes()
        from tools.tests import selector_point_checkpoint as latest
        data=latest.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=AFTER[key]:raise ValueError('Unexpected fixed-sine successor: '+key)
        target=root/BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        if fixture(root,'after',key)!=data:raise ValueError('Changed fixed-sine successor fixture')
