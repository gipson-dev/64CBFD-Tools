"""Reverse only the first predicted selector-point and table-binding successor."""
import hashlib
from pathlib import Path
from tools.experiments import game_selector_point_transform as source

BUILD='conker/build/game-selector-point-transform-install'
AFTER={
    'elf':'eee066d8abb11de3473df415ef421bd144125ebb82062660fd1ce78742880765',
    'fixed_owner':'8a7dcaf2a902d296c58120a5f6675e5b6f97462fbee7f3abf4365210e8bdf595',
    'makefile':'1be5e78171b4169bbbb8bc47dd59d74956870e49a1023eda8bff6a908171ad3c',
    'fixed_checkpoint':'1d17bb42be74b7c351c47b9ed07489e2da80afc61e32eb030a0aaac316e6ade7',
    'fixed_tests':'3e88162a98abe05ee1b809fffeb833e833602e0b567a8a179982ede9e723ff62',
    'phase_tests':'9f84306b7d83b3be92e351a52bc4ccfd690131bd12cbf663f550c44aaa295c52',
}
PATHS={source.PATHS[key]:key for key in AFTER}


def fixture(root,stage,key):
    if stage not in ('before','after') or key not in AFTER:raise AssertionError('Unknown selector-point checkpoint member')
    data=(Path(root)/BUILD/(stage+'-'+key)).read_bytes()
    if hashlib.sha256(data).hexdigest()!=(source.BASELINE if stage=='before' else AFTER)[key]:
        raise AssertionError('Changed selector-point checkpoint fixture: '+key)
    return data


def previous_input(current,path,root):
    from tools.tests import halfword_point_checkpoint as latest
    current=latest.previous_input(current,path,root)
    relative=Path(path).as_posix();prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix):relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest()==AFTER[key]:
        if fixture(root,'after',key)!=current:raise AssertionError('Changed selector-point successor')
        return fixture(root,'before',key)
    return current


def freeze_after(root):
    if set(AFTER)!={'elf','fixed_owner','makefile','fixed_checkpoint','fixed_tests','phase_tests'}:
        raise ValueError('Unknown first selector-point prediction')
    for path,key in PATHS.items():
        data=(root/path).read_bytes()
        from tools.tests import halfword_point_checkpoint as latest
        data=latest.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=AFTER[key]:raise ValueError('Unexpected selector-point successor: '+key)
        target=root/BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        if fixture(root,'after',key)!=data:raise ValueError('Changed selector-point successor fixture')
