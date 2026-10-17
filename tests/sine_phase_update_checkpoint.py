"""Reverse only the first predicted sine/phase successor for archived fixtures."""
import hashlib
from pathlib import Path
from tools.experiments import game_sine_phase_update as source

BUILD='conker/build/game-sine-phase-update-install'
AFTER={
    'elf':'39f955fd7d2a506df706bb6581bef6b106ad20bab4edcdf6693a13a7070a2d54',
    'phase_owner':'2a0a2a01c621241a9c495441157e350556798df089b43b885347960ac8b3d0c5',
    'guards':'26ab94711f4bf70d09dcb372b00fbfbc72f78826180ffb552bccb9d09dc7d08d',
    'motion_checkpoint':'6e104844b0c79fbb5b3eeff9e93746e395150dc1f3f397615381f894a5f9a2ac',
    'motion_tests':'0d47a852ddc422a347470fe8df6c361cef96e04ed047aade0212ec198c10f7b0',
}
EXTRA_AFTER={'reveal_tests':'50b93eabc654c9fad88404f04478d50820f2fc7786dc882ce32954dd1b0ee6d2'}
PATHS={source.PATHS[key]:key for key in (*AFTER,*EXTRA_AFTER)}


def fixture(root,stage,key):
    if stage not in ('before','after') or key not in (*AFTER,*EXTRA_AFTER):raise AssertionError('Unknown sine-phase checkpoint member')
    data=(Path(root)/BUILD/(stage+'-'+key)).read_bytes()
    if hashlib.sha256(data).hexdigest()!=(source.BASELINE if stage=='before' else dict(AFTER,**EXTRA_AFTER))[key]:
        raise AssertionError('Changed sine-phase checkpoint fixture: '+key)
    return data


def previous_input(current,path,root):
    from tools.tests import fixed_sine_update_checkpoint as latest
    current=latest.previous_input(current,path,root)
    relative=Path(path).as_posix();prefix=Path(root).as_posix()+'/'
    if relative.startswith(prefix):relative=relative[len(prefix):]
    key=PATHS.get(relative)
    if key and hashlib.sha256(current).hexdigest()==dict(AFTER,**EXTRA_AFTER)[key]:
        if fixture(root,'after',key)!=current:raise AssertionError('Changed sine-phase successor')
        return fixture(root,'before',key)
    return current


def freeze_after(root):
    if set(AFTER)!={'elf','phase_owner','guards','motion_checkpoint','motion_tests'}:
        raise ValueError('Unknown first sine-phase prediction')
    if set(EXTRA_AFTER)!={'reveal_tests'}:raise ValueError('Unknown sine-phase compatibility prediction')
    for path,key in PATHS.items():
        data=(root/path).read_bytes()
        from tools.tests import fixed_sine_update_checkpoint as latest
        data=latest.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=dict(AFTER,**EXTRA_AFTER)[key]:raise ValueError('Unexpected sine-phase successor: '+key)
        target=root/BUILD/('after-'+key)
        if not target.exists():target.write_bytes(data)
        if fixture(root,'after',key)!=data:raise ValueError('Changed sine-phase successor fixture')
