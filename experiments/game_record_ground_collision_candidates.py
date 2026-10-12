"""Recover active-record floor clamping, bounce damping and settling."""
import argparse
import csv
import io
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1503ECA0, 0x6C150, 134
FUNCTION, SOURCE = 'func_1503ECA0', 'conker/src/game/generated_6B320.c'
ORIGINAL = 's32 func_1503ECA0() {\n    return 0;\n}'
LOCAL_DECLARATIONS = '''extern f32 D_80098928;
extern f32 D_8009892C;
void func_1510F800(s32);
s32 func_1510F8D8(s32, s32, s32, s32);
'''
DECLARATIONS = '''#include "variables.h"
extern u8 D_80098914[];
extern s8 *D_80084454[];
'''+LOCAL_DECLARATIONS
SYMBOLS = dict(D_800C6660=0x800C6660, D_80098914=0x80098914, D_80084454=0x80084454,
    D_80098928=0x80098928, D_8009892C=0x8009892C, func_1510F800=0x1510F800, func_1510F8D8=0x1510F8D8)
PROFILES = dict(compiler.PROFILES, owner=('-O2', '-g3'), compact=('-O2', '-g3', '-Wo,-loopunroll,0'))
BASE = '''void func_1503ECA0(s32 slot) {
    struct106 *control;
    struct04 *element;
    s32 count;
    s32 index;
    f32 height;
    f32 angularDamping;
    f32 linearDamping;

    func_1510F800(0);
    control = &D_800C6660[slot];
    count = D_80098914[((u8 *)control)[0xE]];
    angularDamping = D_80098928;
    linearDamping = D_8009892C;
    for (index = 0; index < count; index++) {
        if (((struct04 *)control->unk0)[index].unk64 != 0) {
            element = (struct04 *)control->unk0 + index;
            if (D_80084454[((u8 *)control)[0xE]][index] == -1 &&
                    ((f32 *)element)[24] != 0.0f) {
                height = func_1510F8D8((s32)((f32 *)element)[9],
                    (s32)((f32 *)element)[10], (s32)((f32 *)element)[11], 0) + 5;
                if (((f32 *)element)[10] < height) {
                    ((f32 *)element)[10] = height;
                    if (((f32 *)element)[19] < -4.0f) {
                        ((f32 *)element)[18] *= linearDamping;
                        ((f32 *)element)[19] *= -0.5f;
                        ((f32 *)element)[20] *= linearDamping;
                        ((f32 *)element)[21] *= -1.0f;
                        ((f32 *)element)[22] *= angularDamping;
                        ((f32 *)element)[23] *= -1.0f;
                    } else {
                        ((f32 *)element)[23] = ((f32 *)element)[22] =
                            ((f32 *)element)[21] = ((f32 *)element)[24] =
                            ((f32 *)element)[20] = ((f32 *)element)[19] =
                            ((f32 *)element)[18] = 0.0f;
                    }
                }
            }
        }
    }
}'''
SELECTED = BASE
SEPARATE = BASE.replace('''                        ((f32 *)element)[23] = ((f32 *)element)[22] =
                            ((f32 *)element)[21] = ((f32 *)element)[24] =
                            ((f32 *)element)[20] = ((f32 *)element)[19] =
                            ((f32 *)element)[18] = 0.0f;''',
    '\n'.join('                        ((f32 *)element)[%d] = 0.0f;' % i for i in (23,22,21,24,20,19,18)))
GATED_DO = SEPARATE.replace('    angularDamping =', '    index = 0;\n    if (count > 0) {\n    angularDamping =').replace(
    '    for (index = 0; index < count; index++) {', '    do {').replace('    }\n}',
    '        index++;\n    } while (index != count);\n    }\n}')
lines = GATED_DO.splitlines()
begin = lines.index('    if (count > 0) {')+1
SELECTED = '\n'.join(lines[:begin]+['    '+line for line in lines[begin:-2]]+lines[-2:])
GUARD_ROWS = [('generated_6B320', FUNCTION, offset, expected, replacement, old, new,
    'Normalize closed collision constant initialization and FPR allocation', '', '', 'false')
    for offset, expected, replacement, old, new in (
        ('0x6C','0x3C010000','0x00009025','R_MIPS_HI16:D_80098928','-'),
        ('0x70','0x00009025','0x3C010000','-','R_MIPS_HI16:D_80098928'),
        ('0x80','0x3C010000','0x3C01BF00','R_MIPS_HI16:D_8009892C','-'),
        ('0x84','0xC4380000','0x4481E000','R_MIPS_LO16:D_8009892C','-'),
        ('0x88','0x3C01BF00','0x3C01C080','-','-'),
        ('0x8C','0x4481E000','0x4481D000','-','-'),
        ('0x90','0x3C01C080','0x3C01BF80','-','-'),
        ('0x94','0x4481D000','0x4481C000','-','-'),
        ('0x98','0x3C01BF80','0x3C010000','-','R_MIPS_HI16:D_8009892C'),
        ('0x9C','0x4481B000','0x4480A000','-','-'),
        ('0xA0','0x4480A000','0xC4360000','-','R_MIPS_LO16:D_8009892C'),
        ('0x16C','0x46185402','0x46165402','-','-'),
        ('0x17C','0x46182182','0x46162182','-','-'),
        ('0x188','0x46164282','0x46184282','-','-'),
        ('0x19C','0x46162182','0x46182182','-','-'))]


def candidates():
    yield 'selected', SELECTED
    yield 'gate-do-separate', GATED_DO
    yield 'gate-do-scoped', GATED_DO.replace('    f32 angularDamping;\n    f32 linearDamping;\n', '').replace(
        '    angularDamping =', '    f32 angularDamping =').replace('    linearDamping =', '    f32 linearDamping =')
    yield 'gate-do-index-late', GATED_DO.replace('    index = 0;\n', '').replace(
        '    do {', '    index = 0;\n    do {')
    yield 'gate-do-linear-first', GATED_DO.replace('    angularDamping = D_80098928;\n    linearDamping = D_8009892C;',
        '    linearDamping = D_8009892C;\n    angularDamping = D_80098928;')
    early = GATED_DO.replace('    if (count > 0) {', '    if (count <= 0) { return; }').replace(
        '    } while (index != count);\n    }\n}', '    } while (index != count);\n}')
    yield 'final-early-zero', early
    yield 'final-early-for', early.replace('    do {', '    for (; index < count; index++) {').replace(
        '        index++;\n    } while (index != count);', '    }')
    yield 'final-loop-offset', GATED_DO.replace('    s32 index;', '    s32 index;\n    s32 offset = 0;').replace(
        '((struct04 *)control->unk0)[index].unk64', '((struct04 *)(control->unk0 + offset))->unk64').replace(
        '(struct04 *)control->unk0 + index', '(struct04 *)(control->unk0 + offset)').replace('        index++;',
        '        index++;\n        offset += 0x68;')
    yield 'final-combined-zero', GATED_DO.replace('    index = 0;\n', '').replace('    count =', '    index = 0;\n    count =')
    yield 'gate-do-type-switch', GATED_DO.replace('if (D_80084454[((u8 *)control)[0xE]][index] == -1 &&\n                    ((f32 *)element)[24] != 0.0f) {',
        'switch (D_80084454[((u8 *)control)[0xE]][index]) {\n            case -1:\n            if (((f32 *)element)[24] != 0.0f) {').replace(
        '            }\n        }\n        index++;', '            }\n            break;\n            }\n        }\n        index++;')
    for selected in (('restitution',), ('reverse',), ('restitution', 'threshold', 'reverse', 'zero')):
        body = GATED_DO
        definitions = {'restitution': '-0.5f', 'threshold': '-4.0f', 'reverse': '-1.0f', 'zero': '0.0f'}
        for name in selected:
            body = body.replace(definitions[name], name)
        declaration = '\n'.join('    f32 '+name+';' for name in selected)
        initialization = '\n'.join('    '+name+' = '+definitions[name]+';' for name in selected)
        body = body.replace('    f32 height;', '    f32 height;\n'+declaration).replace(
            '    linearDamping =', initialization+'\n    linearDamping =')
        yield 'named-constants-'+'-'.join(selected), body
    for order in ((23,22,21,24,20,19,18), (18,19,20,21,22,23,24), (24,23,22,21,20,19,18)):
        old = '\n'.join('                        ((f32 *)element)[%d] = 0.0f;' % i for i in (23,22,21,24,20,19,18))
        new = '\n'.join('                        ((f32 *)element)[%d] = 0.0f;' % i for i in order)
        yield 'settle-order-'+str(order[0]), GATED_DO.replace(old, new)
    yield 'separate-zero', BASE.replace('''                        ((f32 *)element)[23] = ((f32 *)element)[22] =
                            ((f32 *)element)[21] = ((f32 *)element)[24] =
                            ((f32 *)element)[20] = ((f32 *)element)[19] =
                            ((f32 *)element)[18] = 0.0f;''',
        '\n'.join('                        ((f32 *)element)[%d] = 0.0f;' % i for i in (23,22,21,24,20,19,18)))
    yield 'constant-count-gate', BASE.replace('    angularDamping =', '    if (count > 0) {\n    angularDamping =').replace(
        '    }\n}', '    }\n    }\n}')
    yield 'scoped-constants', BASE.replace('    f32 angularDamping;\n    f32 linearDamping;\n', '').replace(
        '    angularDamping = D_80098928;\n    linearDamping = D_8009892C;',
        '    if (count > 0) {\n    f32 angularDamping = D_80098928;\n    f32 linearDamping = D_8009892C;').replace(
        '    }\n}', '    }\n    }\n}')
    yield 'gated-element', BASE.replace('            element = (struct04 *)control->unk0 + index;\n', '').replace(
        '((f32 *)element)[24] != 0.0f', '((f32 *)((struct04 *)control->unk0 + index))[24] != 0.0f').replace(
        '                height =', '                element = (struct04 *)control->unk0 + index;\n                height =')
    yield 'nested-type', BASE.replace('if (D_80084454[((u8 *)control)[0xE]][index] == -1 &&\n                    ((f32 *)element)[24] != 0.0f) {',
        'if (D_80084454[((u8 *)control)[0xE]][index] == -1) {\n            if (((f32 *)element)[24] != 0.0f) {').replace(
        '            }\n        }\n    }', '            }\n            }\n        }\n    }')
    yield 'cached-velocity', BASE.replace('    f32 height;', '    f32 height;\n    f32 velocity;').replace(
        '                    if (((f32 *)element)[19] < -4.0f) {',
        '                    velocity = ((f32 *)element)[19];\n                    if (velocity < -4.0f) {').replace(
        '((f32 *)element)[19] *= -0.5f;', '((f32 *)element)[19] = velocity * -0.5f;')
    yield 'explicit-do', BASE.replace('    for (index = 0; index < count; index++) {',
        '    index = 0;\n    if (count > 0) {\n    do {').replace('    }\n}', '        index++;\n    } while (index < count);\n    }\n}')
    for local in ('struct106 *control;', 'struct04 *element;', 's32 count;', 's32 index;',
            'f32 height;', 'f32 angularDamping;', 'f32 linearDamping;'):
        yield 'local-first-'+local.split()[-1][:-1].replace('*', ''), BASE.replace('    '+local+'\n', '').replace(
            'void func_1503ECA0(s32 slot) {\n', 'void func_1503ECA0(s32 slot) {\n    '+local+'\n')


def compile_candidate(root, out, name, body=SELECTED, profile='owner'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS, PROFILES=PROFILES):
        return compiler.compile_candidate(root, out, name, body, profile)


def install(source):
    assert source.count(ORIGINAL) == 1 and SELECTED not in source
    assert LOCAL_DECLARATIONS.rstrip() not in source
    return source.replace(ORIGINAL, SELECTED).replace('#include "variables.h"\n',
        '#include "variables.h"\n'+LOCAL_DECLARATIONS, 1)


def guard_successor(data):
    rows = list(csv.DictReader(io.StringIO(data.decode('ascii'))))
    assert not any(row['function'] == FUNCTION for row in rows)
    assert data.endswith(b'\n')
    out = io.StringIO(newline='')
    csv.writer(out, lineterminator='\r\n' if data.endswith(b'\r\n') else '\n').writerows(GUARD_ROWS)
    return data+out.getvalue().encode('ascii')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='selected')
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]; out = root/'conker/build/game-record-ground-collision'
    records = []
    for name, body in candidates():
        if args.filter and args.filter not in name: continue
        for profile in (('owner', 'compact', 'o1g3', 'o1') if args.profiles else ('owner',)):
            meta, _ = compile_candidate(root, out, name+'-'+profile, body, profile)
            records.append(meta); print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records, indent=2)+'\n')


if __name__ == '__main__':
    main()
