"""Recover the signed gate, live backward ring cursor and raw coordinate output."""

import argparse
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151D792C, 0x204DDC, 67
FUNCTION = 'func_151D792C'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_204660/func_151D792C.s")'
DECLARATIONS = '''typedef struct {
    f32 x, y, z;
} RingPosition151D792C;

typedef struct {
    RingPosition151D792C position;
    f32 velocity;
    u8 remaining[12];
} RingRecord151D792C;

extern f32 D_800BE9A4;
void func_151D8718(f32 *, f32 *, f32);
'''
SYMBOLS = {'D_800BE9A4': 0x800BE9A4, 'func_151D8718': 0x151D8718}
BASE = '''s32 func_151D792C(u8 *owner) {
    s32 state;
    u8 *records;
    s32 cursor;

    state = *(s8 *)(owner + 0x2C);
    records = *(u8 **)(owner + 0x94);
    if (state < 2 && (*(u16 *)(owner + 0x1E) & 8)) {
        return 0;
    }
    cursor = *(s8 *)(owner + 0x2E);
    while (cursor != *(s8 *)(owner + 0x2D)) {
        cursor--;
        if (cursor < 0) {
            cursor = owner[0x25] - 1;
        }
        func_151D8718((f32 *)(records + cursor * 0x1C),
                     (f32 *)(records + cursor * 0x1C + 0xC), D_800BE9A4);
    }
    if (*(s8 *)(owner + 0x2C) > 0) {
        *(RingPosition151D792C *)(owner + 0x54) =
            *(RingPosition151D792C *)(records + *(s8 *)(owner + 0x2D) * 0x1C);
    } else {
        *(f32 *)(owner + 0x54) = 0.0f;
        *(f32 *)(owner + 0x58) = 0.0f;
        *(f32 *)(owner + 0x5C) = 0.0f;
    }
    return 1;
}'''

SELECTED = BASE.replace('        *(RingPosition151D792C *)(owner + 0x54) =\n            *(RingPosition151D792C *)(records + *(s8 *)(owner + 0x2D) * 0x1C);',
    '        RingPosition151D792C *position = (RingPosition151D792C *)(records + *(s8 *)(owner + 0x2D) * 0x1C);\n        *(RingPosition151D792C *)(owner + 0x54) = *position;')


def candidates():
    yield 'selected', SELECTED
    yield 'inline-output', BASE
    yield 'declarations-record-first', BASE.replace('    s32 state;\n    u8 *records;', '    u8 *records;\n    s32 state;')
    yield 'declarations-cursor-first', BASE.replace('    s32 cursor;\n', '').replace('    s32 state;', '    s32 cursor;\n    s32 state;')
    yield 'register-cursor', BASE.replace('s32 cursor;', 'register s32 cursor;')
    yield 'count-cast', BASE.replace('owner[0x25] - 1', '(s32)owner[0x25] - 1')
    yield 'pre-decrement', BASE.replace('cursor--;', '--cursor;')
    yield 'for-loop', BASE.replace('while (cursor != *(s8 *)(owner + 0x2D))', 'for (; cursor != *(s8 *)(owner + 0x2D);)')
    yield 'buffer-before-state', BASE.replace('    state = *(s8 *)(owner + 0x2C);\n    records = *(u8 **)(owner + 0x94);', '    records = *(u8 **)(owner + 0x94);\n    state = *(s8 *)(owner + 0x2C);')
    yield 'record-local', BASE.replace('    s32 cursor;', '    s32 cursor;\n    f32 *record;').replace(
        '        func_151D8718((f32 *)(records + cursor * 0x1C),\n                     (f32 *)(records + cursor * 0x1C + 0xC), D_800BE9A4);',
        '        record = (f32 *)(records + cursor * 0x1C);\n        func_151D8718(record, record + 3, D_800BE9A4);')
    yield 'goal-local', BASE.replace('    s32 cursor;', '    s32 cursor;\n    s32 goal;').replace(
        'cursor != *(s8 *)(owner + 0x2D)', 'cursor != (goal = *(s8 *)(owner + 0x2D))').replace(
        'records + *(s8 *)(owner + 0x2D) * 0x1C', 'records + goal * 0x1C')
    yield 'output-per-axis', BASE.replace(
        '        *(RingPosition151D792C *)(owner + 0x54) =\n            *(RingPosition151D792C *)(records + *(s8 *)(owner + 0x2D) * 0x1C);',
        '        f32 *position = (f32 *)(records + *(s8 *)(owner + 0x2D) * 0x1C);\n        *(f32 *)(owner + 0x54) = position[0];\n        *(f32 *)(owner + 0x58) = position[1];\n        *(f32 *)(owner + 0x5C) = position[2];')
    yield 'zeros-chain', BASE.replace(
        '        *(f32 *)(owner + 0x54) = 0.0f;\n        *(f32 *)(owner + 0x58) = 0.0f;\n        *(f32 *)(owner + 0x5C) = 0.0f;',
        '        *(f32 *)(owner + 0x54) = *(f32 *)(owner + 0x58) = *(f32 *)(owner + 0x5C) = 0.0f;')
    yield 'old-style', BASE.replace('s32 func_151D792C(u8 *owner)', 's32 func_151D792C(owner)\nu8 *owner;')
    copy = '        *(RingPosition151D792C *)(owner + 0x54) =\n            *(RingPosition151D792C *)(records + *(s8 *)(owner + 0x2D) * 0x1C);'
    zero = '        *(f32 *)(owner + 0x54) = 0.0f;\n        *(f32 *)(owner + 0x58) = 0.0f;\n        *(f32 *)(owner + 0x5C) = 0.0f;'
    tail = '    if (*(s8 *)(owner + 0x2C) > 0) {\n' + copy + '\n    } else {\n' + zero + '\n    }'
    yield 'zero-first', BASE.replace(tail, '    if (*(s8 *)(owner + 0x2C) <= 0) {\n' + zero + '\n    } else {\n' + copy + '\n    }')
    yield 'zero-return', BASE.replace(tail, '    if (*(s8 *)(owner + 0x2C) <= 0) {\n' + zero + '\n        return 1;\n    }\n' + copy)
    yield 'copy-return', BASE.replace(tail, '    if (*(s8 *)(owner + 0x2C) > 0) {\n' + copy + '\n        return 1;\n    }\n' + zero)
    yield 'copy-block-pointer', BASE.replace(copy, '        RingPosition151D792C *position = (RingPosition151D792C *)(records + *(s8 *)(owner + 0x2D) * 0x1C);\n        *(RingPosition151D792C *)(owner + 0x54) = *position;')
    yield 'copy-function-pointer', BASE.replace('    s32 cursor;', '    s32 cursor;\n    RingPosition151D792C *position;').replace(copy, '        position = (RingPosition151D792C *)(records + *(s8 *)(owner + 0x2D) * 0x1C);\n        *(RingPosition151D792C *)(owner + 0x54) = *position;')
    yield 'explicit-stride', BASE.replace('    s32 cursor;', '    s32 cursor;\n    s32 stride = 0x1C;').replace('* 0x1C', '* stride')
    yield 'goal-stride-product', BASE.replace('records + *(s8 *)(owner + 0x2D) * 0x1C', '*(s8 *)(owner + 0x2D) * 0x1C + records')
    yield 'state-assignment', BASE.replace('if (*(s8 *)(owner + 0x2C) > 0)', 'if ((state = *(s8 *)(owner + 0x2C)) > 0)')
    typed = BASE.replace('u8 *records;', 'RingRecord151D792C *records;').replace('*(u8 **)(owner + 0x94)', '*(RingRecord151D792C **)(owner + 0x94)').replace(
        '(f32 *)(records + cursor * 0x1C)', '&records[cursor].position.x').replace(
        '(f32 *)(records + cursor * 0x1C + 0xC)', '&records[cursor].velocity').replace(
        '*(RingPosition151D792C *)(records + *(s8 *)(owner + 0x2D) * 0x1C)', 'records[*(s8 *)(owner + 0x2D)].position')
    yield 'typed-record', typed
    yield 'typed-cursor-final', typed.replace('records[*(s8 *)(owner + 0x2D)].position', 'records[cursor].position')
    yield 'typed-assigned-cursor', typed.replace('if (*(s8 *)(owner + 0x2C) > 0)', 'if ((state = *(s8 *)(owner + 0x2C)) > 0)')
    yield 'cursor-final', BASE.replace('records + *(s8 *)(owner + 0x2D) * 0x1C', 'records + cursor * 0x1C')
    for local_type in ('RingPosition151D792C *', 'u8 *', 'f32 *'):
        local_copy = '        ' + local_type + 'position = (' + local_type + ')(records + *(s8 *)(owner + 0x2D) * 0x1C);\n        *(RingPosition151D792C *)(owner + 0x54) = *(RingPosition151D792C *)position;'
        local = BASE.replace(copy, local_copy)
        name = local_type.split()[0].lower()
        yield 'copy-local-' + name, local
        yield 'copy-local-zero-first-' + name, local.replace(tail.replace(copy, local_copy),
            '    if (*(s8 *)(owner + 0x2C) <= 0) {\n' + zero + '\n    } else {\n' + local_copy + '\n    }')
    yield 'copy-index-product', BASE.replace('    if (*(s8 *)(owner + 0x2C) > 0) {',
        '    if (*(s8 *)(owner + 0x2C) > 0) {\n        s32 offset = *(s8 *)(owner + 0x2D) * 0x1C;').replace(
        'records + *(s8 *)(owner + 0x2D) * 0x1C', 'records + offset')
    yield 'return-variable', BASE.replace('    s32 cursor;', '    s32 cursor;\n    s32 result;').replace(
        '        return 0;', '        result = 0;\n        return result;').replace('    return 1;', '    result = 1;\n    return result;')
    yield 'output-destination-local', BASE.replace('    if (*(s8 *)(owner + 0x2C) > 0) {',
        '    if (*(s8 *)(owner + 0x2C) > 0) {\n        RingPosition151D792C *output = (RingPosition151D792C *)(owner + 0x54);').replace(
        '        *(RingPosition151D792C *)(owner + 0x54) =', '        *output =')
    yield 'zero-vector', BASE.replace(zero, '        RingPosition151D792C zero;\n        zero.x = zero.y = zero.z = 0.0f;\n        *(RingPosition151D792C *)(owner + 0x54) = zero;')
    yield 'scalar-zero-local', BASE.replace(zero, '        f32 zero = 0.0f;\n' + zero.replace('0.0f', 'zero'))
    yield 'negative-unsigned-state', BASE.replace('*(s8 *)(owner + 0x2C)', 'owner[0x2C]')
    yield 'negative-unsigned-cursors', BASE.replace('*(s8 *)(owner + 0x2D)', 'owner[0x2D]').replace('*(s8 *)(owner + 0x2E)', 'owner[0x2E]')
    yield 'negative-signed-wrap-count', BASE.replace('owner[0x25]', '*(s8 *)(owner + 0x25)')
    yield 'negative-wrong-gate', BASE.replace('& 8', '& 4')
    yield 'negative-cached-goal', BASE.replace('    s32 cursor;', '    s32 cursor;\n    s32 goal;').replace(
        '    cursor =', '    goal = *(s8 *)(owner + 0x2D);\n    cursor =', 1).replace('*(s8 *)(owner + 0x2D)', 'goal').replace('    goal = goal;', '    goal = *(s8 *)(owner + 0x2D);')
    yield 'negative-cached-state', BASE.replace('if (*(s8 *)(owner + 0x2C) > 0)', 'if (state > 0)')
    yield 'negative-live-buffer', BASE.replace('records +', '*(u8 **)(owner + 0x94) +').replace('    u8 *records;\n', '').replace('    records = *(u8 **)(owner + 0x94);\n', '')
    yield 'negative-cached-delta', BASE.replace('    s32 cursor;', '    s32 cursor;\n    f32 delta = D_800BE9A4;').replace(' + 0xC), D_800BE9A4);', ' + 0xC), delta);')
    yield 'negative-velocity-offset', BASE.replace(' + 0xC)', ' + 8)')
    yield 'negative-stride', BASE.replace('* 0x1C', '* 0x18')


def owner_guards():
    pairs = ((0x1860000C, 0x2413001C), (0x2413001C, 0x5860000C),
             (0x00530019, 0x44800000), (0x0000C812, 0x00530019),
             (0x03341821, 0x0000C812), (0x8C610000, 0x02994021),
             (0xAE210054, 0x8D010000), (0x8C690004, 0xAE210054),
             (0xAE290058, 0x8D0A0004), (0x8C610008, 0xAE2A0058),
             (0xAE21005C, 0x8D010008), (0x10000007, 0x10000006),
             (0x24020001, 0xAE21005C))
    return [dict(filename='generated_204660', function=FUNCTION, offset='0x%X' % (0xA0 + i * 4),
        expected='0x%08X' % before, replacement='0x%08X' % after,
        expected_relocations='-', replacement_relocations='-',
        note='Normalize closed final XYZ copy registers and branch-likely zero delay schedule',
        insert_after='', insert_after_relocations='', omit='false') for i, (before, after) in enumerate(pairs)]


def normalize(words):
    result = list(words)
    assert len(result) == WORDS and result[0] == 0x27BDFFD0
    for row in owner_guards():
        index = int(row['offset'], 0) // 4
        assert result[index] == int(row['expected'], 0), ('stale ring output schedule', index)
        result[index] = int(row['replacement'], 0)
    return result


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    out.mkdir(exist_ok=True)
    source, obj, elf = (out / (name + suffix) for suffix in ('.c', '.o', '.elf'))
    source.write_text('#include <ultra64.h>\n' + DECLARATIONS + '\n' + body + '\n')
    result = subprocess.run(['ido/ido5.3_recomp/cc', '-c', '-32', '-G', '0', '-Xfullwarn', '-Xcpluscomm',
        '-signed', '-nostdinc', '-non_shared', '-Wab,-r4300_mul', '-mips2', '-o32',
        '-I', 'conker/include', '-I', 'conker/include/2.0L', '-I', 'conker/include/2.0L/PR',
        '-I', 'conker/include/libc', '-D_LANGUAGE_C', '-D_FINALROM', '-DF3DEX_GBI_2',
        '-D_MIPS_SZLONG=32', *PROFILES[profile], '-o', str(obj.relative_to(root)),
        str(source.relative_to(root))], cwd=root, capture_output=True, text=True)
    if result.returncode or result.stdout or result.stderr:
        raise ValueError(result.stdout + result.stderr)
    script = out / 'record-ring-update.ld'
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % ENTRY)
    subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', FUNCTION,
        *['--defsym=%s=0x%X' % item for item in SYMBOLS.items()], '-o', str(elf), str(obj)],
        check=True, capture_output=True)
    _, functions, relocations = parse_object(obj)
    meta, pools = functions[FUNCTION], sections(elf)
    words = list(struct.unpack_from('>%dI' % (meta['size'] // 4), pools['.text'][1], meta['value']))
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    assert not any(words[end:])
    words = words[:end]
    retail = struct.unpack_from('>%dI' % WORDS, (root / 'conker/conker.us.bin').read_bytes(), ROM)
    frames = [(-word) & 65535 for word in words if word & 0xFFFF0000 == 0x27BD0000 and word & 0x8000]
    return dict(name=name, profile=profile, body_words=end, frame=frames[0] if frames else 0,
        differences=sum(a != b for a, b in itertools.zip_longest(words, retail, fillvalue=0)),
        diagnostics='', relocations=relocations,
        pool_bytes=sum(len(v[1]) for n, v in pools.items() if n in ('.rodata', '.data'))), words


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--profiles', action='store_true')
    mode.add_argument('--candidate', choices=[name for name, _ in candidates()])
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-record-ring-update'
    forms = [('profile-' + p, SELECTED, p) for p in PROFILES] if args.profiles else [
        (name, body, 'o2g3') for name, body in candidates() if args.candidate is None or name == args.candidate]
    records = []
    for name, body, profile in forms:
        record, _ = compile_candidate(root, out, name, body, profile)
        records.append(record)
        print(name, record['body_words'], hex(record['frame']), record['differences'], flush=True)
    filename = 'profiles.json' if args.profiles else args.candidate + '-measurement.json' if args.candidate else 'measurements.json'
    (out / filename).write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
