"""Recover the complete backward ring ribbon renderer and phase-wrap joins."""

import argparse
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151D80C4, 0x205574, 405
FUNCTION = 'func_151D80C4'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_204660/func_151D80C4.s")'
DECLARATIONS = '''typedef struct { f32 x, y, z; } RibbonPosition151D80C4;
typedef struct {
    RibbonPosition151D80C4 position;
    f32 velocity, length;
    u8 alpha, padding[3];
    f32 phase;
} RibbonRecord151D80C4;
extern u8 D_80090CD4[];
extern u32 D_800D2C9C, D_800A4AC8[];
extern f32 D_800DD1E8[], D_800DD1D8[];
void func_151D5D60(void *slots, s16 view, s32 size, Vtx **cursor, u8 *fresh);
Gfx *func_15142E24(Gfx *, void *, s32, s32, s32, s32, s32, u8, u8 *, u8 *, s32);
Gfx *func_15142B7C(Gfx *, u32, u32);
Gfx *func_1513F4E4(Gfx *, u8, u8 *);
Gfx *func_15142FBC(Gfx *, u32, u32, u8 *);
'''
SYMBOLS = dict(D_80090CD4=0x80090CD4, D_800D2C9C=0x800D2C9C,
    D_800A4AC8=0x800A4AC8, D_800DD1E8=0x800DD1E8, D_800DD1D8=0x800DD1D8,
    func_151D5D60=0x151D5D60, func_15142E24=0x15142E24,
    func_15142B7C=0x15142B7C, func_1513F4E4=0x1513F4E4,
    func_15142FBC=0x15142FBC, memcpy=0x10022EC0)
SELECTED = '''Gfx *func_151D80C4(u8 *owner, Gfx *output, s16 view) {
    RibbonPosition151D80C4 currentPosition;
    RibbonPosition151D80C4 previousPosition;
    RibbonRecord151D80C4 *records;
    RibbonRecord151D80C4 *payload;
    RibbonRecord151D80C4 *point;
    Vtx *cursor;
    u8 sync;
    f32 previousPhase;
    f32 currentPhase;
    f32 xOffset;
    f32 zOffset;
    s32 index;
    s32 previousIndex;
    s32 previousAlpha;
    s32 currentAlpha;
    s32 factor;
    s32 phase;
    s32 alpha;

    if (*(s8 *)(owner + 0x2C) < 2) {
        return output;
    }
    records = *(RibbonRecord151D80C4 **)(owner + 0x94);
    payload = *(RibbonRecord151D80C4 **)(owner + 0x98);
    func_151D5D60(owner + 0x84, view, owner[0x25] * 32 + 160, &cursor, NULL);
    if (cursor == NULL) {
        return output;
    }
    sync = 1;
    output = func_15142E24(output, D_80090CD4, 0, 0, 0, 0, 31, 0, NULL, &sync, 62);
    output = func_15142B7C(output, 0x200005, 0x1F0600);
    output = func_1513F4E4(output, 0x4C, &sync);
    output = func_15142FBC(output, D_800D2C9C | 0x80000 | 0x2CA0,
        D_800A4AC8[3] | D_800A4AC8[2], &sync);
    if (*(u16 *)(owner + 0x1E) & 2) {
        index = *(s8 *)(owner + 0x2E) - 1;
        if (index < 0) {
            index = owner[0x25] - 1;
        }
        previousPosition = *(RibbonPosition151D80C4 *)(owner + 0x10);
        previousAlpha = 0;
        previousPhase = payload->phase;
    } else {
        previousIndex = *(s8 *)(owner + 0x2E) - 1;
        if (previousIndex < 0) {
            previousIndex = owner[0x25] - 1;
        }
        index = previousIndex - 1;
        if (index < 0) {
            index = owner[0x25] - 1;
        }
        previousPosition = records[previousIndex].position;
        previousAlpha = records[previousIndex].alpha;
        previousPhase = records[previousIndex].phase;
    }
    point = records + index;
    currentPosition = point->position;
    xOffset = D_800DD1E8[view] * 5.5f;
    zOffset = D_800DD1D8[view] * 5.5f;
    currentAlpha = point->alpha;
    currentPhase = point->phase;
    if (*(u16 *)(owner + 0x1E) & 8) {
        factor = (*(s16 *)(owner + 0x1C) * 12) & 255;
    } else {
        factor = 255;
    }
    alpha = (previousAlpha * factor) >> 8;
    phase = (s32)previousPhase;
    cursor->v.ob[0] = (s32)(previousPosition.x + xOffset);
    cursor->v.ob[1] = (s32)previousPosition.y;
    cursor->v.ob[2] = (s32)(previousPosition.z - zOffset);
    cursor->v.tc[0] = phase;
    cursor->v.tc[1] = 0x800;
    cursor->v.cn[0] = 255;
    cursor->v.cn[1] = 255;
    cursor->v.cn[2] = 255;
    cursor->v.cn[3] = alpha;
    cursor->v.flag = 0;
    cursor++;
    cursor->v.ob[0] = (s32)(previousPosition.x - xOffset);
    cursor->v.ob[1] = (s32)previousPosition.y;
    cursor->v.ob[2] = (s32)(previousPosition.z + zOffset);
    cursor->v.tc[0] = phase;
    cursor->v.tc[1] = 0;
    cursor->v.cn[0] = 255;
    cursor->v.cn[1] = 255;
    cursor->v.cn[2] = 255;
    cursor->v.cn[3] = alpha;
    cursor->v.flag = 0;
    cursor++;
    do {
        alpha = (currentAlpha * factor) >> 8;
        phase = (s32)currentPhase;
        cursor->v.ob[0] = (s32)(currentPosition.x + xOffset);
        cursor->v.ob[1] = (s32)currentPosition.y;
        cursor->v.ob[2] = (s32)(currentPosition.z - zOffset);
        cursor->v.tc[0] = phase;
        cursor->v.tc[1] = 0x800;
        cursor->v.cn[0] = 255;
        cursor->v.cn[1] = 255;
        cursor->v.cn[2] = 255;
        cursor->v.cn[3] = alpha;
        cursor->v.flag = 0;
        cursor++;
        cursor->v.ob[0] = (s32)(currentPosition.x - xOffset);
        cursor->v.ob[1] = (s32)currentPosition.y;
        cursor->v.ob[2] = (s32)(currentPosition.z + zOffset);
        cursor->v.tc[0] = phase;
        cursor->v.tc[1] = 0;
        cursor->v.cn[0] = 255;
        cursor->v.cn[1] = 255;
        cursor->v.cn[2] = 255;
        cursor->v.cn[3] = alpha;
        cursor->v.flag = 0;
        cursor++;
        gSPVertex(output++, cursor - 4, 4, 0);
        gSP1Triangle(output++, 0, 1, 2, 0);
        gSP1Triangle(output++, 1, 3, 2, 0);
        if (currentPhase < previousPhase) {
            memcpy(cursor, cursor - 2, 32);
            cursor[-2].v.tc[0] -= 0x8000;
            cursor++;
            cursor[-2].v.tc[0] -= 0x8000;
            cursor++;
        }
        previousIndex = index;
        index--;
        point--;
        if (index < 0) {
            index = owner[0x25] - 1;
            point = records + index;
        }
        currentPosition = point->position;
        currentAlpha = point->alpha;
        previousPhase = records[previousIndex].phase;
        currentPhase = point->phase;
    } while (previousIndex != *(s8 *)(owner + 0x2D));
    return output;
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'array-records', SELECTED.replace('RibbonRecord151D80C4 *records;', 'u8 *records;').replace(
        'records = *(RibbonRecord151D80C4 **)', 'records = *(u8 **)').replace(
        'records[previousIndex].', '((RibbonRecord151D80C4 *)(records + previousIndex * 28))->').replace(
        'point = records + index;', 'point = (RibbonRecord151D80C4 *)(records + index * 28);')
    yield 'reversed-positions', SELECTED.replace('    RibbonPosition151D80C4 currentPosition;\n    RibbonPosition151D80C4 previousPosition;',
        '    RibbonPosition151D80C4 previousPosition;\n    RibbonPosition151D80C4 currentPosition;')
    yield 'unsigned-products', SELECTED.replace('(previousAlpha * factor)', '((u32)previousAlpha * factor)').replace(
        '(currentAlpha * factor)', '((u32)currentAlpha * factor)')
    yield 'outer-success', SELECTED.replace('    if (cursor == NULL) {\n        return output;\n    }',
        '    if (cursor != NULL) {').replace('    return output;\n}', '    }\n    return output;\n}')
    byte = SELECTED.replace('RibbonRecord151D80C4 *records;', 'u8 *records;').replace(
        'RibbonRecord151D80C4 *point;', 'u8 *point;').replace(
        'records = *(RibbonRecord151D80C4 **)', 'records = *(u8 **)').replace(
        'records[previousIndex].position', '*(RibbonPosition151D80C4 *)(records + previousIndex * 28)').replace(
        'records[previousIndex].alpha', 'records[previousIndex * 28 + 0x14]').replace(
        'records[previousIndex].phase', '*(f32 *)(records + previousIndex * 28 + 0x18)').replace(
        'point = records + index;', 'point = records + index * 28;').replace(
        'point->position', '*(RibbonPosition151D80C4 *)point').replace('point->alpha', 'point[0x14]').replace(
        'point->phase', '*(f32 *)(point + 0x18)').replace('        point--;', '        point -= 28;')
    yield 'byte-stride', byte
    reused = byte.replace('    s32 alpha;\n', '').replace('    alpha = (previousAlpha',
        '    previousAlpha = (previousAlpha').replace('        alpha = (currentAlpha',
        '        currentAlpha = (currentAlpha')
    seed, loop = reused.split('    do {', 1)
    reused = seed.replace(' = alpha;', ' = previousAlpha;') + '    do {' + loop.replace(' = alpha;', ' = currentAlpha;')
    yield 'byte-reused-alpha', reused
    reused = reused.replace('    s32 phase;\n', '').replace('    phase = (s32)previousPhase;',
        '    previousIndex = (s32)previousPhase;').replace('        phase = (s32)currentPhase;',
        '        previousIndex = (s32)currentPhase;').replace(' = phase;', ' = previousIndex;')
    yield 'byte-reused-phase', reused
    factored = reused.replace('previousIndex * 28', '(previousIndex * 8 - previousIndex) * 4').replace(
        'index * 28', '(index * 8 - index) * 4')
    yield 'factored-stride', factored
    yield 'factored-byte-alpha', factored.replace('s32 previousAlpha;', 'u8 previousAlpha;').replace(
        's32 currentAlpha;', 'u8 currentAlpha;')
    yield 'byte-factor-else', reused.replace('    if (*(u16 *)(owner + 0x1E) & 8) {',
        '    if (!(*(u16 *)(owner + 0x1E) & 8)) {\n        factor = 255;\n    } else {').replace(
        '    } else {\n        factor = 255;\n    }', '    }')
    floating = reused.replace('u8 *records;', 'f32 *records;').replace('u8 *point;', 'f32 *point;').replace(
        'records = *(u8 **)', 'records = *(f32 **)').replace('previousIndex * 28', 'previousIndex * 7').replace(
        'records[previousIndex * 7 + 0x14]', '((u8 *)(records + previousIndex * 7))[0x14]').replace(
        '*(f32 *)(records + previousIndex * 7 + 0x18)', 'records[previousIndex * 7 + 6]').replace(
        'records + index * 28', 'records + index * 7').replace('point[0x14]', '((u8 *)point)[0x14]').replace(
        '*(f32 *)(point + 0x18)', 'point[6]').replace('point -= 28;', 'point -= 7;')
    yield 'float-stride', floating
    for name, body in (('float-stride', floating), ('byte-reused-phase', reused)):
        yield name + '-phase-at-store', body.replace('    previousIndex = (s32)previousPhase;\n', '').replace(
            '        previousIndex = (s32)currentPhase;\n', '').replace(
            'cursor->v.tc[0] = previousIndex;', 'cursor->v.tc[0] = (s32)previousPhase;', 2).replace(
            'cursor->v.tc[0] = previousIndex;', 'cursor->v.tc[0] = (s32)currentPhase;')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    out.mkdir(exist_ok=True)
    source, obj, elf = (out / (name + suffix) for suffix in ('.c', '.o', '.elf'))
    source.write_text('#include <ultra64.h>\n#include <string.h>\n' + DECLARATIONS + '\n' + body + '\n')
    result = subprocess.run(['ido/ido5.3_recomp/cc', '-c', '-32', '-G', '0', '-Xfullwarn', '-Xcpluscomm',
        '-signed', '-nostdinc', '-non_shared', '-Wab,-r4300_mul', '-mips2', '-o32',
        '-I', 'conker/include', '-I', 'conker/include/2.0L', '-I', 'conker/include/2.0L/PR',
        '-I', 'conker/include/libc', '-D_LANGUAGE_C', '-D_FINALROM', '-DF3DEX_GBI_2',
        '-D_MIPS_SZLONG=32', *PROFILES[profile], '-o', str(obj.relative_to(root)),
        str(source.relative_to(root))], cwd=root, capture_output=True, text=True)
    if result.returncode or result.stdout or result.stderr:
        raise ValueError(result.stdout + result.stderr)
    script = out / 'record-ring-renderer.ld'
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
    return dict(name=name, profile=profile, body_words=end, frame=(-words[0]) & 65535,
        saved_FP=[w >> 16 & 31 for w in words if w >> 26 == 61 and w >> 21 & 31 == 29],
        differences=sum(a != b for a, b in itertools.zip_longest(words, retail, fillvalue=0)),
        diagnostics='', relocations=relocations,
        pool_bytes=sum(len(v[1]) for n, v in pools.items() if n in ('.rodata', '.data'))), words


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-record-ring-renderer'
    records = []
    for name, body in candidates():
        for profile in PROFILES if args.profiles else ('o2g3',):
            record, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(record)
            print(record['name'], record['body_words'], hex(record['frame']), record['differences'], flush=True)
    (out / ('profiles.json' if args.profiles else 'measurements.json')).write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
