"""Recover full absolute-record motion integration and its signed timestep."""
import argparse
import csv
import io
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1503EA54, 0x6BF04, 73
FUNCTION, SOURCE = 'func_1503EA54', 'conker/src/game/generated_6B320.c'
ORIGINAL = 's32 func_1503EA54() {\n    return 0;\n}'
PROTOTYPE, RECOVERED_PROTOTYPE = 's32 func_1503EA54();', 'void func_1503EA54(s32);'
DECLARATIONS = '''#include "variables.h"
extern u8 D_80098914[];
extern s8 *D_80084454[];
'''
SYMBOLS = dict(D_800C6660=0x800C6660, D_800BE9E4=0x800BE9E4,
    D_80098914=0x80098914, D_80084454=0x80084454)
PROFILES = dict(compiler.PROFILES, owner=('-O2', '-g3'), compact=('-O2', '-g3', '-Wo,-loopunroll,0'))
BASE = '''void func_1503EA54(s32 slot) {
    struct106 *control = &D_800C6660[slot];
    f32 step = D_800BE9E4;
    s32 count = D_80098914[((u8 *)control)[0xE]];
    s32 index;
    struct04 *element;

    for (index = 0; index < count; index++) {
        element = (struct04 *)control->unk0 + index;
        if (element->unk64 != 0 && D_80084454[((u8 *)control)[0xE]][index] == -1) {
            ((f32 *)element)[9] += ((f32 *)element)[18] * step;
            ((f32 *)element)[10] += ((f32 *)element)[19] * step;
            ((f32 *)element)[11] += ((f32 *)element)[20] * step;
            ((f32 *)element)[12] += ((f32 *)element)[21] * step;
            ((f32 *)element)[13] += ((f32 *)element)[22] * step;
            ((f32 *)element)[14] += ((f32 *)element)[23] * step;
            ((f32 *)element)[19] += ((f32 *)element)[24] * step;
        }
    }
}'''
GATED = BASE.replace('        element = (struct04 *)control->unk0 + index;\n', '').replace(
    'element->unk64 != 0', '((struct04 *)control->unk0)[index].unk64 != 0').replace(
    '            ((f32 *)element)[9]', '            element = (struct04 *)control->unk0 + index;\n            ((f32 *)element)[9]')
INLINE = GATED.replace('    struct106 *control = &D_800C6660[slot];\n', '').replace(
    '((u8 *)control)[0xE]', '((u8 *)&D_800C6660[slot])[0xE]').replace('control->unk0', 'D_800C6660[slot].unk0')
COUNT_FIRST = INLINE.replace('    f32 step = D_800BE9E4;\n    s32 count = D_80098914[((u8 *)&D_800C6660[slot])[0xE]];',
    '    s32 count = D_80098914[((u8 *)&D_800C6660[slot])[0xE]];\n    f32 step = D_800BE9E4;')
SELECTED = COUNT_FIRST
GUARD_ROWS = [('generated_6B320', FUNCTION, '0x118', '0x00000000', '0x00000000', '-', '-',
    'Retain unreachable retail duplicate motion return', '0x03E00008', '-', 'false')]


def candidates():
    yield 'selected', SELECTED
    yield 'count-first', BASE.replace('    f32 step = D_800BE9E4;\n    s32 count = D_80098914[((u8 *)control)[0xE]];',
        '    s32 count = D_80098914[((u8 *)control)[0xE]];\n    f32 step = D_800BE9E4;')
    yield 'nested-gates', BASE.replace('if (element->unk64 != 0 && D_80084454[((u8 *)control)[0xE]][index] == -1) {',
        'if (element->unk64 != 0) {\n        if (D_80084454[((u8 *)control)[0xE]][index] == -1) {').replace(
        '        }\n    }\n}', '        }\n        }\n    }\n}')
    yield 'explicit-count-gate', BASE.replace('    for (index = 0; index < count; index++) {',
        '    if (count > 0) {\n    for (index = 0; index < count; index++) {').replace(
        '    }\n}', '    }\n    }\n}')
    yield 'explicit-return', BASE.replace('    for (index = 0; index < count; index++) {',
        '    if (count > 0) {\n    for (index = 0; index < count; index++) {').replace(
        '    }\n}', '    }\n    return;\n    }\n}')
    yield 'float-view', BASE.replace('struct04 *element;', 'f32 *values;').replace(
        'element = (struct04 *)control->unk0 + index;', 'values = (f32 *)control->unk0 + index * 26;').replace(
        'element->unk64', '((u8 *)values)[100]').replace('((f32 *)element)', 'values')
    yield 'pointer-cursor', BASE.replace('    struct04 *element;', '    struct04 *element;\n    s32 offset = 0;').replace(
        'index++)', 'index++, offset += sizeof(struct04))').replace('(struct04 *)control->unk0 + index',
        '(struct04 *)(control->unk0 + offset)')
    yield 'gated-element', GATED
    yield 'gated-count-first', GATED.replace('    f32 step = D_800BE9E4;\n    s32 count = D_80098914[((u8 *)control)[0xE]];',
        '    s32 count = D_80098914[((u8 *)control)[0xE]];\n    f32 step = D_800BE9E4;')
    for name, body in (('plain', BASE), ('gated', GATED)):
        do = body.replace('    for (index = 0; index < count; index++) {',
            '    index = 0;\n    if (count > 0) {\n    do {').replace('    }\n}',
            '        index++;\n    } while (index != count);\n    }\n}')
        yield name+'-do', do
        yield name+'-do-return', do.replace('    }\n}', '        return;\n    }\n}')
        yield name+'-early-zero', body.replace('    for (index = 0; index < count; index++) {',
            '    if (count <= 0) {\n        return;\n    }\n    for (index = 0; index < count; index++) {')
    yield 'gated-inline-control', INLINE
    yield 'final-count-first', COUNT_FIRST
    yield 'final-return-count', COUNT_FIRST.replace('void func_', 's32 func_').replace('    }\n}', '    }\n    return count;\n}')
    yield 'final-count-guard', COUNT_FIRST.replace('    for (index = 0; index < count; index++) {',
        '    if (count > 0) {\n    for (index = 0; index < count; index++) {').replace('    }\n}', '    }\n    }\n}')
    yield 'final-else-return', COUNT_FIRST.replace('    for (index = 0; index < count; index++) {',
        '    if (count > 0) {\n    for (index = 0; index < count; index++) {').replace('    }\n}', '    }\n    } else { return; }\n}')
    yield 'final-offset', COUNT_FIRST.replace('    s32 count =', '    s32 slotOffset = slot * sizeof(struct106);\n    s32 count =').replace(
        '((u8 *)&D_800C6660[slot])[0xE]', '((u8 *)D_800C6660)[slotOffset + 0xE]').replace(
        'D_800C6660[slot].unk0', '((struct106 *)((u8 *)D_800C6660 + slotOffset))->unk0')


def compile_candidate(root, out, name, body=SELECTED, profile='owner'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS, PROFILES=PROFILES):
        return compiler.compile_candidate(root, out, name, body, profile)


def install(source):
    assert source.count(ORIGINAL) == source.count(PROTOTYPE) == 1
    assert SELECTED not in source
    return source.replace(ORIGINAL, SELECTED).replace(PROTOTYPE, RECOVERED_PROTOTYPE)


def guard_successor(data):
    rows = list(csv.DictReader(io.StringIO(data.decode('ascii'))))
    assert not any(row['function'] == FUNCTION for row in rows)
    assert data.endswith(b'\n')
    out = io.StringIO(newline='')
    csv.writer(out, lineterminator='\r\n' if data.endswith(b'\r\n') else '\n').writerows(GUARD_ROWS)
    return data+out.getvalue().encode('ascii')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    parser.add_argument('--filter', default='selected')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]; out = root/'conker/build/game-record-motion'
    records = []
    for name, body in candidates():
        if args.filter and args.filter not in name: continue
        for profile in (('owner', 'compact', 'o1g3', 'o1') if args.profiles else ('owner',)):
            meta, _ = compile_candidate(root, out, name+'-'+profile, body, profile)
            records.append(meta); print(meta['name'], meta['body_words'], meta['differences'], flush=True)
    (out/'measurements.json').write_text(json.dumps(records, indent=2)+'\n')


if __name__ == '__main__':
    main()
