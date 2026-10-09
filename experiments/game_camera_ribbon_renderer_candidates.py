"""Complete camera-facing ribbon renderer recovery; no production installation."""

import argparse
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x1514803C, 0x1754EC, 546
FUNCTION = 'func_1514803C'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_175250/func_1514803C.s")'
DECLARATIONS = '''typedef struct { f32 x, y, z; } CameraRibbonPosition;
typedef struct {
    CameraRibbonPosition position;
    f32 velocity;
    u16 phase, reserved;
} CameraRibbonRecord;
extern u8 D_800BE9C0;
extern s32 D_800DD1B0, D_80091564[];
extern u32 D_800915A4[], D_800D2C9C, D_800A4AC8[];
void func_151D5D60(void *, s16, s32, Vtx **, u8 *);
f32 *func_15144B34(s32);
s32 func_1514306C(void *, s32, s32, u8);
Gfx *func_150950D4(Gfx *, void *, s32, s32, s32, s32, s32, s32, s32, s32);
void func_151441A4(s16 *, s16 *, s16 *, s16 *, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8);
void func_151442FC(s16 *, s16 *, s16 *, s16 *, u8, u8, u8, u8, u8, u8, u8, u8, u8, u8);
Gfx *func_15142B7C(Gfx *, u32, u32);
Gfx *func_15142C10(Gfx *, s32, s32, s32, s32, u8 *);
Gfx *func_15142CF0(Gfx *, s32, s32, s32, s32, s32, s32, u8 *);
Gfx *func_1513F4E4(Gfx *, u8, u8 *);
Gfx *func_15142FBC(Gfx *, u32, u32, u8 *);
'''
SYMBOLS = dict(D_800BE9C0=0x800BE9C0, D_800DD1B0=0x800DD1B0,
    D_80091564=0x80091564, D_800915A4=0x800915A4, D_800D2C9C=0x800D2C9C,
    D_800A4AC8=0x800A4AC8, func_151D5D60=0x151D5D60, func_15144B34=0x15144B34,
    func_1514306C=0x1514306C, func_150950D4=0x150950D4, func_151441A4=0x151441A4,
    func_151442FC=0x151442FC, func_15142B7C=0x15142B7C, func_15142C10=0x15142C10,
    func_15142CF0=0x15142CF0, func_1513F4E4=0x1513F4E4, func_15142FBC=0x15142FBC)

OFFSET = '''    rayX = {point}.x - origin[0];
    rayY = {point}.y - origin[1];
    rayZ = {point}.z - origin[2];
    deltaY = previous.y - current.y;
    deltaZ = previous.z - current.z;
    deltaX = previous.x - current.x;
    normalX = deltaY * rayZ - rayY * deltaZ;
    normalY = deltaZ * rayX - rayZ * deltaX;
    normalZ = deltaX * rayY - rayX * deltaY;
    length = sqrtf(normalX * normalX + normalY * normalY + normalZ * normalZ);
    if (length == 0.0f) {{
        offsetX = offsetY = offsetZ = 0.0f;
    }} else {{
        scale = *(f32 *)payload / length;
        offsetX = normalX * scale;
        offsetY = normalY * scale;
        offsetZ = normalZ * scale;
    }}
'''
PAIR = '''    cursor->v.ob[0] = (s32)({position}.x + offsetX);
    cursor->v.ob[1] = (s32)({position}.y + offsetY);
    cursor->v.ob[2] = (s32)({position}.z + offsetZ);
    cursor->v.tc[1] = {record}->phase + 0x4000;
    cursor->v.tc[0] = 0x43C0;
    cursor->v.cn[0] = 255;
    cursor->v.cn[1] = 255;
    cursor->v.cn[2] = 255;
    cursor->v.cn[3] = 255;
    cursor->v.flag = 0;
    cursor++;
    cursor->v.ob[0] = (s32)({position}.x - offsetX);
    cursor->v.ob[1] = (s32)({position}.y - offsetY);
    cursor->v.ob[2] = (s32)({position}.z - offsetZ);
    cursor->v.tc[1] = {record}->phase + 0x4000;
    cursor->v.tc[0] = 0x4000;
    cursor->v.cn[0] = 255;
    cursor->v.cn[1] = 255;
    cursor->v.cn[2] = 255;
    cursor->v.cn[3] = 255;
    cursor->v.flag = 0;
    cursor++;
'''
SELECTED = '''Gfx *func_1514803C(u8 *actor, Gfx *output, s16 view) {
    Vtx *cursor;
    u8 sync;
    CameraRibbonPosition current;
    CameraRibbonPosition previous;
    u8 *payload;
    CameraRibbonRecord *records;
    f32 *origin;
    CameraRibbonRecord *point;
    CameraRibbonRecord *prior;
    s32 index;
    s32 previousIndex;
    s32 texture;
    s16 primitiveR, primitiveG, primitiveB, primitiveA;
    s16 environmentR, environmentG, environmentB, environmentA;
    f32 rayX, rayY, rayZ;
    f32 deltaX, deltaY, deltaZ;
    f32 normalX, normalY, normalZ;
    f32 length, scale;
    f32 offsetX, offsetY, offsetZ;

    payload = *(u8 **)(actor + 0x98);
    if (*(s8 *)(actor + 0x2C) < 2) {
        return output;
    }
    func_151D5D60(actor + 0x84, view, actor[0x25] * 32 - 32, &cursor, NULL);
    if (cursor == NULL) {
        return output;
    }
    if (cursor != NULL) {
        if (D_800BE9C0) {
            cursor += actor[0x25] * 2 - 2;
        }
        sync = 1;
        origin = func_15144B34(view);
        records = *(CameraRibbonRecord **)(actor + 0x94);
        texture = func_1514306C(NULL, payload[0x19], 0, 2);
        if (texture != D_800DD1B0) {
            D_800915A4[0] = D_80091564[payload[0x19]];
            output = func_150950D4(output, D_800915A4, 0, 0, 0, 0, 2, 256, 256,
                (payload[0x18] & 0x80) ? 62 : 3);
            D_800DD1B0 = texture;
        }
        func_151441A4(&primitiveR, &primitiveG, &primitiveB, &primitiveA,
            0, 0, 0, 0, 0, 0, 0, payload[0x1B], payload[0x1A], *(s8 *)(payload + 0x44));
        func_151442FC(&environmentR, &environmentG, &environmentB, &environmentA,
            0, 0, 0, 0, 0, 0, 0, payload[0x1B], payload[0x1A], *(s8 *)(payload + 0x45));
        output = func_15142B7C(output, *(u32 *)(payload + 0x2C), *(u32 *)(payload + 0x30));
        output = func_15142C10(output, environmentR, environmentG, environmentB, environmentA, &sync);
        output = func_15142CF0(output, 0, 0, primitiveR, primitiveG, primitiveB, primitiveA, &sync);
        output = func_1513F4E4(output, payload[0x3B], &sync);
        output = func_15142FBC(output, *(u32 *)(payload + 0x28) | 0x80000 | D_800D2C9C | 0x2C00 |
            *(u32 *)(payload + 0x3C) | *(u32 *)(payload + 0x40),
            D_800A4AC8[*(s32 *)(payload + 0x34) * 2 + 1] |
            D_800A4AC8[*(s32 *)(payload + 0x34) * 2], &sync);
        previousIndex = *(s8 *)(actor + 0x2E) - 1;
        if (previousIndex < 0) {
            previousIndex = actor[0x25] - 1;
        }
        index = previousIndex - 1;
        if (index < 0) {
            index = actor[0x25] - 1;
        }
        prior = records + previousIndex;
        previous = prior->position;
        point = records + index;
        current = point->position;
''' + ''.join('    ' + line if line else line for line in OFFSET.format(point='previous').splitlines(True)) + ''.join(
    '    ' + line if line else line for line in PAIR.format(position='previous', record='prior').splitlines(True)) + '''        do {
''' + ''.join('        ' + line if line else line for line in OFFSET.format(point='current').splitlines(True)) + '''            previousIndex = index;
            index--;
''' + ''.join('        ' + line if line else line for line in PAIR.format(position='current', record='point').splitlines(True)) + '''            gSPVertex(output++, cursor - 4, 4, 0);
            gSP1Triangle(output++, 0, 1, 2, 0);
            gSP1Triangle(output++, 1, 3, 2, 0);
            point--;
            if (index < 0) {
                index = actor[0x25] - 1;
                point = records + index;
            }
            previous = records[previousIndex].position;
            current = point->position;
        } while (previousIndex != *(s8 *)(actor + 0x2D));
    }
    return output;
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'separate-zero', SELECTED.replace('offsetX = offsetY = offsetZ = 0.0f;',
        'offsetX = 0.0f; offsetY = 0.0f; offsetZ = 0.0f;')
    yield 'single-gate', SELECTED.replace('    if (cursor != NULL) {', '    {')
    yield 'cursor-bytes', SELECTED.replace('cursor += actor[0x25] * 2 - 2;',
        'cursor = (Vtx *)((u8 *)cursor + (actor[0x25] * 2 - 2) * 16);')
    yield 'indexed-seed', SELECTED.replace('    CameraRibbonRecord *prior;\n', '').replace(
        '        prior = records + previousIndex;\n', '').replace('prior->', 'records[previousIndex].')
    yield 'reversed-locals', SELECTED.replace('    CameraRibbonPosition current;\n    CameraRibbonPosition previous;',
        '    CameraRibbonPosition previous;\n    CameraRibbonPosition current;')
    outer = SELECTED.replace('    if (*(s8 *)(actor + 0x2C) < 2) {\n        return output;\n    }',
        '    if (*(s8 *)(actor + 0x2C) >= 2) {').replace('    return output;\n}', '    }\n    return output;\n}')
    yield 'outer-active', outer
    indexed = outer.replace('    CameraRibbonRecord *prior;\n', '').replace(
        '        prior = records + previousIndex;\n', '').replace('prior->', 'records[previousIndex].')
    yield 'outer-indexed', indexed
    for name, base in (('outer', outer), ('indexed', indexed)):
        byte = base.replace('CameraRibbonRecord *records;', 'u8 *records;').replace(
            'records = *(CameraRibbonRecord **)', 'records = *(u8 **)').replace(
            'records + previousIndex', '(CameraRibbonRecord *)(records + previousIndex * 20)').replace(
            'records + index', '(CameraRibbonRecord *)(records + index * 20)').replace(
            'records[previousIndex].position', '*(CameraRibbonPosition *)(records + previousIndex * 20)').replace(
            'records[previousIndex].phase', '*(u16 *)(records + previousIndex * 20 + 16)')
        yield name + '-byte-records', byte
        shift = byte.replace('point = (CameraRibbonRecord *)(records + index * 20);',
            'point = (CameraRibbonRecord *)(records + (index * 4 + index) * 4);')
        yield name + '-shift-stride', shift
        for variable in ('rayX', 'rayY', 'rayZ'):
            yield name + '-reuse-' + variable, shift.replace('f32 length, scale;', 'f32 length;').replace('scale =', variable + ' =').replace('* scale;', '* ' + variable + ';')


def compile_candidate(root, output, name, body=SELECTED, profile='o2g3'):
    output.mkdir(parents=True, exist_ok=True)
    source, obj, elf = (output / (name + suffix) for suffix in ('.c', '.o', '.elf'))
    source.write_text('#include <ultra64.h>\n' + DECLARATIONS + body + '\n')
    result = subprocess.run(['ido/ido5.3_recomp/cc', '-c', '-32', '-G', '0', '-Xfullwarn', '-Xcpluscomm',
        '-signed', '-nostdinc', '-non_shared', '-Wab,-r4300_mul', '-mips2', '-o32',
        '-I', 'conker/include', '-I', 'conker/include/2.0L', '-I', 'conker/include/2.0L/PR',
        '-I', 'conker/include/libc', '-D_LANGUAGE_C', '-D_FINALROM', '-DF3DEX_GBI_2',
        '-D_MIPS_SZLONG=32', *PROFILES[profile], '-o', str(obj.relative_to(root)),
        str(source.relative_to(root))], cwd=root, capture_output=True, text=True)
    if result.returncode or result.stdout or result.stderr:
        raise ValueError(result.stdout + result.stderr)
    script = output / 'camera-ribbon-renderer.ld'
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
        saved_FP=[w >> 16 & 31 for w in words if w >> 26 == 61 and w >> 21 & 31 == 29],
        relocations=relocations, diagnostics='', pool_bytes=sum(len(v[1]) for n, v in pools.items()
            if n in ('.rodata', '.data'))), words


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    parser.add_argument('--form')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = root / 'conker/build/game-camera-ribbon-renderer'
    forms = dict(candidates())
    if args.form:
        if args.form not in forms:
            parser.error('unknown form: ' + args.form)
        forms = {args.form: forms[args.form]}
    receipts = []
    for name, body in forms.items():
        for profile in PROFILES if args.profiles else ('o2g3',):
            meta, _ = compile_candidate(root, output, name + '-' + profile, body, profile)
            receipts.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (output / ((args.form or 'all') + ('-profiles' if args.profiles else '') + '.json')).write_text(
        json.dumps(receipts, indent=2) + '\n')


if __name__ == '__main__':
    main()
