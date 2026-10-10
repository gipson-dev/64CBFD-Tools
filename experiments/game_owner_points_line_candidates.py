"""Recover the complete leaf ten-point X-axis interpolation updater."""
import json
import struct
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151B48DC, 0x1E1D8C, 44
FUNCTION = 'func_151B48DC'
SOURCE = 'conker/src/game/generated_1E0560.c'
ORIGINAL = 's32 func_151B48DC() {\n    return 0;\n}'
TYPES = '''typedef struct { f32 x, y, z; } OwnerRibbonPosition32C8;
typedef struct { OwnerRibbonPosition32C8 position, velocity; } OwnerPointRecord3A7C;
typedef struct {
    u8 header[0x10];
    u8 flags;
    u8 gap11[3];
    OwnerRibbonPosition32C8 start, end;
    u8 metadata[0x1C];
    OwnerPointRecord3A7C points[10];
} OwnerPoints3A7C;
'''
DECLARATIONS = 'extern f32 D_800AA3C4;\n'
SYMBOLS = dict(D_800AA3C4=0x800AA3C4)
SELECTED = '''s32 func_151B48DC(OwnerPoints3A7C *owner) {
    f32 start, step, x;
    s32 i;

    start = owner->start.x;
    step = -(start - owner->end.x);
    owner->points[0].position.x = start;
    owner->points[0].position.y = 0.0f;
    owner->points[0].position.z = 0.0f;
    step *= D_800AA3C4;
    x = start + step;
    for (i = 1; i < 10; i++) {
        owner->points[i].position.x = x;
        owner->points[i].position.y = 0.0f;
        owner->points[i].position.z = 0.0f;
        x += step;
    }
    owner->flags &= ~2;
    return 1;
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'count-local', SELECTED.replace('    s32 i;', '    s32 i, count;').replace(
        '    for (i = 1; i < 10;', '    count = 10;\n    for (i = 1; i < count;')
    peeled = SELECTED.replace('    for (i = 1;',
        '    owner->points[1].position.x = x;\n'
        '    owner->points[1].position.y = 0.0f;\n'
        '    owner->points[1].position.z = 0.0f;\n'
        '    x += step;\n    for (i = 2;')
    yield 'peeled-two', peeled
    setup, loop = peeled.split('    for (i = 2; i < 10; i++) {\n', 1)
    work, tail = loop.split('    }\n', 1)
    unrolled = setup + '    for (i = 2; i < 10; i += 4) {\n'
    for index in range(4):
        unrolled += work.replace('points[i]', 'points[i + %d]' % index)
    unrolled += '    }\n' + tail
    yield 'explicit-four', unrolled
    yield 'explicit-four-count', unrolled.replace('    s32 i;', '    s32 i, count;').replace(
        '    for (i = 2; i < 10;', '    count = 10;\n    for (i = 2; i < count;')
    yield 'explicit-four-not-equal', unrolled.replace('i < 10', 'i != 10')
    yield 'explicit-four-count-not-equal', unrolled.replace('    s32 i;', '    s32 i, count;').replace(
        '    for (i = 2; i < 10;', '    count = 10;\n    for (i = 2; i != count;')
    yield 'delayed-negative', SELECTED.replace('step = -(start - owner->end.x)',
        'step = start - owner->end.x').replace('step *= D_', 'step = -step * D_')
    yield 'peeled-delayed-negative', peeled.replace('step = -(start - owner->end.x)',
        'step = start - owner->end.x').replace('step *= D_', 'step = -step * D_')
    yield 'peeled-two-zero-local', peeled.replace('    f32 start, step, x;',
        '    f32 start, step, x, zero;').replace('    start =', '    zero = 0.0f;\n    start =', 1).replace(' = 0.0f;', ' = zero;').replace('zero = zero;', 'zero = 0.0f;')
    yield 'indexed-raw', SELECTED.replace('OwnerPoints3A7C *owner', 'u8 *owner').replace(
        'owner->start.x', '*(f32 *)(owner + 0x14)').replace('owner->end.x', '*(f32 *)(owner + 0x20)').replace(
        'owner->flags', 'owner[0x10]').replace('owner->points[0].position.x', '*(f32 *)(owner + 0x48)').replace(
        'owner->points[0].position.y', '*(f32 *)(owner + 0x4C)').replace(
        'owner->points[0].position.z', '*(f32 *)(owner + 0x50)').replace(
        'owner->points[i].position.x', '*(f32 *)(owner + 0x48 + i * 24)').replace(
        'owner->points[i].position.y', '*(f32 *)(owner + 0x4C + i * 24)').replace(
        'owner->points[i].position.z', '*(f32 *)(owner + 0x50 + i * 24)')
    yield 'negative-reversed-subtraction', SELECTED.replace('-(start - owner->end.x)', 'owner->end.x - start')
    yield 'negative-early-scale', SELECTED.replace('    step *= D_800AA3C4;\n', '').replace(
        '    owner->points[0].position.x', '    step *= D_800AA3C4;\n    owner->points[0].position.x', 1)
    yield 'negative-nine-points', SELECTED.replace('i < 10', 'i < 9')
    yield 'negative-formula', SELECTED.replace('owner->points[i].position.x = x;',
        'owner->points[i].position.x = start + i * step;')
    yield 'negative-velocity-clear', SELECTED.replace('        x += step;',
        '        owner->points[i].velocity.x = 0.0f;\n        x += step;')
    yield 'negative-wrong-flag', SELECTED.replace('owner->flags &= ~2', 'owner->flags &= ~4')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3', symbols=None, entry=ENTRY):
    with patch.multiple(compiler, ENTRY=entry, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=TYPES, DECLARATIONS=DECLARATIONS, SYMBOLS=symbols or SYMBOLS):
        meta, words = compiler.compile_candidate(root, out, name, body, profile)
    frames = [w for w in words if w >> 26 == 9 and w >> 21 & 31 == 29 and w >> 16 & 31 == 29]
    meta['frame'] = (-frames[0]) & 65535 if frames else 0
    return meta, words


def install(before):
    if before.count(ORIGINAL) != 1:
        raise ValueError('expected one original line placeholder')
    return before.replace('/* Non-matching placeholders', DECLARATIONS +
        '\n/* Non-matching placeholders', 1).replace(ORIGINAL, SELECTED)


RAW = tuple(int(word, 16) for word in '''
44808000 00000000 c4800014 c4840020 e490004c e4900050 46040081 3c010000
e4800048 c4260000 46001087 24850018 46061082 e4b0004c e4b00050 24020002
24830030 46020380 e4ae0048 2405000a 46027300 e46c0048 46026300 24420004
e4700064 e4700068 e46c0060 46026300 e470007c e4700080 e4700094 e46c0078
46026300 e4700098 24630060 e470ffec e46c0030 46026300 1445ffee e470fff0
908e0010 24020001 31cffffd a08f0010 03e00008 00000000
'''.split())
OMIT = (1, 11)
SETUP = (2, 3, 0, 7, 6, 8, 4, 5, 9, 10, 15, 12, 16, 19, 14, 13, 17, 18, 20)
LOOP = (21, 35, 39, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 36, 38, 37)


def recipe(words):
    """Closed producer-role scheduling; no retail words construct replacements."""
    if len(words) != len(RAW) or any((word & (0xFFFF0000 if i in (7, 9) else 0xFFFFFFFF)) != RAW[i]
            for i, word in enumerate(words)):
        raise ValueError('stale complete X-axis line body')
    adjusted = list(words)
    changes = [(3, 16, 4, 2), (6, 16, 4, 2), (6, 6, 2, 4), (9, 16, 6, 8),
        (10, 11, 2, 4), (10, 6, 2, 6), (12, 16, 6, 8), (12, 11, 2, 6),
        (12, 6, 2, 12), (17, 16, 2, 12), (20, 16, 2, 12), (20, 6, 12, 14)]
    for index in (22, 27, 32, 37):
        changes.extend(((index, 16, 2, 12), (index, 11, 12, 14), (index, 6, 12, 14)))
    for index in (21, 26, 31, 36):
        changes.append((index, 16, 12, 14))
    for index, shift, old, new in changes:
        if adjusted[index] >> shift & 31 != old:
            raise ValueError('stale line floating producer role')
        adjusted[index] = adjusted[index] & ~(31 << shift) | new << shift
    # The point-one pointer is used only by these three stores, then replaced by10.
    for index, offset in ((13, 0x64), (14, 0x68), (18, 0x60)):
        if adjusted[index] >> 21 & 31 != 5:
            raise ValueError('stale point-one pointer view')
        adjusted[index] = adjusted[index] & ~((31 << 21) | 65535) | 4 << 21 | offset
    # Move point-two zeros ahead of the cursor increment, preserving absolute homes.
    for index, offset in ((35, 0x4C), (39, 0x50)):
        adjusted[index] = adjusted[index] & 0xFFFF0000 | offset
    origins = SETUP + LOOP + tuple(range(40, 46))
    if sorted(origins) != [i for i in range(46) if i not in OMIT]:
        raise ValueError('line schedule is not a closed two-omission permutation')
    return [adjusted[i] for i in origins], [i * 4 for i in origins]


def guard_rows(path):
    text, functions, relocations = parse_object(path)
    target = functions[FUNCTION]
    if target['size'] != 184:
        raise ValueError('expected complete 46-word line body')
    fitted, origins = recipe(struct.unpack_from('>46I', text, target['value']))
    spec = lambda uses: ';'.join(kind + ':' + symbol for kind, symbol in uses) or '-'
    rows, destination = [], 0
    for index, word in enumerate(struct.unpack_from('>46I', text, target['value'])):
        omitted = index in OMIT
        replacement = word if omitted else fitted[destination]
        old = relocations.get(target['value'] + index * 4, ())
        new = old if omitted else relocations.get(target['value'] + origins[destination], ())
        rows.append(dict(filename='generated_1E0560', function=FUNCTION, offset='0x%X' % (index * 4),
            expected='0x%08X' % word, replacement='0x%08X' % replacement,
            expected_relocations=spec(old), replacement_relocations=spec(new),
            note='Normalize certified X-axis line producer schedule and folded point pointer',
            insert_after='', insert_after_relocations='', omit='true' if omitted else 'false'))
        destination += not omitted
    return rows


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-points-line'
    records = []
    for name, body in candidates():
        meta, _ = compile_candidate(root, out, name, body)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
