"""Fit declaration-backed live temporaries to the retail finalizer roles."""
import argparse
import json
from pathlib import Path

from tools.experiments import game_actor_command_finalizer_fitting as fitting

BASE=fitting.FITTED
DECLARATIONS=(
    's32 primaryIndex;','s32 suppressed;','s32 primaryBias;','s32 secondaryBias;',
    's32 noise;','s32 limit;','s32 lower;','s32 upper;','s32 sign;','s32 choose;',
    's32 reverse;','s32 current;','s32 delta;','s16 value = actor[4];',
    'f32 scale;','f32 magnitude;')
HEADER='\n'.join('    '+line for line in DECLARATIONS)
ROLE_ORDER=('primaryIndex','suppressed','secondaryBias','limit','lower','upper',
    'primaryBias','current','noise','sign','choose','reverse','delta','value','scale','magnitude')


def ordered_body(order=ROLE_ORDER,body=BASE):
    names={line.split()[1].split(';')[0]:line for line in DECLARATIONS}
    assert set(order)==set(names) and len(order)==len(names) and body.count(HEADER)==1
    return body.replace(HEADER,'\n'.join('    '+names[name] for name in order),1)


def initial_type(body,name):
    assert name in ('current','delta')
    body=body.replace('    s16 value = actor[4];','    s16 value;',1)
    body=body.replace('    s32 '+name+';','    s32 '+name+' = actor[4];',1)
    prefix,rest=body.split('    limit = 0xFF;',1)
    prefix=prefix.replace('value ==',name+' ==')
    return prefix+'    limit = 0xFF;'+rest


def late_lower(body,near='numeric'):
    body=body.replace('    lower = 40;\n','',1)
    anchor='        current = actor[0x1FE];' if near=='numeric' else '        if (actor[4] == 0x42)'
    assert body.count(anchor)==1
    return body.replace(anchor,'        lower = 40;\n'+anchor,1)


def noise_promotion(body):
    old='    if (value == 0x69 || value == 0x7C || value == 0x87)'
    new='    if ((delta = value) == 0x69 || delta == 0x7C || delta == 0x87)'
    assert body.count(old)==1
    return body.replace(old,new,1)


def candidates():
    yield 'baseline',BASE
    yield 'retail-slots',ordered_body()
    for position in (1,3,7,12,15):
        order=list(ROLE_ORDER)
        order.remove('primaryIndex')
        order.insert(position,'primaryIndex')
        yield 'index-position-'+str(position),ordered_body(order)
    for name in ('current','delta'):
        yield 'type-'+name,initial_type(ordered_body(),name)
        yield 'type-'+name+'-old-slots',initial_type(BASE,name)
    for qualified in (True,False):
        body=ordered_body()
        if not qualified:
            body=body.replace('volatile s32 first,','s32 first,',1)
        prefix='qualified' if qualified else 'ordinary'
        yield prefix+'-promoted-noise',noise_promotion(body)
        yield prefix+'-promoted-noise-late-lower',late_lower(noise_promotion(body))
        body=initial_type(body,'delta')
        yield prefix+'-type-delta-late-lower',late_lower(body)
        yield prefix+'-type-delta-bounds-lower',late_lower(body,'bounds')
    body=noise_promotion(ordered_body())
    for name in ('suppressed','primaryIndex','primaryBias','noise','lower','upper'):
        yield 'register-'+name,body.replace('    s32 '+name+';','    register s32 '+name+';',1)
    for name in ('suppressed','primaryBias','secondaryBias','noise','lower','upper','choose','reverse'):
        yield 'unsigned-'+name,body.replace('    s32 '+name+';','    u32 '+name+';',1)
    yield 'unsigned-flags',body.replace('    s32 suppressed;','    u32 suppressed;').replace(
        '    s32 choose;','    u32 choose;').replace('    s32 reverse;','    u32 reverse;')


SELECTED=noise_promotion(ordered_body())
SLOTS=dict(reverse=0x18,sign=0x20,noise=0x24,primaryBias=0x2C,upper=0x30,lower=0x34)


def recovered_owner(source):
    if source.count(BASE)==1:
        return source.replace(BASE,SELECTED,1)
    if source.count(SELECTED)==1:
        return source
    raise ValueError('Expected the known extent/frame body or role-fit body')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name')
    parser.add_argument('--filter',default='')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-actor-command-finalizer-roles'
    out.mkdir(exist_ok=True)
    records=[]
    for name,body in candidates():
        if args.name and name!=args.name:
            continue
        if args.filter not in name:
            continue
        meta,_=fitting.compile_candidate(root,out,name,body)
        records.append(meta)
        print(name,meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
