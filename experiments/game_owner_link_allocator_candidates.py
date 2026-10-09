"""Recover the owner-link allocator's mixed O32 ABI and derived float fields."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x151B30B0, 0x1E0560, 53
FUNCTION = 'func_151B30B0'
SOURCE = 'conker/src/game/generated_1E0560.c'
ORIGINAL = 's32 func_151B30B0() {\n    return 0;\n}'
DECLARATIONS = '''extern f32 D_800AA390;
void *func_15167A68(s32, s32, s32, s32, u8, u8);
void *memcpy(void *, const void *, u32);
'''
SYMBOLS = dict(D_800AA390=0x800AA390,func_15167A68=0x15167A68,
    memcpy=0x10022EC0,bzero=0x100226F0)
SELECTED = '''u8 *func_151B30B0(void *request, f32 parameter, s32 extraBytes, u8 slot, s32 context) {
    u8 *created;
    f32 distance;
    f32 scaled;

    created = func_15167A68(0x33, context, extraBytes + 0x150, 1, slot, 1);
    if (created == NULL) {
        return NULL;
    }
    memcpy(created + 0x10, request, 56);
    distance = *(f32 *)(created + 0x38);
    created[0x10] |= 0xE;
    scaled = distance * distance / D_800AA390;
    *(f32 *)(created + 0x138) = scaled + scaled;
    *(s32 *)(created + 0x13C) = (s32)(distance * parameter * 4096.0f);
    bzero(created + 0x140, 16);
    return created;
}'''


def candidates():
    yield 'selected',SELECTED
    yield 'positive-gate',SELECTED.replace('    if (created == NULL) {\n        return NULL;\n    }\n',
        '    if (created != NULL) {\n').replace('    return created;','    }\n    return created;')
    yield 'float-first',SELECTED.replace('    u8 *created;\n    f32 distance;\n    f32 scaled;',
        '    f32 distance;\n    f32 scaled;\n    u8 *created;')
    yield 'volatile-parameter',SELECTED.replace('f32 parameter,','volatile f32 parameter,')
    yield 'volatile-arguments',SELECTED.replace('void *request,','void *volatile request,').replace(
        'f32 parameter,','volatile f32 parameter,').replace('s32 extraBytes,','volatile s32 extraBytes,').replace(
        'u8 slot,','volatile u8 slot,')
    yield 'scaled-inline',SELECTED.replace('    scaled = distance * distance / D_800AA390;\n'
        '    *(f32 *)(created + 0x138) = scaled + scaled;',
        '    *(f32 *)(created + 0x138) = 2.0f * (distance * distance / D_800AA390);')
    yield 'negative-wrong-distance',SELECTED.replace('created + 0x38','created + 0x30')
    yield 'negative-short-copy',SELECTED.replace('request, 56','request, 52')
    yield 'negative-return-copy',SELECTED.replace('    memcpy(created + 0x10, request, 56);',
        '    created = memcpy(created + 0x10, request, 56);')
    yield 'negative-small-allocation',SELECTED.replace('extraBytes + 0x150','extraBytes + 0x140')
    yield 'negative-wrong-scale',SELECTED.replace('4096.0f','2048.0f')


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    out.mkdir(parents=True,exist_ok=True)
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD='',DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root,out,name,body,profile)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-owner-link-allocator'
    records=[]
    for name,body in candidates():
        for profile in compiler.PROFILES if args.profiles else ('o2g3',):
            meta,_=compile_candidate(root,out,name+'-'+profile,body,profile)
            records.append(meta)
            print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__ == '__main__':
    main()
