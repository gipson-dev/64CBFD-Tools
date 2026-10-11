"""Screen complete resource-buffer lifetimes and retail branch joins."""
import argparse
import itertools
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_resource_buffers_candidates as recovery

BASE = recovery.QUALIFIED
PAIR = '''typedef struct {
    u8 padding[0x28C];
    u8 *first;
    u8 *second;
} ResourcePair15084044;
'''


def split_join(body):
    old = '''            } else {
                *(u8 **)(pair + 0x28C) = *(u8 **)(pair + 0x290) = config;
                D_800D1F80[identity] += 2;
            }
            first = *(u8 **)(pair + 0x28C);'''
    new = '''                first = *(u8 **)(pair + 0x28C);
            } else {
                *(u8 **)(pair + 0x28C) = *(u8 **)(pair + 0x290) = config;
                D_800D1F80[identity] += 2;
                first = *(u8 **)(pair + 0x28C);
            }'''
    assert body.count(old)==1
    return body.replace(old,new)


def separate_source(body):
    return body.replace('    u8 *config;', '    u8 *config;\n    u8 *shared;').replace(
        '    config = D_800D19A0[identity];', '    shared = D_800D19A0[identity];').replace(
        '\n    if (config == NULL)', '\n    if (shared == NULL)').replace(
        '*(u8 **)(pair + 0x28C) = *(u8 **)(pair + 0x290) = config;',
        '*(u8 **)(pair + 0x28C) = *(u8 **)(pair + 0x290) = shared;').replace('first == config', 'first == shared')


def typed_pair(body):
    return body.replace('    u8 *pair;', '    ResourcePair15084044 *pair;').replace(
        '    u8 *cursor;', '    ResourcePair15084044 *cursor;').replace(
        'pair = actor + channel * 8;', 'pair = (ResourcePair15084044 *)(actor + channel * 8);').replace(
        'cursor = actor + channel * 8;', 'cursor = (ResourcePair15084044 *)(actor + channel * 8);').replace(
        'cursor += 4', 'cursor = (ResourcePair15084044 *)((u8 *)cursor + 4)').replace(
        '*(u8 **)(pair + 0x28C)', 'pair->first').replace('*(u8 **)(pair + 0x290)', 'pair->second').replace(
        '*(u8 **)(cursor + 0x28C)', 'cursor->first')


def candidates():
    yield 'banked', BASE, ''
    for join,separate,packed,cursor in itertools.product((False,True),(False,True),(False,True),('plain','shift')):
        body=split_join(BASE) if join else BASE
        if separate: body=separate_source(body)
        if packed: body=body.replace('    s32 mode;', '    u8 mode;').replace('    s32 identity;', '    u8 identity;')
        if cursor=='shift': body=body.replace('cursor = actor + channel * 8;', 'cursor = actor + (channel << 3);')
        yield 'join%d-source%d-byte%d-%s'%(join,separate,packed,cursor),body,''
    for join,separate in itertools.product((False,True),(False,True)):
        body=split_join(BASE) if join else BASE
        if separate: body=separate_source(body)
        yield 'pair-join%d-source%d'%(join,separate),typed_pair(body),PAIR


def compile_candidate(root,out,name,body=BASE,profile='o2g3',record=''):
    with patch.object(recovery,'RECORD',recovery.RECORD+record):
        return recovery.compile_candidate(root,out,name,body,profile)


NEAR = split_join(BASE).replace('cursor = actor + channel * 8;', 'cursor = actor + (channel << 3);')
QUALIFIED = NEAR.replace('''        cursor = actor + (channel << 3);
        for (offset = 0;''', '''        offset = 0;
        cursor = actor + (channel << 3);
        for (;''')


def lifetime_candidates():
    for initial,eligible,initialize in itertools.product((False,True),(False,True),(False,True)):
        body=NEAR
        if initial:
            body=body.replace('    config = D_800D19A0[identity];\n    if (config == NULL)',
                '    if (D_800D19A0[identity] == NULL)').replace(
                '*(u8 **)(pair + 0x28C) = *(u8 **)(pair + 0x290) = config;',
                '*(u8 **)(pair + 0x28C) = *(u8 **)(pair + 0x290) = D_800D19A0[identity];').replace(
                'first == config', 'first == D_800D19A0[identity]')
        if eligible:
            body=body.replace('''            if ((*(u8 **)(cursor + 0x28C) == NULL) ||
                (*(u8 **)(cursor + 0x28C) == D_800D19A0[identity]) ||''',
                '''            config = *(u8 **)(cursor + 0x28C);
            if ((config == NULL) || (config == D_800D19A0[identity]) ||''')
        if initialize:
            body=body.replace('''        cursor = actor + (channel << 3);
        for (offset = 0;''', '''        offset = 0;
        cursor = actor + (channel << 3);
        for (;''')
        yield 'inline%d-eligible%d-init%d'%(initial,eligible,initialize),body,''
    for registers in (('config',),('first',),('mode',),('identity',),('offset',),('config','first'),
            ('config','mode'),('config','identity'),('mode','identity')):
        body=NEAR
        for variable in registers:
            for dtype in ('u8 *','s32 '):
                body=body.replace('    '+dtype+variable+';', '    register '+dtype+variable+';')
        yield 'register-'+'-'.join(registers),body,''
    body=separate_source(NEAR)
    for variable in ('config','shared','first','mode','identity','offset','size'):
        for dtype in ('u8 *','s32 '):
            shaped=body.replace('    '+dtype+variable+';', '    register '+dtype+variable+';')
            if shaped!=body: yield 'source-register-'+variable,shaped,''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles',action='store_true')
    parser.add_argument('--lifetimes',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-resource-buffers-matching'; records=[]
    for name,body,record in (lifetime_candidates() if args.lifetimes else candidates()):
        for profile in (('o2g3','o2','o1g3') if args.profiles else ('o2g3',)):
            meta,_=compile_candidate(root,out,name+'-'+profile,body,profile,record)
            records.append(meta)
            print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__': main()
