"""Bounded complete fixed-span ten-point initializer candidates."""
import json
import struct
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler
from tools.experiments.game_owner_points_line_candidates import TYPES
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151B4B78, 0x1E2028, 41
FUNCTION = 'func_151B4B78'
SOURCE = 'conker/src/game/generated_1E0560.c'
ORIGINAL = 's32 func_151B4B78() {\n    return 0;\n}'
DECLARATIONS = 'extern f32 D_800AA3C8;\n'
SYMBOLS = dict(D_800AA3C8=0x800AA3C8)
SELECTED = '''s32 func_151B4B78(OwnerPoints3A7C *owner) {
    f32 x, step;
    s32 i;

    x = -1000.0f;
    step = D_800AA3C8;
    for (i = 0; i < 10; i++) {
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
        '    for (i = 0; i < 10;', '    count = 10;\n    for (i = 0; i < count;')
    yield 'zero-local', SELECTED.replace('    f32 x, step;', '    f32 x, step, zero;').replace(
        '    x =', '    zero = 0.0f;\n    x =', 1).replace(' = 0.0f;', ' = zero;').replace('zero = zero;', 'zero = 0.0f;')
    yield 'negative-late-step', SELECTED.replace('    step = D_800AA3C8;\n', '').replace(
        '        x += step;', '        if (i == 0) step = D_800AA3C8;\n        x += step;')
    yield 'negative-start', SELECTED.replace('-1000.0f', '-999.0f')
    yield 'negative-nine-points', SELECTED.replace('i < 10', 'i < 9')
    yield 'negative-formula', SELECTED.replace('owner->points[i].position.x = x;',
        'owner->points[i].position.x = -1000.0f + i * step;')
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
        raise ValueError('expected one original fixed-span placeholder')
    return before.replace('/* Non-matching placeholders', DECLARATIONS +
        '\n/* Non-matching placeholders', 1).replace(ORIGINAL, SELECTED)


RAW = tuple(int(word, 16) for word in '''
3c01c47a 44816000 3c010000 c4220000 44807000 e48c0048 46026000 24020002
24830030 2405000a e4800060 46020000 e48e004c e48e0050 e48e0064 e48e0068
e4600048 46020000 24420004 e46e0064 e46e0068 e4600060 46020000 e46e007c
e46e0080 e46e0094 e4600078 46020000 e46e0098 24630060 e46effec e4600030
46020000 1445ffee e46efff0 908e0010 24020001 31cffffd a08f0010 03e00008 00000000
'''.split())
ORDER = tuple(range(16)) + (16, 30, 34, 17, 18, 19, 20, 21, 22, 23, 24,
    25, 26, 27, 28, 29, 31, 33, 32) + tuple(range(35, 41))


def recipe(words):
    """Closed floating-role cycle and two cursor-relative zero-store moves."""
    if len(words) != len(RAW) or any((word & (0xFFFF0000 if i in (2, 3) else 0xFFFFFFFF)) != RAW[i]
            for i, word in enumerate(words)):
        raise ValueError('stale complete fixed-span body')
    adjusted = list(words)
    roles = {12: 2, 2: 14, 14: 12}
    for index, word in enumerate(words):
        op = word >> 26
        shifts = (16,) if op in (49, 57) else ()
        if op == 17:
            shifts = (11,) if word >> 21 & 31 == 4 else (16, 11, 6)
        for shift in shifts:
            reg = word >> shift & 31
            adjusted[index] = adjusted[index] & ~(31 << shift) | roles.get(reg, reg) << shift
    # These two stores move before the cursor increment; retain their physical homes.
    for index, offset in ((30, 0x4C), (34, 0x50)):
        adjusted[index] = adjusted[index] & 0xFFFF0000 | offset
    if sorted(ORDER) != list(range(41)):
        raise ValueError('fixed-span schedule is not a closed permutation')
    return [adjusted[i] for i in ORDER], [i * 4 for i in ORDER]


def guard_rows(path):
    text, functions, relocations = parse_object(path)
    target = functions[FUNCTION]
    if target['size'] != 164:
        raise ValueError('expected complete 41-word fixed-span body')
    words = struct.unpack_from('>41I', text, target['value'])
    fitted, origins = recipe(words)
    spec = lambda uses: ';'.join(kind + ':' + symbol for kind, symbol in uses) or '-'
    rows = []
    for index, word in enumerate(words):
        old = relocations.get(target['value'] + index * 4, ())
        new = relocations.get(target['value'] + origins[index], ())
        rows.append(dict(filename='generated_1E0560', function=FUNCTION, offset='0x%X' % (index * 4),
            expected='0x%08X' % word, replacement='0x%08X' % fitted[index],
            expected_relocations=spec(old), replacement_relocations=spec(new),
            note='Normalize certified fixed-span floating roles and point zero-store schedule',
            insert_after='', insert_after_relocations='', omit='false'))
    return rows


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-points-span'
    records = []
    for name, body in candidates():
        meta, _ = compile_candidate(root, out, name, body)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
