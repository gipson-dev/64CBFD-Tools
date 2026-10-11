"""Complete actor animation selector transition, retained callback values and mode reads."""
import json
import argparse
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY,ROM,WORDS=0x1502FBE8,0x5D098,98
FUNCTION,SOURCE='func_1502FBE8','conker/src/game/generated_58F80.c'
ORIGINAL='s32 func_1502FBE8() {\n    return 0;\n}'
DECLARATIONS='''extern u8 D_800CC2D0[];
extern u32 D_800D1588[];
extern u16 D_800C5A90[];
extern u8 D_800C35EA, D_800C3638;
void func_150837D4(s32, s32, s32);
void func_1505E650(u8 *, u16, f32, f32, f32, f32, s32);
void func_1507EABC(u8 *);
'''
SYMBOLS=dict(D_800CC2D0=0x800CC2D0,D_800D1588=0x800D1588,D_800C5A90=0x800C5A90,
    D_800C35EA=0x800C35EA,D_800C3638=0x800C3638,func_150837D4=0x150837D4,
    func_1505E650=0x1505E650,func_1507EABC=0x1507EABC)
SELECTED='''void func_1502FBE8(u8 *actor) {
    s32 index, mode;
    u32 resource;
    u8 animation;
    u16 frame;

    index = actor[0x1C9];
    if (index != 0) {
        resource = D_800D1588[actor[4]];
        if (index == 255) {
            actor[0x1C9] = 0;
            index = 0;
        } else {
            index--;
            if (index >= actor[0x2C9] || index == actor[0x1C8]) {
                return;
            }
        }
        animation = (*(u8 **)(actor + 0x2C4))[index];
        func_150837D4((s32)((u32)actor - (u32)D_800CC2D0) / 0x32C, animation, 0);
        actor[0x1C8] = index;
        mode = D_800C35EA;
        if (mode == 1) {
            D_800C3638 = 0;
        }
        if (resource != D_800D1588[animation]) {
            frame = *(u16 *)(actor + 0x84);
            if (frame >= D_800C5A90[animation]) {
                *(u16 *)(actor + 0x84) = 0xFFFF;
                func_1505E650(actor, 0, 1.0f, 0.0f, 0.0f, 0.0f, 0);
            } else {
                *(u16 *)(actor + 0x84) = 0xFFFF;
                func_1505E650(actor, frame, 1.0f, 0.0f, 0.0f, 0.0f, 0);
            }
            mode = D_800C35EA;
        }
        if (mode == 1) {
            D_800C3638 = 1;
        }
        func_1507EABC(actor);
    }
}'''


def candidates():
    yield 'selected',SELECTED
    for index in ('s32','u32','u8'):
        for animation in ('u8','s32','u32'):
            yield 'types-'+index+'-'+animation,SELECTED.replace('s32 index, mode;',
                index+' index;\n    s32 mode;').replace('u8 animation;',animation+' animation;')
    yield 'early-empty',SELECTED.replace('    if (index != 0) {',
        '    if (index == 0) { return; }\n    {')
    yield 'signed-pointer-distance',SELECTED.replace('(s32)((u32)actor - (u32)D_800CC2D0)',
        '(actor - (u8 *)D_800CC2D0)')
    yield 'divide-before-byte',SELECTED.replace('s32 index, mode;', 's32 index, mode, slot;').replace(
        '        animation =', '        slot = (s32)((u32)actor - (u32)D_800CC2D0) / 0x32C;\n        animation =').replace(
        'func_150837D4((s32)((u32)actor - (u32)D_800CC2D0) / 0x32C,', 'func_150837D4(slot,')
    yield 'captured-pending',SELECTED.replace('s32 index, mode;', 's32 index, mode;\n    u8 pending;').replace(
        '    index = actor[0x1C9];','    pending = actor[0x1C9];\n    index = pending;')
    for animation in ('s32','u8'):
        for frame in ('s32','u32','u16'):
            body=SELECTED.replace('u8 animation;',animation+' animation;').replace(
                'u16 frame;',frame+' frame;')
            yield 'retained-'+animation+'-'+frame,body
            yield 'pending-'+animation+'-'+frame,body.replace('s32 index, mode;',
                's32 index, mode, pending;').replace('    index = actor[0x1C9];',
                '    pending = actor[0x1C9];\n    index = pending;')
    body=SELECTED.replace('u8 animation;', 's32 animation;').replace('u16 frame;','s32 frame;')
    for separate in (False,True):
        shaped=body
        if separate:
            shaped=shaped.replace('s32 index, mode;', 's32 index, mode, pending;').replace(
                '    index = actor[0x1C9];\n    if (index != 0)',
                '    pending = actor[0x1C9];\n    if (pending != 0)').replace(
                'if (index == 255)', 'if (pending == 255)').replace('            index--;',
                '            index = pending - 1;')
        yield 'focused-separate-'+str(separate),shaped
        for branch_reads in (True,False):
            new=shaped
            if branch_reads:
                new=new.replace('            mode = D_800C35EA;\n','').replace(
                    '0.0f, 0.0f, 0.0f, 0);','0.0f, 0.0f, 0.0f, 0);\n                mode = D_800C35EA;')
            else:
                new=new.replace('            mode = D_800C35EA;','            mode = D_800C35EA;\n            if (mode == 1) { D_800C3638 = 1; }').replace(
                    '        }\n        if (mode == 1) {\n            D_800C3638 = 1;\n        }',
                    '        } else if (mode == 1) {\n            D_800C3638 = 1;\n        }')
            yield 'focused-reads-'+str(separate)+'-'+str(branch_reads),new


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD='',DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root,out,name,body,profile)


def copied_owner(before,body=SELECTED):
    if before.count(ORIGINAL)!=1 or before.count('s32 func_1502FBE8();')!=1 or\
            before.count('        func_1502FBE8(actor);')!=1:
        raise ValueError('stale actor animation selector owner')
    declarations='''extern u32 D_800D1588[];
extern u16 D_800C5A90[];
void func_1505E650(u8 *, u16, f32, f32, f32, f32, s32);
void func_1507EABC(u8 *);

'''
    return before.replace('s32 func_1502FBE8();','void func_1502FBE8(u8 *);').replace(
        '        func_1502FBE8(actor);','        func_1502FBE8((u8 *)actor);').replace(ORIGINAL,declarations+body)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--focused',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];out=root/'conker/build/game-actor-animation-selector'
    records=[]
    for name,body in candidates():
        if args.focused and not name.startswith('focused-'):continue
        meta,words=compile_candidate(root,out,name,body)
        records.append(meta);print(name,meta['body_words'],meta['frame'],meta['differences'],flush=True)
    (out/('focused.json' if args.focused else 'measurements.json')).write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
