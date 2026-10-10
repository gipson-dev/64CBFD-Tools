"""Recover the complete captured-object metadata adapter and fallback ABI."""
import json
import re
import struct
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151B4A14, 0x1E1EC4, 89
FUNCTION = 'func_151B4A14'
SOURCE = 'conker/src/game/generated_1E0560.c'
ORIGINAL = 's32 func_151B4A14() {\n    return 0;\n}'
SIGNATURE = '''u8 *owner, s32 *mode1, s32 *mode2, s32 *envR, s32 *envG,
                  s32 *envB, s32 *alpha, s32 *primR, s32 *primG, s32 *primB,
                  s32 *primA, s32 *renderMode, u8 *bank, u8 *combine'''
DECLARATIONS = '''void func_1502EC34(u8 *, s32 *, s32 *, s32 *, s32 *);
s32 func_151B498C(''' + SIGNATURE + ''');
'''
SYMBOLS = dict(func_1502EC34=0x1502EC34, func_151B498C=0x151B498C)
SCRATCH = '''typedef struct {
    u8 reserved00[8];
    s32 opacity, blue, green, red;
    u8 *object;
    u8 reserved1C[11];
    u8 result;
} OwnerMetadataScratch4A14;
'''
BASE = '''s32 func_151B4A14(''' + SIGNATURE + ''') {
    s32 red, green, blue, opacity;
    u8 *object;
    u8 result;

    result = 1;
    object = *(u8 **)(owner + 0x150);
    func_1502EC34(object, &red, &green, &blue, &opacity);
    if (object[0xA4] & 1) {
        *mode1 = 0x200005;
        *mode2 = 0x60600;
        *envR = red;
        *envG = green;
        *envB = blue;
        *alpha = 0xFF;
        *primB = opacity;
        *primG = opacity;
        *primR = opacity;
        *primA = 0xFF;
        *renderMode = 0x100000;
        *bank = 5;
        *combine = 0x2F;
    } else {
        result = func_151B498C(owner, mode1, mode2, envR, envG, envB, alpha,
            primR, primG, primB, primA, renderMode, bank, combine);
    }
    return result;
}'''
SELECTED = BASE.replace('    s32 red, green, blue, opacity;\n    u8 *object;\n    u8 result;',
    '    u8 result;\n    /* Retain retail scratch allocation; reserved words are never accessed. */\n'
    '    s32 reserved1, reserved2;\n    u8 *object;\n    s32 red, green, blue, opacity;\n    s32 reserved3;')


def candidates():
    yield 'selected', SELECTED
    yield 'compact-locals', BASE
    yield 'locals-reordered', BASE.replace('    s32 red, green, blue, opacity;\n    u8 *object;\n    u8 result;',
        '    u8 result;\n    u8 *object;\n    s32 red, green, blue, opacity;')
    yield 'locals-extra-two', BASE.replace('    s32 red, green, blue, opacity;\n    u8 *object;\n    u8 result;',
        '    u8 result;\n    s32 unused1, unused2;\n    u8 *object;\n    s32 red, green, blue, opacity;')
    yield 'locals-extra-three', BASE.replace('    s32 red, green, blue, opacity;\n    u8 *object;\n    u8 result;',
        '    u8 result;\n    s32 unused1, unused2, unused3;\n    u8 *object;\n    s32 red, green, blue, opacity;')
    yield 'locals-split-reserved', BASE.replace('    s32 red, green, blue, opacity;\n    u8 *object;\n    u8 result;',
        '    u8 result;\n    s32 reserved1, reserved2;\n    u8 *object;\n    s32 red, green, blue, opacity;\n    s32 reserved3;')
    yield 'locals-reserved-bytes', BASE.replace('    s32 red, green, blue, opacity;\n    u8 *object;\n    u8 result;',
        '    u8 result;\n    u8 reserved[8];\n    u8 *object;\n    s32 red, green, blue, opacity;')
    yield 'locals-reserved-nine', BASE.replace('    s32 red, green, blue, opacity;\n    u8 *object;\n    u8 result;',
        '    u8 result;\n    u8 reserved[9];\n    u8 *object;\n    s32 red, green, blue, opacity;')
    scratch = BASE.replace('    s32 red, green, blue, opacity;\n    u8 *object;\n    u8 result;',
        '    OwnerMetadataScratch4A14 scratch;')
    scratch = re.sub(r'\b(red|green|blue|opacity|object|result)\b', r'scratch.\1', scratch)
    yield 'scratch-record', SCRATCH + scratch
    yield 'volatile-register-args', BASE.replace('u8 *owner,', 'u8 *volatile owner,').replace(
        's32 *mode1,', 's32 *volatile mode1,').replace('s32 *mode2,', 's32 *volatile mode2,').replace(
        's32 *envR,', 's32 *volatile envR,')
    yield 'volatile-object-result', BASE.replace('u8 *object;', 'u8 *volatile object;').replace(
        'u8 result;', 'volatile u8 result;')
    yield 'wide-result', BASE.replace('u8 result;', 's32 result;')
    yield 'negative-early-mode', SELECTED.replace('    u8 result;', '    u8 result, mode;').replace(
        '    func_1502EC34', '    mode = object[0xA4];\n    func_1502EC34', 1).replace('object[0xA4] & 1', 'mode & 1')
    yield 'negative-reload-object', SELECTED.replace('    if (object[0xA4]',
        '    object = *(u8 **)(owner + 0x150);\n    if (object[0xA4]')
    yield 'negative-byte-color', SELECTED.replace('*envR = red;', '*envR = (u8)red;')
    yield 'negative-wrong-custom', SELECTED.replace('*mode1 = 0x200005;', '*mode1 = 0x220005;')
    yield 'negative-store-order', SELECTED.replace('        *mode1 = 0x200005;\n        *mode2 = 0x60600;',
        '        *mode2 = 0x60600;\n        *mode1 = 0x200005;')
    yield 'negative-wide-return', SELECTED.replace('u8 result;', 's32 result;')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3', symbols=None, entry=ENTRY):
    with patch.multiple(compiler, ENTRY=entry, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=symbols or SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, profile)


def install(before):
    if before.count(ORIGINAL) != 1:
        raise ValueError('expected one original metadata adapter placeholder')
    return before.replace('/* Non-matching placeholders', DECLARATIONS +
        '\n/* Non-matching placeholders', 1).replace(ORIGINAL, SELECTED)


RAW = tuple(int(word, 16) for word in '''
27BDFF98 AFBF003C AFA40068 AFA5006C AFA60070 AFA70074 8FAE0068 24030001
27AF0048 8DC40150 A3A30067 AFAF0010 27A50054 27A60050 27A7004C 0C000000
AFA40058 8FA40058 93A30067 8FA5006C 909800A4 8FA60070 8FA70074 33190001
13200025 8FA40068 3C080020 35080005 3C090006 ACA80000 35290600 ACC90000
8FAA0054 240200FF ACEA0000 8FAC0078 8FAB0050 AD8B0000 8FAE007C 8FAD004C
3C0B0010 ADCD0000 8FAF0080 240D0005 ADE20000 8FB9008C 8FB80048 240F002F
AF380000 8FA80088 AD180000 8FA90084 AD380000 8FAA0090 AD420000 8FAC0094
AD8B0000 8FAE0098 A1CD0000 8FB9009C 10000017 A32F0000 8FA80078 8FB8007C
8FA90080 8FAA0084 8FAB0088 8FAC008C 8FAD0090 8FAE0094 8FAF0098 8FB9009C
AFA80010 AFB80014 AFA90018 AFAA001C AFAB0020 AFAC0024 AFAD0028 AFAE002C
AFAF0030 0C000000 AFB90034 304300FF 00601025 8FBF003C 27BD0068 03E00008 00000000
'''.split())
RENAMES = ((33, 16, 2, 4), (44, 16, 2, 4), (46, 16, 24, 2),
    (48, 16, 24, 2), (50, 16, 24, 2), (52, 16, 24, 2), (54, 16, 2, 4),
    (59, 16, 25, 24), (61, 21, 25, 24), (62, 16, 8, 25), (63, 16, 24, 8),
    (71, 16, 25, 24), (72, 16, 8, 25), (73, 16, 24, 8), (82, 16, 25, 24))


def recipe(words):
    """Closed branch-local producer renames; no accesses or scheduling changes."""
    if len(words) != 89 or any((word & (0xFC000000 if i in (15, 81) else 0xFFFFFFFF)) != RAW[i]
            for i, word in enumerate(words)):
        raise ValueError('stale complete metadata adapter body')
    result = list(words)
    for index, shift, old, new in RENAMES:
        if result[index] >> shift & 31 != old:
            raise ValueError('stale metadata producer role')
        result[index] = result[index] & ~(31 << shift) | new << shift
    return result, [i * 4 for i in range(89)]


def guard_rows(path):
    text, functions, relocations = parse_object(path)
    target = functions[FUNCTION]
    if target['size'] != 356:
        raise ValueError('expected complete 89-word metadata adapter body')
    words = struct.unpack_from('>89I', text, target['value'])
    fitted, _ = recipe(words)
    spec = lambda uses: ';'.join(kind + ':' + symbol for kind, symbol in uses) or '-'
    rows = []
    for index, word in enumerate(words):
        uses = spec(relocations.get(target['value'] + index * 4, ()))
        rows.append(dict(filename='generated_1E0560', function=FUNCTION, offset='0x%X' % (index * 4),
            expected='0x%08X' % word, replacement='0x%08X' % fitted[index],
            expected_relocations=uses, replacement_relocations=uses,
            note='Normalize certified metadata adapter branch-local producer registers',
            insert_after='', insert_after_relocations='', omit='false'))
    return rows


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-metadata-adapter'
    records = []
    for name, body in candidates():
        profiles = compiler.PROFILES if name == 'selected' else ('o2g3',)
        for profile in profiles:
            meta, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
