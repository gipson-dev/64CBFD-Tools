"""Complete record integration, height query and response callback fitting."""

import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x15148BA4, 0x176054, 143
FUNCTION = 'func_15148BA4'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_175250/func_15148BA4.s")'
SYMBOLS = dict(D_800BE9A4=0x800BE9A4, func_15046C80=0x15046C80,
    D_8008A430=0x8008A430, D_8008A450=0x8008A450)
DECLARATIONS = '''typedef struct { f32 x, y, z; } RecordPosition15148BA4;
typedef struct HeightResult71820 {
    f32 height;
    s16 vertices[9];
    s16 pad16;
    u32 metadata;
    u8 flags;
    u8 state;
    u16 pad1E;
    s32 value;
} HeightResult71820;
s32 func_15046C80(f32 *, u16, f32, HeightResult71820 *);
extern s32 (*D_8008A430[])(u8 *, f32, f32, f32, f32, void *);
extern s32 (*D_8008A450[])(u8 *, f32, f32, f32, f32, void *);
'''
BASE = '''s32 func_15148BA4(u8 *actor) {
    u8 *payload = *(u8 **)(actor + 0x98);
    MotionRecord15148AF4 *records = *(MotionRecord15148AF4 **)(actor + 0x94);
    s32 index = *(s8 *)(actor + 0x2E);
    RecordPosition15148BA4 previous;
    f32 position[3];
    MotionRecord15148AF4 *record;
    s32 selector;

    /* Retail's snapshot gate is narrower than the later response gate. */
    if (payload[0x18] & 7) {
        previous = *(RecordPosition15148BA4 *)(records + *(s8 *)(actor + 0x2D));
    }
    index--;
    do {
        if (index < 0) {
            index = actor[0x25] - 1;
        }
        record = records + index;
        record->velocityY -= *(f32 *)(payload + 0x10) * D_800BE9A4;
        record->x += *(f32 *)(payload + 0x04) * D_800BE9A4;
        record->y += record->velocityY * D_800BE9A4;
        record->z += *(f32 *)(payload + 0x0C) * D_800BE9A4;
    } while (index-- != *(s8 *)(actor + 0x2D));
    if (payload[0x18] & 0x17) {
        if (records[*(s8 *)(actor + 0x2D)].y < previous.y) {
            position[0] = records[*(s8 *)(actor + 0x2D)].x;
            position[1] = previous.y;
            position[2] = records[*(s8 *)(actor + 0x2D)].z;
            if (func_15046C80(position, 0, records[*(s8 *)(actor + 0x2D)].y,
                    (HeightResult71820 *)(actor + 0x60))) {
                if (actor[0x7D] == 3) {
                    selector = payload[0x24];
                    if (selector != 0) {
                        return D_8008A450[selector](actor, previous.x, previous.y,
                            previous.z, *(f32 *)(actor + 0x60), actor + 0x64) != 0;
                    }
                } else {
                    selector = payload[0x23];
                    if (selector != 0) {
                        return D_8008A430[selector](actor, previous.x, previous.y,
                            previous.z, *(f32 *)(actor + 0x60), actor + 0x64) != 0;
                    }
                }
            }
        }
    }
    return 1;
}'''

SELECTED = '''s32 func_15148BA4(u8 *actor) {
    u8 *payload = *(u8 **)(actor + 0x98);
    MotionRecord15148AF4 *records = *(MotionRecord15148AF4 **)(actor + 0x94);
    s32 index = *(s8 *)(actor + 0x2E);
    RecordPosition15148BA4 previous;
    f32 position[3];
    s32 selector;

    /* Retail's snapshot gate is narrower than the later response gate. */
    if (payload[0x18] & 7) {
        previous = *(RecordPosition15148BA4 *)(records + *(s8 *)(actor + 0x2D));
    }
    do {
        index--;
        if (index < 0) {
            index = actor[0x25] - 1;
        }
        records[index].velocityY -= *(f32 *)(payload + 0x10) * D_800BE9A4;
        records[index].x += *(f32 *)(payload + 0x04) * D_800BE9A4;
        records[index].y += records[index].velocityY * D_800BE9A4;
        records[index].z += *(f32 *)(payload + 0x0C) * D_800BE9A4;
    } while (index != *(s8 *)(actor + 0x2D));
    if (payload[0x18] & 0x17) {
        if (records[*(s8 *)(actor + 0x2D)].y < previous.y) {
            position[0] = records[*(s8 *)(actor + 0x2D)].x;
            position[1] = previous.y;
            position[2] = records[*(s8 *)(actor + 0x2D)].z;
            if (func_15046C80(position, 0, records[*(s8 *)(actor + 0x2D)].y,
                    (HeightResult71820 *)(actor + 0x60))) {
                if (actor[0x7D] == 3) {
                    selector = payload[0x24];
                    if (selector != 0) {
                        if (D_8008A450[selector](actor, previous.x, previous.y,
                                previous.z, *(f32 *)(actor + 0x60), actor + 0x64) == 0) {
                            return 0;
                        }
                    }
                } else {
                    selector = payload[0x23];
                    if (selector != 0) {
                        if (D_8008A430[selector](actor, previous.x, previous.y,
                                previous.z, *(f32 *)(actor + 0x60), actor + 0x64) == 0) {
                            return 0;
                        }
                    }
                }
            }
        }
    }
    return 1;
}'''
PATCHES = ((18, 0x016A6021, 0x014B6021), (92, 0xAFA80054, 0xAFA80050),
    (94, 0x8FA80054, 0x8FA80050))


def normalize(words):
    assert len(words) == WORDS
    result = list(words)
    for index, expected, replacement in PATCHES:
        assert result[index] == expected, (index, hex(result[index]))
        result[index] = replacement
    return result


def guard_rows():
    return [dict(filename='generated_175250', function=FUNCTION, offset='0x%X' % (i * 4),
        expected='0x%08X' % expected, replacement='0x%08X' % replacement,
        expected_relocations='-', replacement_relocations='-',
        note='Normalize record height response commutative pointer or closed payload spill slot',
        insert_after='', insert_after_relocations='', omit='false') for i, expected, replacement in PATCHES]


def candidates():
    yield 'selected', SELECTED
    yield 'baseline', BASE
    yield 'top-decrement', BASE.replace('    index--;\n    do {', '    do {\n        index--;').replace(
        'while (index-- !=', 'while (index !=')
    yield 'indexed', BASE.replace('    MotionRecord15148AF4 *record;\n', '').replace(
        '        record = records + index;\n', '').replace('record->', 'records[index].')
    yield 'position-order', BASE.replace('RecordPosition15148BA4 previous;\n    f32 position[3];',
        'f32 position[3];\n    RecordPosition15148BA4 previous;')
    yield 'cached-current', BASE.replace('    if (payload[0x18] & 0x17) {',
        '    record = records + *(s8 *)(actor + 0x2D);\n    if (payload[0x18] & 0x17) {').replace(
        'records[*(s8 *)(actor + 0x2D)].', 'record->')
    explicit = BASE
    for table in ('D_8008A450', 'D_8008A430'):
        expression = 'return %s[selector](actor, previous.x, previous.y,\n                            previous.z, *(f32 *)(actor + 0x60), actor + 0x64) != 0;' % table
        replacement = 'if (%s[selector](actor, previous.x, previous.y,\n                            previous.z, *(f32 *)(actor + 0x60), actor + 0x64) == 0) {\n                            return 0;\n                        }\n                        return 1;' % table
        explicit = explicit.replace(expression, replacement)
    for top, indexed, live_selector in itertools.product((False, True), repeat=3):
        body = explicit
        if top:
            body = body.replace('    index--;\n    do {', '    do {\n        index--;').replace('while (index-- !=', 'while (index !=')
        if indexed:
            body = body.replace('    MotionRecord15148AF4 *record;\n', '').replace(
                '        record = records + index;\n', '').replace('record->', 'records[index].')
        if live_selector:
            body = body.replace('    s32 selector;\n', '')
            for offset, table in (('0x24', 'D_8008A450'), ('0x23', 'D_8008A430')):
                body = body.replace('                    selector = payload[%s];\n' % offset, '').replace(
                    '%s[selector]' % table, '%s[payload[%s]]' % (table, offset))
            body = body.replace('if (selector != 0)', 'if (payload[0x24] != 0)', 1).replace(
                'if (selector != 0)', 'if (payload[0x23] != 0)', 1)
        yield 'explicit-%d-%d-%d' % (top, indexed, live_selector), body
        yield 'fallthrough-%d-%d-%d' % (top, indexed, live_selector), body.replace(
            '                        return 1;\n', '')
        yield 'positive-%d-%d-%d' % (top, indexed, live_selector), body.replace(
            'actor + 0x64) == 0)', 'actor + 0x64) != 0)').replace(
            '                            return 0;', '                            return 1;').replace(
            '                        return 1;', '                        return 0;')
        if top and indexed and not live_selector:
            fitted = body.replace('                        return 1;\n', '').replace(
                '*(RecordPosition15148BA4 *)(records + *(s8 *)(actor + 0x2D))',
                '*(RecordPosition15148BA4 *)&records[*(s8 *)(actor + 0x2D)]')
            yield 'address-index', fitted
            for kind in ('u8', 's8', 'u16', 's16'):
                yield 'selector-' + kind, fitted.replace('s32 selector;', kind + ' selector;')
            for name in ('index', 'payload', 'records', 'selector'):
                line = next(line for line in fitted.splitlines() if name in line and ';' in line)
                yield 'register-' + name, fitted.replace(line, line.replace('    ', '    register ', 1))
            yield 'query-struct', fitted.replace('f32 position[3];', 'RecordPosition15148BA4 position;').replace(
                'position[0]', 'position.x').replace('position[1]', 'position.y').replace('position[2]', 'position.z').replace(
                'func_15046C80(position,', 'func_15046C80(&position.x,')
            for name, expression in (
                    ('byte-pointer', '(u8 *)records + *(s8 *)(actor + 0x2D) * 20'),
                    ('integer-pointer', '(u32)records + *(s8 *)(actor + 0x2D) * 20'),
                    ('reverse-byte', '*(s8 *)(actor + 0x2D) * 20 + (u8 *)records'),
                    ('reverse-integer', '*(s8 *)(actor + 0x2D) * 20 + (u32)records')):
                yield name, fitted.replace('*(RecordPosition15148BA4 *)&records[*(s8 *)(actor + 0x2D)]',
                    '*(RecordPosition15148BA4 *)(%s)' % expression)


def compile_candidate(root, output, name, body=SELECTED, profile='o2g3'):
    output.mkdir(exist_ok=True)
    source, obj, elf = (output / (name + suffix) for suffix in ('.c', '.o', '.elf'))
    source.write_text('#include <ultra64.h>\nextern f32 D_800BE9A4;\n'
        'typedef struct { f32 x, y, z, velocityY, reserved; } MotionRecord15148AF4;\n'
        + DECLARATIONS + body + '\n')
    result = subprocess.run(['ido/ido5.3_recomp/cc', '-c', '-32', '-G', '0', '-Xfullwarn', '-Xcpluscomm',
        '-signed', '-nostdinc', '-non_shared', '-Wab,-r4300_mul', '-mips2', '-o32',
        '-I', 'conker/include', '-I', 'conker/include/2.0L', '-I', 'conker/include/2.0L/PR',
        '-I', 'conker/include/libc', '-D_LANGUAGE_C', '-D_FINALROM', '-DF3DEX_GBI_2',
        '-D_MIPS_SZLONG=32', *PROFILES[profile], '-o', str(obj.relative_to(root)),
        str(source.relative_to(root))], cwd=root, capture_output=True, text=True)
    if result.returncode or result.stdout or result.stderr:
        raise ValueError(result.stdout + result.stderr)
    script = output / 'record-height-response.ld'
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % ENTRY)
    subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', FUNCTION,
        *['--defsym=%s=0x%X' % item for item in SYMBOLS.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
    _, functions, relocations = parse_object(obj)
    meta, pools = functions[FUNCTION], sections(elf)
    words = list(struct.unpack_from('>%dI' % (meta['size'] // 4), pools['.text'][1], meta['value']))
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    assert not any(words[end:]); words = words[:end]
    retail = struct.unpack_from('>%dI' % WORDS, (root / 'conker/conker.us.bin').read_bytes(), ROM)
    frames = [(-w) & 65535 for w in words if w & 0xFFFF0000 == 0x27BD0000 and w & 0x8000]
    return dict(name=name, profile=profile, body_words=end, frame=frames[0] if frames else 0,
        differences=sum(a != b for a, b in itertools.zip_longest(words, retail, fillvalue=0)),
        relocations=relocations, diagnostics='',
        pool_bytes=sum(len(v[1]) for n, v in pools.items() if n in ('.rodata', '.data'))), words


def main():
    root = Path(__file__).resolve().parents[2]; output = root / 'conker/build/game-record-height-response'
    receipts = []
    for name, body in candidates():
        meta, _ = compile_candidate(root, output, name, body)
        receipts.append(meta)
        print(name, meta['body_words'], meta['frame'], meta['differences'], flush=True)
    (output / 'measurements.json').write_text(json.dumps(receipts, indent=2) + '\n')


if __name__ == '__main__':
    main()
