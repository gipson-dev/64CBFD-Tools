"""Recover the full dispatcher's emitted flag, spill lifetime and private homes."""
import argparse
import json
import re
from pathlib import Path

from tools.experiments import game_actor_render_dispatch_candidates as recovery

BASE=recovery.SELECTED
LIMIT='D_800BEBA4 < ((s32)((u32)commands - (u32)D_800BE9C8[D_800BE9C0]) >> 3)'
ENDING='''    if ('''+LIMIT+''') {
        return original;
    }
    return commands;'''
MASK='''    if ((actor[0x74] & (1U << (view & 31))) == (1U << (view & 31))) {'''


def candidates():
    yield 'baseline',BASE
    cached=BASE.replace('    s32 alpha;','    s32 alpha;\n    u32 mask;').replace(MASK,
        '    mask = 1U << (view & 31);\n    if ((actor[0x74] & mask) == mask) {')
    reused=BASE.replace(MASK,'    alpha = 1U << (view & 31);\n    if ((actor[0x74] & alpha) == alpha) {')
    flag=BASE.replace('    s32 alpha;','    s32 alpha;\n    s32 overflow;').replace(ENDING,
        '''    overflow = 0;
    if ('''+LIMIT+''') {
        overflow = 1;
    }
    if (overflow == 0) {
        return commands;
    } else {
        return original;
    }''')
    cached_flag=flag.replace('    s32 overflow;','    s32 overflow;\n    u32 mask;').replace(
        MASK,'    mask = 1U << (view & 31);\n    if ((actor[0x74] & mask) == mask) {')
    reused_flag=cached_flag.replace('    u32 mask;\n','').replace('mask = 1U','overflow = 1U').replace(
        '(actor[0x74] & mask) == mask','(actor[0x74] & overflow) == overflow')
    for name,body in (('cached-mask',cached),('reused-alpha-mask',reused),('overflow-flag',flag),
            ('cached-mask-flag',cached_flag),('reused-mask-flag',reused_flag)):
        yield name,body
        yield name+'-volatile-actor',body.replace('u8 *actor;','u8 *volatile actor;')
    owner=BASE.replace('    s32 alpha;','    s32 alpha;\n    u8 *owner;').replace(
        '        u8 *owner = *(u8 **)(actor + 0x318);','        owner = *(u8 **)(actor + 0x318);')
    yield 'top-owner',owner
    yield 'top-owner-flag',flag.replace('    s32 overflow;','    s32 overflow;\n    u8 *owner;').replace(
        '        u8 *owner = *(u8 **)(actor + 0x318);','        owner = *(u8 **)(actor + 0x318);')
    returned=BASE.replace('    Gfx *original;','    Gfx *original;\n    Gfx *returned;').replace(
        '    commands = func_1502CCFC','    returned = func_1502CCFC').replace(
        '(u32)commands - (u32)D_800BE9C8','(u32)returned - (u32)D_800BE9C8').replace(
        '    return commands;\n}','    return returned;\n}')
    yield 'returned-cursor',returned
    yield 'returned-cursor-volatile-actor',returned.replace('u8 *actor;','u8 *volatile actor;')
    nested=BASE.replace('''    if (func_1506196C(actor, view) == 0) {
        return commands;
    }
    if (*(u8 **)(actor + 0x1D4) == NULL) {
        return commands;
    }''','''    if (func_1506196C(actor, view) != 0) {
        if (*(u8 **)(actor + 0x1D4) != NULL) {''').replace(
        '    return commands;\n}','    return commands;\n        }\n    }\n    return original;\n}')
    yield 'nested-render',nested
    yield 'nested-render-flag',nested.replace('    s32 alpha;','    s32 alpha;\n    s32 overflow;').replace(
        ENDING,flag[flag.index('    overflow = 0;'):flag.rindex('\n}')])
    yield 'nested-render-volatile-actor',nested.replace('u8 *actor;','u8 *volatile actor;')


def lifetime_candidates():
    forms=dict(candidates())
    flag=forms['overflow-flag']
    declarations='\n'.join('    '+line for line in (
        'Gfx *original;','u8 *actor;','u8 *matrix;','s32 parameters[4];',
        's32 tier;','s32 alpha;','s32 overflow;'))
    for name,order in (
            ('retail-order',('s32 tier;','s32 alpha;','s32 parameters[4];',
                'u8 *matrix;','Gfx *original;','u8 *actor;','s32 overflow;')),
            ('reverse-order',('s32 overflow;','s32 alpha;','s32 tier;',
                's32 parameters[4];','u8 *matrix;','u8 *actor;','Gfx *original;')),
            ('tier-first',('s32 tier;','s32 parameters[4];','u8 *matrix;',
                'Gfx *original;','u8 *actor;','s32 alpha;','s32 overflow;'))):
        yield name,flag.replace(declarations,'\n'.join('    '+line for line in order))
    final=flag[flag.index('    overflow = 0;'):flag.rindex('\n}')]
    for name,ending in (
            ('flag-cursor-return','''    if (overflow == 0) {
        return commands;
    }
    return original;'''),
            ('flag-assignment-return','''    if (overflow != 0) {
        commands = original;
    }
    return commands;'''),
            ('flag-else-assignment','''    if (overflow == 0) {
        return commands;
    } else {
        commands = original;
    }
    return commands;''')):
        prefix=final[:final.index('    if (overflow == 0)')]
        yield name,flag.replace(final,prefix+ending)
    boolean=BASE.replace('    s32 alpha;','    s32 alpha;\n    s32 overflow;').replace(
        ENDING,'''    overflow = ('''+LIMIT+''') ? 1 : 0;
    if (overflow == 0) {
        return commands;
    } else {
        return original;
    }
    return commands;''')
    yield 'ternary-flag',boolean
    yield 'ternary-flag-no-trailing-return',boolean.replace(
        '    }\n    return commands;\n}','    }\n}')
    inverted=boolean.replace('''    if (overflow == 0) {
        return commands;
    } else {
        return original;
    }''','''    if (overflow != 0) {
        return original;
    } else {
        return commands;
    }''')
    yield 'inverted-ternary-flag',inverted
    for label,names in (
            ('semantic-names',dict(original='savedCommands',actor='object',
                matrix='transform',parameters='colour',tier='detail',alpha='opacity',
                overflow='overLimit')),
            ('private-home-names',dict(original='sp34',actor='actor',matrix='sp38',
                parameters='sp40',tier='sp54',alpha='alpha',overflow='overflow')),
            ('short-names',dict(original='start',actor='actor',matrix='matrix',
                parameters='rgba',tier='level',alpha='alpha',overflow='full'))):
        renamed=re.sub(r'\b('+'|'.join(names)+r')\b',lambda m:names[m.group()],inverted)
        yield label,renamed
    scoped=flag.replace('    s32 overflow;\n','').replace('    overflow = 0;',
        '    {\n    s32 overflow;\n    overflow = 0;').replace(
        '    }\n}','    }\n    }\n}')
    yield 'scoped-flag',scoped


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lifetime',action='store_true')
    parser.add_argument('--only',nargs='+')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/('conker/build/game-actor-render-dispatch-lifetime' if args.lifetime
        else 'conker/build/game-actor-render-dispatch-layout')
    records=[]
    for name,body in lifetime_candidates() if args.lifetime else candidates():
        if args.only and name not in args.only:
            continue
        for profile in ('o2g3','o1g3'):
            meta,_=recovery.compile_candidate(root,out,name+'-'+profile,body,profile)
            records.append(meta)
            print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    receipt='measurements-selected.json' if args.only else 'measurements.json'
    (out/receipt).write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
