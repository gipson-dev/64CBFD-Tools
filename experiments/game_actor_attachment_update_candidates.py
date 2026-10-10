"""Recover the complete leaf attachment updater and fresh inclusive copy limit."""
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1502F264, 0x5C714, 89
FUNCTION = 'func_1502F264'
SOURCE = 'conker/src/game/generated_58F80.c'
ORIGINAL = 's32 func_1502F264() {\n    return 0;\n}'
TYPES = 'typedef struct { u8 bytes[0x32C]; } ActorBlock58F80;\n'
DECLARATIONS = 'extern u8 D_800CC2D0[];\nextern s32 D_80082FA0;\n'
SYMBOLS = dict(D_800CC2D0=0x800CC2D0,D_80082FA0=0x80082FA0)
SELECTED = '''void func_1502F264(s32 slot) {
    u8 *actor;
    u8 *attached;
    u8 *source;
    u8 *target;
    f32 *matrix;
    s32 index;
    u8 flags;
    u16 angle;

    actor = (u8 *)D_800CC2D0 + (u32)slot * 0x32C;
    if (actor[0x65] != 0) {
        attached = (u8 *)D_800CC2D0 + (u32)actor[0x65] * 0x32C - 0x32C;
        if ((actor[0x101] & 2) != 2) {
            matrix = *(f32 **)(attached + 0x1D4);
            if (matrix == NULL) {
                *(f32 *)(actor + 0x14) = *(f32 *)(attached + 0x14);
                *(f32 *)(actor + 0x18) = *(f32 *)(attached + 0x18);
                *(f32 *)(actor + 0x1C) = *(f32 *)(attached + 0x1C);
            } else {
                matrix = (f32 *)((u8 *)matrix + *(u32 *)(actor + 0x5C) * 0x40);
                *(f32 *)(actor + 0x14) = matrix[12];
                *(f32 *)(actor + 0x18) = matrix[13];
                *(f32 *)(actor + 0x1C) = matrix[14];
            }
            flags = actor[0x101];
            *(f32 *)(actor + 0x180) = *(f32 *)(attached + 0x180);
            *(f32 *)(actor + 0x20) = -4.0f;
            if ((flags & 0x20) == 0) {
                angle = *(u16 *)(attached + 0x76);
                flags = actor[0x101];
                *(u16 *)(actor + 0x76) = angle;
                *(f32 *)(actor + 0x3C) = *(f32 *)(attached + 0x3C);
                *(f32 *)(actor + 0x40) = *(f32 *)(attached + 0x40);
                *(u16 *)(actor + 0x76) = *(u16 *)(attached + 0x76);
                *(u16 *)(actor + 0x7A) = *(u16 *)(attached + 0x7A);
                *(u16 *)(actor + 0x78) = *(u16 *)(attached + 0x78);
            }
            if ((flags & 0x40) == 0) {
                actor[7] = attached[7];
                actor[8] = attached[8];
                actor[9] = attached[9];
                actor[10] = attached[10];
                actor[15] = attached[15];
                index = 0;
                source = attached;
                target = actor;
                if (D_80082FA0 >= 0) {
                    do {
                        target[11] = source[11];
                        index++;
                        source++;
                        target++;
                    } while (D_80082FA0 >= index);
                }
            }
        }
    }
}'''
BASE=SELECTED
SELECTED=BASE.replace('(u32)slot * 0x32C','slot * 0x32C').replace('(u32)actor[0x65]','actor[0x65]')


def candidates():
    yield 'selected',SELECTED
    yield 'unsigned-offset',BASE
    for mode in ('signed','block-signed','block-unsigned'):
        body=BASE
        if mode=='signed':
            body=body.replace('(u32)slot * 0x32C','slot * 0x32C').replace('(u32)actor[0x65]','actor[0x65]')
        else:
            index='(u32)slot' if mode=='block-unsigned' else 'slot'
            body=body.replace('(u8 *)D_800CC2D0 + (u32)slot * 0x32C',
                '(u8 *)((ActorBlock58F80 *)D_800CC2D0 + '+index+')').replace(
                '(u8 *)D_800CC2D0 + (u32)actor[0x65] * 0x32C - 0x32C',
                '(u8 *)((ActorBlock58F80 *)D_800CC2D0 + actor[0x65] - 1)')
        yield mode,body
    for name,body in (('selected',SELECTED),('block-signed',dict(list(candidates_base()))['block'])):
        yield name+'-for',body.replace('''                if (D_80082FA0 >= 0) {
                    do {
                        target[11] = source[11];
                        index++;
                        source++;
                        target++;
                    } while (D_80082FA0 >= index);
                }''','''                for (; index <= D_80082FA0; index++, source++, target++) {
                    target[11] = source[11];
                }''')
        yield name+'-direct-angle',body.replace('                angle = *(u16 *)(attached + 0x76);\n',
            '').replace('                flags = actor[0x101];\n                *(u16 *)(actor + 0x76) = angle;',
            '                *(u16 *)(actor + 0x76) = *(u16 *)(attached + 0x76);\n                flags = actor[0x101];')
    yield 'negative-no-attachment',SELECTED.replace('actor[0x65] != 0','0')
    yield 'negative-zero-based',SELECTED.replace(' * 0x32C - 0x32C',' * 0x32C')
    yield 'negative-wrong-bit',SELECTED.replace('& 2) != 2','& 1) != 1')
    yield 'negative-fixed-limit',SELECTED.replace('D_80082FA0','3')
    yield 'negative-exclusive-limit',SELECTED.replace('D_80082FA0 >= index','D_80082FA0 > index')
    yield 'negative-matrix-stride',SELECTED.replace(' * 0x40',' * 0x20')
    yield 'negative-no-repeat-angle',SELECTED.replace(
        '                *(u16 *)(actor + 0x76) = *(u16 *)(attached + 0x76);\n','')
    for flags_type in ('u8','u32','s32'):
        for volatile_flags in (False,True):
            for volatile_limit in (False,True):
                body=SELECTED.replace('u8 flags;','%s flags;'%flags_type)
                if volatile_flags:
                    body=body.replace('flags = actor[0x101];','flags = *(volatile u8 *)(actor + 0x101);')
                if volatile_limit:
                    body=body.replace('D_80082FA0','*(volatile s32 *)&D_80082FA0')
                yield 'flags-%s-%d-limit-%d'%(flags_type,volatile_flags,volatile_limit),body
    for flags_type in ('u8','u32'):
        body=SELECTED.replace('u8 flags;','%s flags;'%flags_type).replace(
            'flags = actor[0x101];','flags = *(volatile u8 *)(actor + 0x101);').replace(
            'D_80082FA0','*(volatile s32 *)&D_80082FA0')
        for destination in ('volatile-stores','volatile-bytes','direct-angle','wide-angle'):
            shaped=body
            if destination=='volatile-stores':
                for offset in (7,8,9,10,15):
                    shaped=shaped.replace('actor[%d] = attached[%d];'%(offset,offset),
                        '((volatile u8 *)actor)[%d] = attached[%d];'%(offset,offset))
                shaped=shaped.replace('target[11] = source[11];','((volatile u8 *)target)[11] = source[11];')
            if destination=='volatile-bytes':
                shaped=shaped.replace('u8 *actor;','volatile u8 *actor;').replace('u8 *target;',
                    'volatile u8 *target;')
            if destination=='direct-angle':
                shaped=shaped.replace('                angle = *(u16 *)(attached + 0x76);\n',
                    '').replace('                flags = *(volatile u8 *)(actor + 0x101);\n                *(u16 *)(actor + 0x76) = angle;',
                    '                *(u16 *)(actor + 0x76) = *(u16 *)(attached + 0x76);\n                flags = *(volatile u8 *)(actor + 0x101);')
            if destination=='wide-angle': shaped=shaped.replace('u16 angle;','u32 angle;')
            yield 'ordered-%s-%s'%(flags_type,destination),shaped


def candidates_base():
    yield 'block',BASE.replace('(u8 *)D_800CC2D0 + (u32)slot * 0x32C',
        '(u8 *)((ActorBlock58F80 *)D_800CC2D0 + slot)').replace(
        '(u8 *)D_800CC2D0 + (u32)actor[0x65] * 0x32C - 0x32C',
        '(u8 *)((ActorBlock58F80 *)D_800CC2D0 + actor[0x65] - 1)')


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD=TYPES,DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS):
        meta,words=compiler.compile_candidate(root,out,name,body,profile)
    frames=[(-word)&65535 for word in words if word>>16==0x27BD and word&0x8000]
    meta['frame']=frames[0] if frames else 0
    return meta,words


def install(before,body=SELECTED):
    assert before.count(ORIGINAL)==1
    return before.replace('#include <ultra64.h>\n','#include <ultra64.h>\n'+
        'extern s32 D_80082FA0;\n',1).replace('s32 func_1502F264();',
        'void func_1502F264(s32 slot);').replace(ORIGINAL,body)


def main():
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-actor-attachment-update'
    records=[]
    for name,body in candidates():
        for profile in compiler.PROFILES if name=='selected' else ('o2g3',):
            meta,_=compile_candidate(root,out,name+'-'+profile,body,profile)
            records.append(meta)
            print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
