"""Recover the view FOV/clip command with typed o32 float arguments."""
import argparse
import hashlib
import itertools
import re
import json
from pathlib import Path
import struct

from tools.experiments import game_remaining_donor_candidates as build

BUILD = 'conker/build/game-view-projection-command'
FUNCTION, OWNER, ENTRY, ROM, WORDS = 'func_1510B128', 'generated_138520', 0x1510B128, 0x1385D8, 129
SELECTED_LABEL = 'homes-1-0-2'
PATHS = {
    "elf": "conker/build/conker.us.elf",
    "owner": "conker/src/game/generated_138520.c",
    "parent": "conker/src/game_476D0.c",
    "guards": "conker/retail_word_patches.us.csv",
    "progress": "conker/progress.csv",
    "makefile": "conker/Makefile",
    "functions": "conker/include/functions.h",
    "variables": "conker/include/variables.h",
    "structs": "conker/include/structs.h",
    "original": "conker/asm/138520.s",
    "caller": "conker/asm/156160.s",
    "sinf": "conker/src/libultra/gu/sinf.c",
    "cosf": "conker/src/libultra/gu/cosf.c",
    "layout": "conker/retail_layout.us.txt"
}
BASELINE = {
    "original": "ad0efe574a623e2a2a9ef2446c7536d7ccf35a12d90388c7cf60aa947e519761",
    "caller": "4e10813d55b4483b99161e35e8178361de936b8e589725cb1dc81e24d6543954",
    "progress": "005fd7682d37802a2b7591cfb023648b6a083c8df6b957bdfedd737222cad68e",
    "layout": "a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5",
    "elf": "f36703ce83adebb99de90c1bc8061eec68431f36f6a366b90b2a331d25574c1a",
    "structs": "081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69",
    "functions": "2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81",
    "parent": "831ac69eb405bc46db96cf7f76d032f9eb9b021c89192f60843b2cd6e615f2d8",
    "owner": "152336b59dde6dca1da8d07cdb7b9ac5a8585725e0e76221315e404e19923d57",
    "variables": "1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8",
    "sinf": "ae271497692ea1a00abd96bcfed9209458cf8ea694b0df385aa5dddf9fc1a679",
    "guards": "c0bf9a67de2d35e5acb65eb383e82d9b6cd78323866ed44cba6a26c5998baf94",
    "cosf": "8947b41f56a8854981be155231dfbb5d4f0b885c4c60d4cdc7bba069f8841b09",
    "makefile": "838070597f76ea2f7182c158dfb6710946cfcabcb5435e994f93cdb99340e313"
}

PREAMBLE = '''typedef struct {
    u8 padding0[0xC];
    f32 extentX, extentY, axisScaleX, axisScaleY, projectionX, projectionY;
    u8 padding24[0x48];
    f32 baseFovX, baseFovY, fovX, fovY, projectionScaleX, projectionScaleY;
    u8 padding84[0xFC];
} ViewProjection138520;
#define PROJECTION_VIEWS_138520 ((ViewProjection138520 *)D_800BE628)
extern f32 D_800A2C24, D_800A2C28;
extern f32 D_800C3648, D_800C364C, D_800C3650, D_800D9B1C, D_800D9B20;
f32 sinf(f32);
f32 cosf(f32);
s32 func_1510B5F8(s32 index, u16 *normalization, f32 fovY, f32 fovX,
                  f32 nearPlane, f32 farPlane, f32 scale);
'''

BODY = '''/* Update effective FOVs, projection scales and the selected view's matrix. */
void func_1510B128(s32 index, f32 offsetX, f32 offsetY, f32 scale, f32 nearFallback) {
    f32 halfAngle, cosine, focalExtent, nearPlane, farPlane;

    PROJECTION_VIEWS_138520[index].fovX =
        PROJECTION_VIEWS_138520[index].baseFovX + offsetX + D_800C3648;
    PROJECTION_VIEWS_138520[index].fovY =
        PROJECTION_VIEWS_138520[index].baseFovY + offsetY + D_800C3648;
    halfAngle = PROJECTION_VIEWS_138520[index].fovX * D_800A2C24;
    cosine = cosf(halfAngle);
    focalExtent = cosine * PROJECTION_VIEWS_138520[index].extentX / sinf(halfAngle);
    PROJECTION_VIEWS_138520[index].projectionX =
        PROJECTION_VIEWS_138520[index].projectionScaleX *
        (PROJECTION_VIEWS_138520[index].axisScaleX * focalExtent) * scale;
    halfAngle = PROJECTION_VIEWS_138520[index].fovY * D_800A2C28;
    cosine = cosf(halfAngle);
    focalExtent = cosine * PROJECTION_VIEWS_138520[index].extentY / sinf(halfAngle);
    PROJECTION_VIEWS_138520[index].projectionY =
        PROJECTION_VIEWS_138520[index].projectionScaleY *
        (PROJECTION_VIEWS_138520[index].axisScaleY * focalExtent) * scale;
    nearPlane = D_800C364C != 0.0f ? D_800C364C :
        nearFallback != 0.0f ? nearFallback : D_800D9B20;
    farPlane = D_800C3650 != 0.0f ? D_800C3650 : D_800D9B1C;
    func_1510B5F8(index, (u16 *)(D_800BE628 + index * 0x180 + 0xB8),
        PROJECTION_VIEWS_138520[index].fovY, PROJECTION_VIEWS_138520[index].fovX,
        nearPlane, farPlane, scale);
}
'''


def recover(before, body=BODY):
    lo, hi = build.function_span(before, FUNCTION)
    result = before[:lo] + body.rstrip() + before[hi:]
    result = result.replace('extern u8 *D_800BE628;\n', 'extern u8 *D_800BE628;\n\n' + PREAMBLE, 1)
    result = result.replace('s32 func_1510B32C(', 'void func_1510B32C(', 1)
    result = result.replace('func_1510B128(arg0, *(s32 *)&arg1, *(s32 *)&arg2, *(s32 *)&arg3, 0);',
                            'func_1510B128(arg0, arg1, arg2, arg3, 0.0f);', 1)
    result = result.replace('s32 func_1510B5F8() {',
        's32 func_1510B5F8(s32 index, u16 *normalization, f32 fovY, f32 fovX,\n'
        '                  f32 nearPlane, f32 farPlane, f32 scale) {', 1)
    return result


def recover_parent(before):
    return before.replace('s32 func_1510B128(s32 index,', 'void func_1510B128(s32 index,', 1)


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        if {key: hashlib.sha256(value).hexdigest() for key, value in data.items()} != BASELINE:
            raise ValueError('Changed view-command baseline')
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Modified immutable view-command manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Modified immutable view-command input: ' + key)


def variants_initial():
    yield 'selected', BODY
    yield 'separate-locals', BODY.replace('f32 halfAngle, cosine, focalExtent, nearPlane, farPlane;',
        'f32 nearPlane, farPlane;\n    f32 halfAngle;\n    f32 cosine;\n    f32 focalExtent;')
    yield 'nested-if', BODY.replace(
        'nearPlane = D_800C364C != 0.0f ? D_800C364C :\n        nearFallback != 0.0f ? nearFallback : D_800D9B20;',
        'if (D_800C364C != 0.0f) { nearPlane = D_800C364C; }\n'
        '    else if (nearFallback != 0.0f) { nearPlane = nearFallback; }\n'
        '    else { nearPlane = D_800D9B20; }')
    yield 'expression-trig', BODY.replace('    cosine = cosf(halfAngle);\n    focalExtent = cosine *',
        '    focalExtent = cosf(halfAngle) *')


def variants():
    yield from variants_initial()
    nested = dict(variants_initial())['nested-if']
    for split in ('halfAngle', 'cosine', 'focalExtent', 'halfAngle,cosine',
                  'cosine,focalExtent', 'halfAngle,cosine,focalExtent'):
        fields = split.split(',')
        source = nested
        for name in fields:
            source = source.replace(name + ',', name + 'X, ' + name + 'Y,', 1)
        point = source.index('    halfAngle = PROJECTION_VIEWS_138520[index].fovY')
        opening, closing = source[:point], source[point:]
        declaration, opening = opening.split('\n\n', 1)
        for name in fields:
            opening = opening.replace(name, name + 'X')
            closing = closing.replace(name, name + 'Y')
        yield 'split-' + split.replace(',', '-'), declaration + '\n\n' + opening + closing
    for label, body in [('nested', nested), ('ternary', BODY)]:
        for mode in ('step-scale', 'swap-axis', 'reverse-cosine-product', 'direct-product'):
            result = body
            if mode == 'step-scale':
                for axis in ('X', 'Y'):
                    old = ('    PROJECTION_VIEWS_138520[index].projection' + axis + ' =\n'
                        '        PROJECTION_VIEWS_138520[index].projectionScale' + axis + ' *\n'
                        '        (PROJECTION_VIEWS_138520[index].axisScale' + axis + ' * focalExtent) * scale;')
                    new = ('    focalExtent = PROJECTION_VIEWS_138520[index].axisScale' + axis + ' * focalExtent;\n'
                        '    PROJECTION_VIEWS_138520[index].projection' + axis + ' =\n'
                        '        PROJECTION_VIEWS_138520[index].projectionScale' + axis + ' * focalExtent * scale;')
                    result = result.replace(old, new)
            elif mode == 'swap-axis':
                for axis in ('X', 'Y'):
                    result = result.replace('PROJECTION_VIEWS_138520[index].axisScale' + axis + ' * focalExtent',
                        'focalExtent * PROJECTION_VIEWS_138520[index].axisScale' + axis)
            elif mode == 'reverse-cosine-product':
                for axis in ('X', 'Y'):
                    result = result.replace('cosine * PROJECTION_VIEWS_138520[index].extent' + axis,
                        'PROJECTION_VIEWS_138520[index].extent' + axis + ' * cosine')
            elif mode == 'direct-product':
                result = result.replace('    cosine = cosf(halfAngle);\n    focalExtent = cosine *',
                    '    focalExtent = cosf(halfAngle) *')
            yield label + '-' + mode, result
    for clip, declaration, product in itertools.product(range(4), range(4), range(4)):
        result = nested
        old = ('if (D_800C364C != 0.0f) { nearPlane = D_800C364C; }\n'
            '    else if (nearFallback != 0.0f) { nearPlane = nearFallback; }\n'
            '    else { nearPlane = D_800D9B20; }')
        shapes = (
            'if (D_800C364C != 0.0f) { nearPlane = D_800C364C; }\n'
            '    else { nearPlane = nearFallback != 0.0f ? nearFallback : D_800D9B20; }',
            'nearPlane = D_800C364C;\n    if (nearPlane == 0.0f) {\n'
            '        nearPlane = nearFallback != 0.0f ? nearFallback : D_800D9B20;\n    }',
            old,
            'if (D_800C364C == 0.0f) {\n'
            '        nearPlane = nearFallback != 0.0f ? nearFallback : D_800D9B20;\n'
            '    } else { nearPlane = D_800C364C; }',
        )
        result = result.replace(old, shapes[clip])
        if declaration == 1:
            result = result.replace('f32 halfAngle, cosine, focalExtent, nearPlane, farPlane;',
                'f32 halfAngle;\n    f32 cosine;\n    f32 focalExtent;\n    f32 nearPlane;\n    f32 farPlane;')
        if declaration == 2:
            result = result.replace('    cosine = cosf(halfAngle);\n    focalExtent = cosine *',
                '    focalExtent = cosf(halfAngle) *')
        if declaration == 3:
            result = result.replace('f32 halfAngle, cosine, focalExtent, nearPlane, farPlane;',
                'f32 halfAngle, cosine, focalExtent;\n    f32 nearPlane, farPlane;')
        if product:
            result = result.replace('f32 halfAngle,', 'f32 axisScale, projectionScale;\n    f32 halfAngle,', 1)
            if 'f32 axisScale' not in result:
                result = result.replace('    f32 halfAngle;', '    f32 axisScale, projectionScale;\n    f32 halfAngle;', 1)
            for axis in ('X', 'Y'):
                old = ('    PROJECTION_VIEWS_138520[index].projection' + axis + ' =\n'
                    '        PROJECTION_VIEWS_138520[index].projectionScale' + axis + ' *\n'
                    '        (PROJECTION_VIEWS_138520[index].axisScale' + axis + ' * focalExtent) * scale;')
                first = '    axisScale = PROJECTION_VIEWS_138520[index].axisScale' + axis + ';\n'
                second = '    projectionScale = PROJECTION_VIEWS_138520[index].projectionScale' + axis + ';\n'
                expression = ('projectionScale * (axisScale * focalExtent)' if product != 3 else
                    '(axisScale * focalExtent) * projectionScale')
                result = result.replace(old, (first + second if product != 2 else second + first) +
                    '    PROJECTION_VIEWS_138520[index].projection' + axis + ' = ' + expression + ' * scale;')
        yield 'fit-%d-%d-%d' % (clip, declaration, product), result
    for split, style, snapshot in itertools.product(range(4), range(3), range(4)):
        result = nested
        if split:
            fields = (('cosine',), ('focalExtent',), ('cosine', 'focalExtent'))[split - 1]
            for name in fields:
                result = result.replace(name + ',', name + 'X, ' + name + 'Y,', 1)
            point = result.index('    halfAngle = PROJECTION_VIEWS_138520[index].fovY')
            opening, closing = result[:point], result[point:]
            declaration, opening = opening.split('\n\n', 1)
            for name in fields:
                opening, closing = opening.replace(name, name + 'X'), closing.replace(name, name + 'Y')
            result = declaration + '\n\n' + opening + closing
        if snapshot:
            result = result.replace('    f32 halfAngle,', '    f32 nearOverride;\n    f32 halfAngle,', 1)
            point = result.index('    if (D_800C364C')
            result = result[:point] + '    nearOverride = D_800C364C;\n' + result[point:].replace('D_800C364C', 'nearOverride')
            if snapshot >= 2:
                result = result.replace('    f32 nearOverride;', '    f32 farOverride;\n    f32 nearOverride;', 1)
                point = result.index('    farPlane = D_800C3650')
                result = result[:point] + '    farOverride = D_800C3650;\n' + result[point:].replace('D_800C3650', 'farOverride')
            if snapshot == 3:
                result = result.replace('    f32 farOverride;\n    f32 nearOverride;', '    f32 nearOverride, farOverride;', 1)
        if style:
            declaration, statements = result.split('\n\n', 1)
            if style == 1:
                line = next(x for x in declaration.splitlines() if 'f32 halfAngle,' in x)
                names = [x.strip() for x in line.strip()[4:-1].split(',')]
                declaration = declaration.replace(line, '\n'.join('    f32 ' + x + ';' for x in names))
            else:
                declaration = declaration.replace('halfAngle, ', '').replace('    f32 ', '    f32 halfAngle;\n    f32 ', 1)
            result = declaration + '\n\n' + statements
        yield 'homes-%d-%d-%d' % (split, style, snapshot), result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]*', args.filter):
        parser.error('filter must contain only label characters')
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    freeze(root, out)
    before = (out / 'before-owner').read_text()
    retail = list(struct.unpack_from('>129I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    rows = []
    for label, body in variants():
        if args.filter not in label:
            continue
        obj, diagnostics = build.compile_owner(root, out, recover(before, body), label)
        data, functions = build.link_owner(root, out, obj, OWNER)
        info = functions[FUNCTION]
        words = list(struct.unpack_from('>%dI' % (info['size'] // 4), data, info['value']))
        row = dict(label=label, code_bytes=info['size'],
            differences=[(i, hex(a), hex(b)) for i, (a, b) in enumerate(zip(words, retail)) if a != b],
            uncompared_slot_words=max(0, WORDS - len(words)), diagnostics=diagnostics,
            frame_bytes=(-words[0] & 0xFFFF), unused_cosine_control=body.count('cosine') == 1)
        rows.append(row)
        print(label, info['size'], len(row['differences']), row['uncompared_slot_words'], diagnostics, flush=True)
    suffix = '-' + args.filter.rstrip('-') if args.filter else ''
    (out / ('candidates' + suffix + '.json')).write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()

