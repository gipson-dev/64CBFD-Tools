"""Recover the complete main resource loader, publications and failure rollback."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1503CF20, 0x6A3D0, 274
FUNCTION, SOURCE = 'func_1503CF20', 'conker/src/game/generated_6A3D0.c'
ORIGINAL = 's32 func_1503CF20() {\n    return 0;\n}'
PROTOTYPE = 's32 func_1503CF20(s32, s32, u8 *, s32, s32);'
DECLARATIONS = '''extern u8 *D_800D19A0[];
extern u32 D_800C4020[];
extern u32 *D_800C4488[];
extern u32 *D_800C48F0[];
extern u32 D_800C4BE0[];
extern u32 *D_800C5338[];
extern u32 D_800C5048[];
extern u16 D_800C4310[];
extern u16 D_800C57A0[];
extern u16 D_800C4778[];
extern u16 D_800C5628[];
extern u16 D_800C4ED0[];
extern u8 *D_800C6360[];
extern u8 *D_800C5C08[];
extern u8 *D_800C6070[];
void *func_1502B6BC(s32 *, s32, s32 *, s32, ...);
void func_1503D438(u32 *, u32);
s32 func_1503D368();
s32 func_1503DC3C(s32);
void func_1510CE60(u32, s32, s32, s32, s32);
s32 func_1503D984();
s32 func_1503D804();
s32 func_150028BC(s32);
s32 func_1503D774(s32, s32);
s32 func_1503D660();
s32 func_1503DD1C();
void func_10004074(void *);
'''
SYMBOLS = {name:int(name[2:],16) for name in (
    'D_800D19A0','D_800C4020','D_800C4488','D_800C48F0','D_800C4BE0',
    'D_800C5338','D_800C5048','D_800C4310','D_800C57A0','D_800C4778',
    'D_800C5628','D_800C4ED0','D_800C6360','D_800C5C08','D_800C6070')}
SYMBOLS.update({name:int(name[5:],16) for name in (
    'func_1502B6BC','func_1503D438','func_1503D368','func_1503DC3C',
    'func_1510CE60','func_1503D984','func_1503D804','func_150028BC',
    'func_1503D774','func_1503D660','func_1503DD1C','func_10004074')})
SELECTED = '''s32 func_1503CF20(s32 identity, s32 unused, u8 *config, s32 extras, s32 flags) {
    s32 output;
    u32 *block;
    u8 **mainSlot;
    u32 *first;
    u32 **primary;
    u32 **secondary;
    u16 *count;
    s32 failed;
    s32 index;
    u32 boundary;
    u8 **cleanupSlot;

    if (identity == 0xFF) {
        return 0;
    }
    if (identity >= 0xBB) {
        return 0;
    }
    mainSlot = &D_800D19A0[identity];
    failed = 0;
    if (*mainSlot != NULL) {
        return 0;
    }
    block = func_1502B6BC(&output, 7, 0, 2, 1, identity);
    if (block == NULL) {
        return 1;
    }
    *mainSlot = (u8 *)block + 0x38;
    first = &D_800C4020[identity];
    *first = block[0];
    primary = &D_800C4488[identity];
    *primary = (u32 *)block[2];
    secondary = &D_800C48F0[identity];
    *secondary = (u32 *)block[10];
    D_800C4BE0[identity] = block[4];
    D_800C5338[identity] = (u32 *)block[6];
    D_800C5048[identity] = block[8];
    D_800C4310[identity] = block[1] >> 2;
    if (*first != 0) {
        boundary = *first;
    } else {
        boundary = (u32)*primary;
    }
    D_800C57A0[identity] = (boundary - (u32)block - 0x38) >> 4;
    count = &D_800C4778[identity];
    *count = block[3] >> 2;
    for (index = 0; index < *count; index++) {
        func_1503D438(&(*primary)[index], (u32)block);
        func_1503D368((*primary)[index], (u32)block);
    }
    boundary = block[11] >> 2;
    for (index = 0; (u32)index < boundary; index++) {
        func_1503D438(&(*secondary)[index], (u32)block);
        func_1503D368((*secondary)[index], (u32)block);
    }
    D_800C5628[identity] = block[7] / 12;
    D_800C4ED0[identity] = block[5] >> 4;
    if (extras != 0) {
        failed = func_1503DC3C(identity);
        if (failed == 0) {
            for (index = 0; index < *count; index++) {
                func_1510CE60((*primary)[index], 0, 0, 0x3E, 0);
            }
        }
    }
    if (failed == 0) {
        func_1503D984(identity);
        failed |= func_1503D804(identity);
    }
    if (failed == 0) {
        if (((config != NULL) && (*(u32 *)(config + 0x18) & 0x4000)) ||
            (flags & 1)) {
            if (func_150028BC(identity) != 0) {
                failed |= 8;
            }
        }
    }
    if (failed == 0) {
        failed |= func_1503D774(identity, 0);
        if (failed == 0) {
            failed |= func_1503D660(identity, 0);
        }
    }
    if (failed != 0) {
        if (D_800C6360[identity] != NULL) {
            func_10004074(D_800C6360[identity]);
        }
        func_1503DD1C(identity);
        cleanupSlot = &D_800C5C08[identity];
        if (*cleanupSlot != NULL) {
            func_10004074(*cleanupSlot);
            *cleanupSlot = NULL;
        }
        cleanupSlot = &D_800C6070[identity];
        if (*cleanupSlot != NULL) {
            func_10004074(*cleanupSlot);
            *cleanupSlot = NULL;
        }
        if (*mainSlot != NULL) {
            func_10004074(*mainSlot - 0x38);
            *mainSlot = NULL;
        }
    }
    return failed;
}'''


def compile_candidate(root, out, name, body=None, profile='retail', declarations=None):
    profiles = dict(compiler.PROFILES,retail=('-O2','-g3','-Wo,-loopunroll,0'))
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD='',DECLARATIONS=DECLARATIONS if declarations is None else declarations,
            SYMBOLS=SYMBOLS,PROFILES=profiles):
        return compiler.compile_candidate(root,out,name,QUALIFIED if body is None else body,profile)


def candidates():
    yield 'selected',SELECTED
    explicit = SELECTED.replace('    s32 index;', '    s32 index;\n    s32 offset;').replace(
        '    for (index = 0; index < *count; index++) {',
        '    offset = 0;\n    for (index = 0; index < *count; index++) {').replace(
        '    for (index = 0; (u32)index < boundary; index++) {',
        '    offset = 0;\n    for (index = 0; (u32)index < boundary; index++) {').replace(
        '&(*primary)[index]', '(u32 *)((u8 *)*primary + offset)').replace(
        '(*primary)[index]', '*(u32 *)((u8 *)*primary + offset)').replace(
        '&(*secondary)[index]', '(u32 *)((u8 *)*secondary + offset)').replace(
        '(*secondary)[index]', '*(u32 *)((u8 *)*secondary + offset)').replace(
        'func_1503D368(*(u32 *)((u8 *)*primary + offset), (u32)block);',
        'func_1503D368(*(u32 *)((u8 *)*primary + offset), (u32)block);\n        offset += 4;').replace(
        'func_1503D368(*(u32 *)((u8 *)*secondary + offset), (u32)block);',
        'func_1503D368(*(u32 *)((u8 *)*secondary + offset), (u32)block);\n        offset += 4;').replace(
        'func_1510CE60(*(u32 *)((u8 *)*primary + offset), 0, 0, 0x3E, 0);',
        'func_1510CE60(*(u32 *)((u8 *)*primary + offset), 0, 0, 0x3E, 0);\n                offset += 4;')
    yield 'explicit-offset',explicit
    gated = explicit.replace(
        '    *count = block[3] >> 2;\n    offset = 0;\n    for (index = 0; index < *count; index++) {',
        '    index = 0;\n    if ((*count = block[3] >> 2) > 0) {\n        offset = 0;\n        do {').replace(
        '        offset += 4;\n    }\n    boundary = block[11] >> 2;',
        '        index++;\n        offset += 4;\n        } while (index < *count);\n    }\n    boundary = block[11] >> 2;').replace(
        '    offset = 0;\n    for (index = 0; (u32)index < boundary; index++) {',
        '    index = 0;\n    offset = 0;\n    if (boundary != 0) {\n        do {').replace(
        '        offset += 4;\n    }\n    D_800C5628',
        '        index++;\n        offset += 4;\n        } while ((u32)index < boundary);\n    }\n    D_800C5628')
    for prefix in ('func_1503D438(', 'func_1503D368(', 'index++;', 'offset += 4;'):
        gated=gated.replace('\n        '+prefix,'\n            '+prefix)
    gated=gated.replace('        if (failed == 0) {\n            offset = 0;\n    for',
        '        if (failed == 0) {\n            offset = 0;\n            for').replace(
        '        if (failed == 0) {\n        offset = 0;\n    for',
        '        if (failed == 0) {\n            offset = 0;\n            for').replace(
        '        if (failed == 0) {\n    offset = 0;\n    for',
        '        if (failed == 0) {\n            offset = 0;\n            for')
    yield 'gated-loops',gated
    yield 'explicit-register-error',explicit.replace('    s32 failed;', '    register s32 failed;')
    yield 'gated-register-error',gated.replace('    s32 failed;', '    register s32 failed;')
    yield 'gated-error-assign',gated.replace('failed |= func_', 'failed = func_')
    for name,body in (('selected',SELECTED),('explicit',explicit),('gated',gated)):
        yield name+'-late-error',body.replace('    failed = 0;\n','').replace(
            '    if (extras != 0)', '    failed = 0;\n    if (extras != 0)')
    for name,body in (('explicit',explicit),('gated',gated)):
        yield name+'-unsigned-error',body.replace('    s32 failed;', '    u32 failed;')
        yield name+'-output-array',body.replace('    s32 output;', '    s32 output[1];').replace(
            'func_1502B6BC(&output,', 'func_1502B6BC(output,')
        yield name+'-unsigned-output',body.replace('    s32 output;', '    u32 output;').replace(
            'func_1502B6BC(&output,', 'func_1502B6BC((s32 *)&output,')
    for name,body in (('selected',SELECTED),('gated',gated)):
        yield name+'-failed-first',body.replace('    s32 failed;\n','').replace(
            '    s32 output;', '    s32 failed;\n    s32 output;')
        yield name+'-failed-last',body.replace('    s32 failed;\n','').replace(
            '    u8 **cleanupSlot;', '    u8 **cleanupSlot;\n    s32 failed;')


QUALIFIED = dict(candidates())['gated-late-error']


def install(before,body=None):
    if before.count(ORIGINAL)!=1 or before.count('s32 func_1503CF20();')!=1:
        raise ValueError('stale main resource loader owner/interface')
    existing = {line for line in before.split(ORIGINAL,1)[0].splitlines() if line.endswith(';')}
    additions = '\n'.join(line for line in DECLARATIONS.splitlines() if line not in existing)
    return before.replace('s32 func_1503CF20();',PROTOTYPE).replace(
        'void func_150028BC(s32);','s32 func_150028BC(s32);').replace(
        ORIGINAL,additions+'\n\n'+(QUALIFIED if body is None else body))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variants',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-main-resource-loader'
    records=[]
    for name,body in candidates() if args.variants else [('qualified',QUALIFIED)]:
        meta,_=compile_candidate(root,out,name,body)
        records.append(meta)
        print(name,meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
