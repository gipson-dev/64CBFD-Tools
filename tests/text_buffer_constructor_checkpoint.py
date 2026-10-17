"""Reverse only the first complete predicted constructor successor for old fixtures."""
import hashlib
from pathlib import Path
from tools.experiments import game_text_buffer_constructor as source

BUILD='conker/build/game-text-buffer-constructor-install'
AFTER={
    'elf':'789239972b3c6cfcd76713dc326d12295c7b7e8379eb812e239d29d1098017ac',
    'tile_owner':'e71e4a1e4e8498ed686d2185cecd2ecfa3ab6fee6d86347f64be89a7326a8e7e',
    'guards':'b15711ee995226efb2f2d45dd6b62c52f4fdc560118b4f6a1885dfc820a62832',
    'link_checkpoint':'73b7a3c61cd3795d90d4e119ef92d2bac1214c5e2c6fa60cf79a02673c6113f1',
    'fade_source':'12fcb7ffdf34408597f06b976a22b8a445a498f56489f49cb813ddbfa3d0cc73',
}
EXTRA_AFTER={
    'fade_tests':'fef4d9077458feb0fe40e6c0d09da4842bfb9fc72e9a4a50c0d5d0fc574940ee',
    'link_tests':'a478371c81502c711b34b91e2632b801d062212b27afd060766fba9b005d1057',
}
ALL_AFTER=dict(AFTER,**EXTRA_AFTER)
PATHS={source.PATHS[key]:key for key in ALL_AFTER}


def fixture(root,stage,key):
    if stage not in ('before','after') or key not in ALL_AFTER:raise AssertionError('Unknown constructor checkpoint member')
    data=(Path(root)/BUILD/(stage+'-'+key)).read_bytes()
    if hashlib.sha256(data).hexdigest()!=(source.BASELINE if stage=='before' else ALL_AFTER)[key]:
        raise AssertionError('Changed text-constructor checkpoint fixture: '+key)
    return data


def previous_input(current,path,root):
    from tools.tests import text_reveal_checkpoint as latest
    current=latest.previous_input(current,path,root)
    relative=Path(path).as_posix();prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix):relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest()==ALL_AFTER[key]:
        if fixture(root,'after',key)!=current:raise AssertionError('Changed text-constructor successor')
        return fixture(root,'before',key)
    return current


def freeze_after(root):
    if set(AFTER)!={'elf','tile_owner','guards','link_checkpoint','fade_source'}:
        raise ValueError('Unknown first constructor prediction')
    if set(EXTRA_AFTER)!={'fade_tests','link_tests'}:raise ValueError('Unknown fixture-cache prediction')
    for path,key in PATHS.items():
        data=(root/path).read_bytes()
        from tools.tests import text_reveal_checkpoint as latest
        data=latest.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=ALL_AFTER[key]:raise ValueError('Unexpected constructor successor: '+key)
        target=root/BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        if fixture(root,'after',key)!=data:raise ValueError('Changed constructor successor fixture')
