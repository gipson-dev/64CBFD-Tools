"""Measure the seven-mode object color/opacity helper without installing it."""
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1502EC34, 0x5C0E4, 150
FUNCTION = 'func_1502EC34'
SOURCE = 'conker/src/game/generated_58F80.c'
DECLARATIONS = 'extern f32 D_80096F38, D_80096F3C;\nf32 cosf(f32);\n'
SYMBOLS = dict(D_80096F38=0x80096F38, D_80096F3C=0x80096F3C, cosf=0x15047C00)
BASE = '''void func_1502EC34(u8 *object, s32 *red, s32 *green, s32 *blue, s32 *opacity) {
    s32 high, value;
    f32 amount;

    switch (object[0xA4]) {
    case 1:
        *red = object[0xA5];
        *green = object[0xA6];
        *blue = object[0xA7];
        value = *(s32 *)(object + 0xA0);
        if ((u32)value >= 256) {
            amount = *(f32 *)value;
            amount = amount < 0.0f ? 0.0f : (amount > 255.0f ? 255.0f : amount);
            *opacity = (s32)(amount * D_80096F38);
        } else {
            *opacity = value;
        }
        break;
    case 2:
    case 3:
        *red = 0;
        *green = 0;
        *blue = 0;
        value = object[0xA5];
        *opacity = value;
        if (object[0xA4] == 3) {
            *opacity = 255 - value;
        }
        break;
    case 4:
    case 5:
        value = *(s32 *)(object + 0xA0);
        high = (value >> 24) & 255;
        *red = (value >> 16) & 255;
        *green = (*(s32 *)(object + 0xA0) >> 8) & 255;
        *blue = *(s32 *)(object + 0xA0) & 255;
        value = (s32)(high + 64.0f * ((cosf((u32)object[0xA5] * D_80096F3C) + 1.0f) * 0.5f));
        *opacity = value;
        *opacity = value + (((255 - value) * (255 - object[0xA7])) >> 8);
        break;
    case 6:
    case 7:
        value = *(s32 *)(object + 0xA0);
        *red = (value >> 16) & 255;
        high = (value >> 24) & 255;
        *green = (*(s32 *)(object + 0xA0) >> 8) & 255;
        *blue = *(s32 *)(object + 0xA0) & 255;
        *opacity = 255 - ((object[0xA5] * high) >> 8);
        break;
    }
}'''
SELECTED = BASE.replace('    s32 high, value;', '    s32 reserved0, reserved1;\n    s32 high, value;').replace(
    '        value = (s32)(high + 64.0f * ((cosf((u32)object[0xA5] * D_80096F3C) + 1.0f) * 0.5f));',
    '        amount = cosf((u32)object[0xA5] * D_80096F3C);\n'
    '        value = (s32)(high + 64.0f * ((amount + 1.0f) * 0.5f));')


def candidates():
    yield 'selected', SELECTED
    yield 'compact', BASE
    for count in range(1, 5):
        yield 'reserved-%d' % count, BASE.replace('    s32 high, value;',
            '    s32 ' + ', '.join('reserved%d' % i for i in range(count)) + ';\n    s32 high, value;')
    for index, expression in enumerate(('64.0f * ((amount + 1.0f) * 0.5f) + high',
            'high + ((amount + 1.0f) * 0.5f) * 64.0f',
            '(high + 64.0f * ((amount + 1.0f) * 0.5f))')):
        yield 'expression-%d' % index, BASE.replace('    s32 high, value;', '    s32 reserved, high, value;').replace(
            '        value = (s32)(high + 64.0f * ((cosf((u32)object[0xA5] * D_80096F3C) + 1.0f) * 0.5f));',
            '        amount = cosf((u32)object[0xA5] * D_80096F3C);\n        value = (s32)(' + expression + ');')
    yield 'separate-color', BASE.replace('    s32 high, value;', '    s32 reserved, high, value, color;').replace(
        '        value = *(s32 *)(object + 0xA0);\n        *red = (value >> 16) & 255;\n        high = (value >> 24) & 255;',
        '        color = *(s32 *)(object + 0xA0);\n        *red = (color >> 16) & 255;\n        high = (color >> 24) & 255;')
    yield 'locals-reordered', BASE.replace('s32 high, value;', 's32 value, high;')
    yield 'clamp-if', BASE.replace('            amount = amount < 0.0f ? 0.0f : (amount > 255.0f ? 255.0f : amount);',
        '            if (amount < 0.0f) amount = 0.0f;\n            else if (amount > 255.0f) amount = 255.0f;')
    yield 'separate-amount', BASE.replace('        value = (s32)(high + 64.0f * ((cosf((u32)object[0xA5] * D_80096F3C) + 1.0f) * 0.5f));',
        '        amount = cosf((u32)object[0xA5] * D_80096F3C);\n'
        '        value = (s32)(high + 64.0f * ((amount + 1.0f) * 0.5f));')
    yield 'negative-cache-mode', BASE.replace('    s32 high, value;', '    s32 high, value, mode;').replace(
        '    switch (object[0xA4])', '    mode = object[0xA4];\n    switch (mode)').replace('if (object[0xA4] == 3)', 'if (mode == 3)')
    yield 'negative-cache-word', BASE.replace('(*(s32 *)(object + 0xA0) >> 8)', '(value >> 8)').replace(
        '*blue = *(s32 *)(object + 0xA0) & 255;', '*blue = value & 255;')
    yield 'negative-byte-opacity', BASE.replace('*opacity = (s32)(amount * D_80096F38);',
        '*opacity = (u8)(s32)(amount * D_80096F38);')
    yield 'negative-unsigned-product', BASE.replace('(((255 - value) * (255 - object[0xA7])) >> 8)',
        '(((u32)(255 - value) * (255 - object[0xA7])) >> 8)')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, profile)


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-object-color-mode'
    records = []
    for name, body in candidates():
        for profile in compiler.PROFILES if name == 'selected' else ('o2g3',):
            meta, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], meta['pool_bytes'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
