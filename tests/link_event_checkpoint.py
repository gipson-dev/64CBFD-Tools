"""Accept only the first independently predicted complete link-event successor."""
import hashlib
from pathlib import Path
from tools.experiments import game_link_event_callback as source

BUILD='conker/build/game-link-event-install'
AFTER={
    'elf':'20b597fa44e3ebe08ddbd7b90346b56df821d3e3ca7cb4733da7e74ee8ee56d8',
    'tile_owner':'3caade2a56d289fddc2d49bc85c9b529352dc9bceb3dd0af172955f2517704a9',
    'guards':'b520ef277d609c277857af840c8f0a1ac4b668abb76146a7d58b4b65e13fd083',
    'burst_checkpoint':'6284b53fdccac9b2f127ad9faf95eb7d3f5bd810c424b4727992cc360eb0cc60',
}
PATHS={source.PATHS[key]:key for key in AFTER}


def fixture(root,stage,key):
    data=(Path(root)/BUILD/(stage+'-'+key)).read_bytes()
    if hashlib.sha256(data).hexdigest()!=(source.BASELINE if stage=='before' else AFTER)[key]:
        raise AssertionError('Changed link-event checkpoint fixture: '+key)
    return data


def previous_input(current,path,root):
    from tools.tests import text_buffer_constructor_checkpoint as latest
    current=latest.previous_input(current,path,root)
    relative=Path(path).as_posix();prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix):relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest()==AFTER[key]:
        if fixture(root,'after',key)!=current:raise AssertionError('Changed link-event successor')
        return fixture(root,'before',key)
    return current


def freeze_after(root):
    if set(AFTER)!={'elf','tile_owner','guards','burst_checkpoint'}:raise ValueError('Unknown first link-event prediction')
    for path,key in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=AFTER[key]:raise ValueError('Unexpected link-event successor: '+key)
        target=root/BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        if fixture(root,'after',key)!=data:raise ValueError('Changed link-event successor fixture')
