"""Recover captured signed halves and the single wrapped period correction."""
import itertools
import json
import re
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY,ROM,WORDS=0x1502C608,0x59AB8,56
FUNCTION,SOURCE='func_1502C608','conker/src/game/generated_58F80.c'
ORIGINAL='s32 func_1502C608() {\n    return 0;\n}'
DECLARATIONS='''extern u8 D_800BEAC0;
extern u8 D_800CC2D0[];
extern u8 *D_8008CA4C[];
s32 func_1502C3BC(s32);
'''
SYMBOLS=dict(D_800BEAC0=0x800BEAC0,D_800CC2D0=0x800CC2D0,
    D_8008CA4C=0x8008CA4C,func_1502C3BC=0x1502C3BC)
BASE='''void func_1502C608(s32 slot) {
    u8 *actor;
    s16 value;
    s16 step;
    s32 period;
    u32 enabled;

    if (D_800BEAC0 == 0) {
        actor = (u8 *)D_800CC2D0 + (u32)slot * 0x32C;
        enabled = actor[7];
        value = *(volatile s16 *)(actor + 0x60);
        step = *(volatile s16 *)(actor + 0x62);
        if (enabled != 0) {
            period = D_8008CA4C[func_1502C3BC(slot)][4] << 8;
            value = value + step;
            if (value >= period) {
                value = value - period;
            } else if (value < 0) {
                value = value + period;
            }
            *(s16 *)(actor + 0x60) = value;
        }
    }
}'''
SELECTED=BASE.replace('    u32 enabled;\n','').replace('        enabled = actor[7];\n',
    '').replace('enabled != 0','actor[7] != 0').replace(
        'period = D_8008CA4C[func_1502C3BC(slot)][4] << 8;',
        'period = func_1502C3BC(slot);\n            period = D_8008CA4C[period][4] << 8;')


def candidates():
    yield 'selected',SELECTED
    yield 'initial',BASE
    for value_type,enabled_type in itertools.product(('s16','s32'),('u8','u32','s32')):
        body=BASE.replace('s16 value;','%s value;'%value_type).replace('s16 step;',
            '%s step;'%value_type).replace('u32 enabled;','%s enabled;'%enabled_type)
        if value_type=='s32':
            body=body.replace('value = value + step;','value = (s16)(value + step);').replace(
                'value = value - period;','value = (s16)(value - period);').replace(
                'value = value + period;','value = (s16)(value + period);')
        yield 'types-'+value_type+'-'+enabled_type,body
    yield 'signed-slot',SELECTED.replace('(u32)slot','slot')
    yield 'step-first',SELECTED.replace('    s16 value;\n    s16 step;',
        '    s16 step;\n    s16 value;')
    yield 'explicit-index',SELECTED.replace('    s32 period;','    s32 period, identity;').replace(
        '            period = D_8008CA4C[func_1502C3BC(slot)][4] << 8;',
        '            identity = func_1502C3BC(slot);\n            period = D_8008CA4C[identity][4] << 8;')
    yield 'positive-store-return',SELECTED.replace('''            } else if (value < 0) {
                value = value + period;
            }
            *(s16 *)(actor + 0x60) = value;''','''            } else {
                if (value >= 0) {
                    *(s16 *)(actor + 0x60) = value;
                    return;
                }
                value = value + period;
            }
            *(s16 *)(actor + 0x60) = value;''')
    yield 'nonvolatile-halves',SELECTED.replace('volatile s16','s16')
    for gate,period,order in itertools.product(('named','direct'),('named','slot'),('value-first','step-first')):
        body=BASE
        if gate=='direct':
            body=body.replace('    u32 enabled;\n','').replace('        enabled = actor[7];\n',
                '').replace('enabled != 0','actor[7] != 0')
        if period=='slot':
            body=body.replace('    s32 period;\n','').replace('period','slot')
        if order=='step-first':
            body=body.replace('    s16 value;\n    s16 step;','    s16 step;\n    s16 value;')
        yield '%s-gate-%s-period-%s'%(gate,period,order),body
    direct=BASE.replace('    u32 enabled;\n','').replace('        enabled = actor[7];\n',
        '').replace('enabled != 0','actor[7] != 0')
    for name,body in (
            ('register-period',direct.replace('s32 period;','register s32 period;')),
            ('scoped-period',direct.replace('    s32 period;\n','').replace(
                '        if (actor[7] != 0) {','        if (actor[7] != 0) {\n            s32 period;')),
            ('register-halves',direct.replace('    s16','    register s16')),
            ('register-actor',direct.replace('    u8 *actor;','    register u8 *actor;')),
            ('scoped-locals',direct.replace('    u8 *actor;\n    s16 value;\n    s16 step;\n    s32 period;\n','').replace(
                '    if (D_800BEAC0 == 0) {','    if (D_800BEAC0 == 0) {\n        u8 *actor;\n        s16 value, step;\n        s32 period;')),
            ('register-all',direct.replace('    u8 *actor;','    register u8 *actor;').replace(
                '    s16','    register s16').replace('    s32 period;','    register s32 period;'))):
        yield name,body
    for period_type in ('u16','u32','s16'):
        yield 'period-'+period_type,direct.replace('s32 period;',period_type+' period;')
    yield 'period-index',direct.replace(
        'period = D_8008CA4C[func_1502C3BC(slot)][4] << 8;',
        'period = func_1502C3BC(slot);\n            period = D_8008CA4C[period][4] << 8;')
    yield 'slot-index',direct.replace(
        'period = D_8008CA4C[func_1502C3BC(slot)][4] << 8;',
        'slot = func_1502C3BC(slot);\n            period = D_8008CA4C[slot][4] << 8;')
    yield 'configuration-pointer',direct.replace('s32 period;', 's32 period;\n    u8 *configuration;').replace(
        'period = D_8008CA4C[func_1502C3BC(slot)][4] << 8;',
        'configuration = D_8008CA4C[func_1502C3BC(slot)];\n            period = configuration[4] << 8;')
    for order in ('period-first','actor-last','period-between'):
        declarations={'period-first':'    s32 period;\n    u8 *actor;\n    s16 value, step;',
            'actor-last':'    s16 value, step;\n    s32 period;\n    u8 *actor;',
            'period-between':'    u8 *actor;\n    s16 value;\n    s32 period;\n    s16 step;'}
        yield order,direct.replace('    u8 *actor;\n    s16 value;\n    s16 step;\n    s32 period;',declarations[order])
    for storage in ('struct','array'):
        for order in ('value-first','step-first'):
            body=direct.replace('    s16 value;\n    s16 step;',
                '    struct { s16 %s; } captured;'%('value, step' if order=='value-first' else 'step, value')
                if storage=='struct' else '    s16 captured[2];')
            names=('captured.value','captured.step') if storage=='struct' else (
                ('captured[0]','captured[1]') if order=='value-first' else ('captured[1]','captured[0]'))
            prefix,code=body.split('    if (D_800BEAC0',1)
            for old,new in zip(('value','step'),names):
                code=re.sub(r'\b'+old+r'\b',new,code)
            yield storage+'-'+order,prefix+'    if (D_800BEAC0'+code
    for name,old,new in (
            ('negative-disable-gate','D_800BEAC0 == 0','D_800BEAC0 != 0'),
            ('negative-actor-gate','actor[7] != 0','actor[7] == 0'),
            ('negative-period-shift','[4] << 8','[4] << 7'),
            ('negative-no-negative-correction','value = value + period;','value = value;'),
            ('negative-wrong-target','*(s16 *)(actor + 0x60) = value;','*(s16 *)(actor + 0x62) = value;')):
        yield name,SELECTED.replace(old,new)
    yield 'negative-reload-captures',SELECTED.replace(
        '            value = value + step;',
        '            value = *(volatile s16 *)(actor + 0x60);\n'
        '            step = *(volatile s16 *)(actor + 0x62);\n'
        '            value = value + step;')


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD='',DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS):
        meta,words=compiler.compile_candidate(root,out,name,body,profile)
    frames=[(-word)&65535 for word in words if word>>16==0x27BD and word&0x8000]
    meta['frame']=frames[0] if frames else 0
    return meta,words


def install(before,body=SELECTED):
    assert before.count(ORIGINAL)==1
    return before.replace('#include <ultra64.h>\n','#include <ultra64.h>\nextern u8 *D_8008CA4C[];\n',1).replace(
        's32 func_1502C608();','void func_1502C608(s32 slot);').replace(ORIGINAL,body)


def main():
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-actor-counter-update'
    records=[]
    for name,body in candidates():
        for profile in compiler.PROFILES if name=='selected' else ('o2g3',):
            meta,_=compile_candidate(root,out,name+'-'+profile,body,profile)
            records.append(meta)
            print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
