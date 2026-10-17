"""Reverse only the immutable first halfword-point successor."""
import hashlib
from pathlib import Path
from tools.experiments import game_halfword_point_update as source

BUILD='conker/build/game-halfword-point-update-install'
AFTER={
    'elf':'1d4825bdc189a539fafe4b1e2b9e63e7104626932e40e0f15dfbfb60ba3e8e2f',
    'fixed_owner':'2107156a650a7b3587f6dc3b2517235fe494b689cf89d27e0a195b793db64ba9',
    'selector_checkpoint':'1375dd0b7f822e756b2876396d7cccad240552e43979d54990e8e5247e20ea78',
    'selector_tests':'3694582650077fb11f2eee824637a12aef3b0a68f75968b3a5517555c0a8d765',
}
PATHS={source.PATHS[key]:key for key in AFTER}


def fixture(root,stage,key):
    if stage not in ('before','after') or key not in AFTER:raise AssertionError('Unknown halfword-point checkpoint member')
    data=(Path(root)/BUILD/(stage+'-'+key)).read_bytes()
    if hashlib.sha256(data).hexdigest()!=(source.BASELINE if stage=='before' else AFTER)[key]:
        raise AssertionError('Changed halfword-point checkpoint fixture: '+key)
    return data


def previous_input(current,path,root):
    from tools.tests import actor_state_checkpoint as latest
    current=latest.previous_input(current,path,root)
    relative=Path(path).as_posix();prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix):relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest()==AFTER[key]:
        if fixture(root,'after',key)!=current:raise AssertionError('Changed halfword-point successor')
        return fixture(root,'before',key)
    return current


def freeze_after(root):
    if set(AFTER)!={'elf','fixed_owner','selector_checkpoint','selector_tests'}:
        raise ValueError('Unknown first halfword-point prediction')
    for path,key in PATHS.items():
        data=(root/path).read_bytes()
        from tools.tests import actor_state_checkpoint as latest
        data=latest.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=AFTER[key]:raise ValueError('Unexpected halfword-point successor: '+key)
        target=root/BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        if fixture(root,'after',key)!=data:raise ValueError('Changed halfword-point successor fixture')
