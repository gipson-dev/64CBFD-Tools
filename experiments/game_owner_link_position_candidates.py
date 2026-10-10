"""Complete linked-owner position provider: widths, reloads and leaf ABI."""
import json
import struct
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151B3F28, 0x1E13D8, 45
FUNCTION = 'func_151B3F28'
SOURCE = 'conker/src/game/generated_1E0560.c'
ORIGINAL = 's32 func_151B3F28() {\n    return 0;\n}'
TYPES = '''typedef struct { u8 *actor; u8 epoch; } OwnerPositionLink3F28;
'''
DECLARATIONS = 'extern f32 D_800AA3AC;\n'
SYMBOLS = dict(D_800AA3AC=0x800AA3AC)
SELECTED = '''s32 func_151B3F28(u8 *actor, f32 *output, u8 enabled) {
    OwnerPositionLink3F28 *link;
    s32 result;
    f32 y;

    result = 1;
    if (enabled) {
        link = (OwnerPositionLink3F28 *)(actor + 0x150);
        if (*(s32 *)link->actor != 0 && link->epoch == link->actor[0x3B]) {
            output[0] = *(f32 *)(link->actor + 0x14);
            output[1] = *(f32 *)(link->actor + 0x18);
            output[2] = *(f32 *)(link->actor + 0x1C);
            actor[0x10] &= ~4;
        } else {
            result = 0;
            actor[0x10] |= 0xC;
        }
    } else {
        output[0] = 0.0f;
        y = D_800AA3AC;
        output[2] = 0.0f;
        output[1] = y;
        actor[0x10] &= ~8;
    }
    return result;
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'word-mode', SELECTED.replace('u8 enabled', 's32 enabled').replace(
        'if (enabled)', 'if ((u8)enabled)')
    yield 'volatile-mode', SELECTED.replace('u8 enabled', 'volatile u8 enabled')
    yield 'early-return', SELECTED.replace('            actor[0x10] |= 0xC;',
        '            actor[0x10] |= 0xC;\n            return result;')
    yield 'late-constant', SELECTED.replace('        y = D_800AA3AC;\n', '').replace(
        '        output[1] = y;', '        output[1] = D_800AA3AC;').replace('    f32 y;\n', '')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3', symbols=None, entry=ENTRY):
    with patch.multiple(compiler, ENTRY=entry, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=TYPES, DECLARATIONS=DECLARATIONS, SYMBOLS=symbols or SYMBOLS):
        meta, words = compiler.compile_candidate(root, out, name, body, profile)
    adjustments = [w for w in words if w >> 26 == 9 and w >> 21 & 31 == 29 and w >> 16 & 31 == 29]
    if adjustments:
        raise ValueError('unexpected frame allocation in leaf provider')
    meta['frame'] = 0
    return meta, words


RAW = tuple(int(w, 16) for w in '''
afa60008 30ce00ff 01c03025 10c0001c 24030001 8c8f0150 24820150 8df80000
53000013 908d0010 8c460000 90590004 90c8003b 5728000e 908d0010 c4c40014
e4a40000 8c490000 c5260018 e4a60004 8c4a0000 c548001c e4a80008 908b0010
316cfffb 1000000f a08c0010 908d0010 00001825 35ae000c 1000000a a08e0010
44801000 3c010000 e4a20000 c4200000 e4a20008 e4a00004 908f0010 31f8fff7
a0980010 00601025 03e00008 00000000
'''.split())


def recipe(words):
    """Expand the failure return copy and rename the closed disabled FP roles.

    No retail input is used to construct this recipe. The additional move is
    copied from the shared tail, whose zero/one result is already established.
    The old failure branch moves past that shared move and executes its copy
    in the delay slot. No public access changes order.
    """
    if len(words) != 44 or any((w & (0xFFFF0000 if i in (33, 35) else 0xFFFFFFFF)) != RAW[i]
            for i, w in enumerate(words)):
        raise ValueError('stale complete linked-position body')
    origins = list(range(30)) + [31, 30, 41] + list(range(32, 44))
    fitted = [words[i] for i in origins]
    for i in (3, 25):
        fitted[i] += 1
    fitted[31] = (fitted[31] & 0xFFFF0000) | 0xB
    for i, shift, old, new in ((33, 11, 2, 0), (35, 16, 2, 0),
            (36, 16, 0, 10), (37, 16, 2, 0), (38, 16, 0, 10)):
        if fitted[i] >> shift & 31 != old:
            raise ValueError('stale disabled FP role')
        fitted[i] = (fitted[i] & ~(31 << shift)) | new << shift
    return fitted, [i * 4 for i in origins]


def guard_rows(object_path):
    text, functions, relocations = parse_object(object_path)
    target = functions[FUNCTION]
    if target['size'] != 176:
        raise ValueError('expected complete 44-word provider')
    raw = list(struct.unpack_from('>44I', text, target['value']))
    fitted, origins = recipe(raw)
    rows = []
    spec = lambda uses: ';'.join(kind + ':' + symbol for kind, symbol in uses) or '-'
    for i, expected in enumerate(raw):
        destination = i if i <= 31 else i + 1
        replacement = fitted[destination]
        old = relocations.get(target['value'] + i * 4, [])
        new = relocations.get(target['value'] + origins[destination], [])
        rows.append(dict(filename='generated_1E0560', function=FUNCTION, offset='0x%03X' % (i * 4),
            expected='0x%08X' % expected, replacement='0x%08X' % replacement,
            expected_relocations=spec(old), replacement_relocations=spec(new),
            note='Normalize certified linked-owner return copy and disabled FP roles',
            insert_after='0x%08X' % fitted[32] if i == 31 else '',
            insert_after_relocations='-' if i == 31 else '', omit='false'))
    return rows


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-link-position'
    records = []
    for name, body in candidates():
        meta, _ = compile_candidate(root, out, name, body)
        records.append(meta)
        print(name, meta['body_words'], meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
