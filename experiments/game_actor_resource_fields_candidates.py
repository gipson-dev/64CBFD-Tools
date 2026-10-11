"""Complete actor resource fields, optional configuration and live byte copies."""
import itertools
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x150839B8, 0xB0E68, 68
FUNCTION, SOURCE = 'func_150839B8', 'conker/src/game/generated_AEB40.c'
ORIGINAL = 's32 func_150839B8() {\n    return 0;\n}'
DECLARATIONS = '''extern u8 *D_800D1C90[];
extern s32 D_800BE9F0;
extern u32 D_80086CAC[];
void func_15036C70(u8 *);
'''
SYMBOLS = dict(D_800D1C90=0x800D1C90, D_800BE9F0=0x800BE9F0,
    D_80086CAC=0x80086CAC, func_15036C70=0x15036C70)
SELECTED = '''void func_150839B8(u8 *actor, s32 identity, u8 *configuration) {
    u8 *resource;
    u16 value;

    if (identity != 255) {
        resource = D_800D1C90[identity];
        if (configuration != NULL) {
            value = *(u16 *)(configuration + 0x2C);
            if (value == 0) {
                *(u16 *)(actor + 0x10) = *(u16 *)(resource + 0x2A);
            } else if (value == 1) {
                *(u16 *)(actor + 0x10) = 0;
            } else {
                *(u16 *)(actor + 0x10) = value;
            }
            if (D_800BE9F0 == 0x1D) {
                *(u16 *)(actor + 0x10) = 1000;
            }
        } else {
            *(u16 *)(actor + 0x10) = 0;
        }
        actor[0x13B] = resource[0x39];
        actor[0x2CB] = *(s8 *)(resource + 0x33);
        *(u32 *)(actor + 0x2CC) = *(u32 *)(resource + 0x34);
        actor[5] = resource[0x12];
        actor[0x68] = resource[0x3B];
        actor[0x69] = resource[0x3C];
        *(s16 *)(actor + 0x160) = *(s16 *)(resource + 2);
        if (resource[4] != 0) {
            *(u32 *)(actor + 0x2C4) = D_80086CAC[resource[5]];
            actor[0x2C8] = resource[4];
        }
        actor[0x2C9] = resource[0x38] + actor[0x2C8];
        if (resource[0x29] != 0) {
            func_15036C70(actor);
        }
    }
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'reverse-load-order', SELECTED.replace('resource[0x38] + actor[0x2C8]', 'actor[0x2C8] + resource[0x38]')
    for width, reused, live in itertools.product(('u16', 's32', 'u32'), (False, True), (False, True)):
        body = SELECTED.replace('    u16 value;', '    '+width+' value;')
        if reused:
            body = body.replace('    '+width+' value;\n', '').replace('value', 'identity')
        if live:
            body = body.replace(' + actor[0x2C8]', ' + *(volatile u8 *)(actor + 0x2C8)')
        yield 'value-%s-reuse%d-live%d' % (width, reused, live), body
    yield 'unsigned-identity', SELECTED.replace('s32 identity', 'u32 identity')
    yield 'unsigned-fields', SELECTED.replace('*(s8 *)(resource + 0x33)', 'resource[0x33]').replace(
        '(s16 *)(actor + 0x160)', '(u16 *)(actor + 0x160)').replace('(s16 *)(resource + 2)', '(u16 *)(resource + 2)')
    yield 'early-return', SELECTED.replace('    if (identity != 255) {', '    if (identity == 255) return;\n    {')
    yield 'volatile-counts', SELECTED.replace('resource[4]', '*(volatile u8 *)(resource + 4)').replace(
        ' + actor[0x2C8]', ' + *(volatile u8 *)(actor + 0x2C8)')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, profile)


def install(before, body=SELECTED):
    if before.count(ORIGINAL) != 1 or before.count('s32 func_150839B8();') != 1:
        raise ValueError('stale actor resource fields owner')
    extra = 'extern u32 D_80086CAC[];\nvoid func_15036C70(u8 *);\n\n'
    return before.replace(ORIGINAL, extra+body).replace('s32 func_150839B8();\n', '')


def main():
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-actor-resource-fields'
    records = []
    for name, body in candidates():
        meta, _ = compile_candidate(root, out, name, body)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out/'measurements.json').write_text(json.dumps(records, indent=2)+'\n')


if __name__ == '__main__':
    main()
