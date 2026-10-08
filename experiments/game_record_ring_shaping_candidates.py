"""Recover live backward ring trimming, wrapped phase and unsigned fade bytes."""

import argparse
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151D7CD0, 0x205180, 253
FUNCTION = 'func_151D7CD0'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_204660/func_151D7CD0.s")'
DECLARATIONS = '''typedef struct { f32 x, y, z; } ShapingVector151D7CD0;
extern f32 D_800BE9A4;
extern f32 D_800AB2DC, D_800AB2E0, D_800AB2E4, D_800AB2E8;
f32 func_15143E64(f32 *vector);
f32 func_15144528(f32 value, f32 upper, f32 lower);
'''
SYMBOLS = {'D_800BE9A4': 0x800BE9A4, 'D_800AB2DC': 0x800AB2DC,
    'D_800AB2E0': 0x800AB2E0, 'D_800AB2E4': 0x800AB2E4,
    'D_800AB2E8': 0x800AB2E8, 'func_15143E64': 0x15143E64,
    'func_15144528': 0x15144528}
BASE = '''s32 func_151D7CD0(u8 *owner) {
    f32 *payload;
    f32 *records;
    f32 *previous;
    f32 *record;
    f32 vector[3];
    f32 total;
    f32 fraction;
    f32 distance;
    f32 start;
    f32 width;
    f32 inverse;
    s32 index;

    payload = *(f32 **)(owner + 0x98);
    records = *(f32 **)(owner + 0x94);
    if (*(s8 *)(owner + 0x2C) >= 2) {
        total = 0.0f;
        index = *(s8 *)(owner + 0x2E);
        if (*(u16 *)(owner + 0x1E) & 2) {
            previous = (f32 *)(owner + 0x10);
        } else {
            index--;
            if (index < 0) {
                index = owner[0x25] - 1;
            }
            previous = records + index * 7;
        }
        do {
            index--;
            if (index < 0) {
                index = owner[0x25] - 1;
            }
            record = records + index * 7;
            vector[0] = record[0] - previous[0];
            vector[1] = record[1] - previous[1];
            vector[2] = record[2] - previous[2];
            fraction = func_15143E64(vector);
            total += fraction;
            record[4] = fraction;
            if (total > 80.0f) {
                if (record[4] != 0.0f) {
                    fraction = (total - 80.0f) * (1.0f / record[4]);
                    record[0] -= vector[0] * fraction;
                    record[1] -= vector[1] * fraction;
                    record[2] -= vector[2] * fraction;
                    record[4] *= 1.0f - fraction;
                }
                total = 80.0f;
                while (index != *(s8 *)(owner + 0x2D)) {
                    owner[0x2D] = *(s8 *)(owner + 0x2D) + 1;
                    if (*(s8 *)(owner + 0x2D) == owner[0x25]) {
                        owner[0x2D] = 0;
                    }
                    owner[0x2C] = *(s8 *)(owner + 0x2C) - 1;
                }
            }
            previous = record;
        } while (index != *(s8 *)(owner + 0x2D));
    }
    if (*(s8 *)(owner + 0x2C) >= 2) {
        payload[6] += -41.0f * D_800BE9A4;
        payload[6] = func_15144528(payload[6], D_800AB2DC, -16384.0f);
        distance = 0.0f;
        index = *(s8 *)(owner + 0x2E);
        do {
            index--;
            if (index < 0) {
                index = owner[0x25] - 1;
            }
            record = records + index * 7;
            distance += record[4];
            record[6] = func_15144528(payload[6] + distance * D_800AB2E0,
                D_800AB2E4, -16384.0f);
        } while (index != *(s8 *)(owner + 0x2D));
    }
    if (*(s8 *)(owner + 0x2C) >= 2) {
        start = total * D_800AB2E8;
        width = total - start;
        inverse = 1.0f / width;
        distance = 0.0f;
        index = *(s8 *)(owner + 0x2E);
        do {
            index--;
            if (index < 0) {
                index = owner[0x25] - 1;
            }
            record = records + index * 7;
            if (start < distance) {
                fraction = distance - start;
                if (width < fraction) {
                    fraction = width;
                }
                ((u8 *)record)[0x14] = (u32)((width - fraction) * inverse * 60.0f);
            } else {
                ((u8 *)record)[0x14] = 60;
            }
            distance += record[4];
        } while (index != *(s8 *)(owner + 0x2D));
    }
    return 1;
}'''
SELECTED = BASE


def candidates():
    yield 'selected', SELECTED
    yield 'negative-reassociated-divide', BASE.replace('(total - 80.0f) * (1.0f / record[4])', '(total - 80.0f) / record[4]')
    byte = BASE.replace('f32 *records;', 'u8 *records;').replace(
        'records = *(f32 **)', 'records = *(u8 **)').replace('records + index * 7', '(f32 *)(records + index * 0x1C)')
    yield 'byte-stride', byte
    for name, body in (('natural', BASE), ('byte', byte)):
        yield name + '-integer-zeros', body.replace('0.0f', '0')
        vector = body.replace('f32 vector[3];', 'ShapingVector151D7CD0 vector;').replace(
            'func_15143E64(vector)', 'func_15143E64((f32 *)&vector)')
        for index, axis in enumerate('xyz'):
            vector = vector.replace('vector[%d]' % index, 'vector.' + axis)
        yield name + '-struct-vector', vector
        yield name + '-struct-integer-zeros', vector.replace('0.0f', '0')
        phased = body.replace('    f32 distance;\n', '').replace('    s32 index;\n', '')
        phased = phased.replace('        total = 0.0f;', '        s32 index;\n\n        total = 0.0f;')
        phased = phased.replace('        payload[6] +=', '        s32 index;\n        f32 distance;\n\n        payload[6] +=')
        phased = phased.replace('        start = total', '        s32 index;\n        f32 distance;\n\n        start = total')
        yield name + '-phase-locals', phased
        yield name + '-phase-integer-zeros', phased.replace('0.0f', '0')
    for field in ('vector', 'total', 'index', 'record'):
        line = {'vector': '    f32 vector[3];', 'total': '    f32 total;', 'index': '    s32 index;', 'record': '    f32 *record;'}[field]
        yield 'first-' + field, BASE.replace(line + '\n', '').replace('    f32 *payload;', line + '\n    f32 *payload;')
    yield 'reverse-count-compare', BASE.replace('*(s8 *)(owner + 0x2D) == owner[0x25]', 'owner[0x25] == *(s8 *)(owner + 0x2D)')
    yield 'negative-unsigned-state', BASE.replace('*(s8 *)(owner + 0x2C)', 'owner[0x2C]')
    yield 'negative-unsigned-current', BASE.replace('*(s8 *)(owner + 0x2E)', 'owner[0x2E]')
    yield 'negative-unsigned-goal', BASE.replace('*(s8 *)(owner + 0x2D)', 'owner[0x2D]')
    yield 'negative-signed-count', BASE.replace('owner[0x25]', '*(s8 *)(owner + 0x25)')
    yield 'negative-live-buffer', BASE.replace('record = records + index * 7;', 'record = *(f32 **)(owner + 0x94) + index * 7;')
    yield 'negative-limit', BASE.replace('80.0f', '81.0f')
    yield 'negative-phase-sign', BASE.replace('-41.0f', '41.0f')
    yield 'negative-no-state-reload', BASE.replace('    f32 *payload;', '    s32 state;\n    f32 *payload;').replace(
        '    payload =', '    state = *(s8 *)(owner + 0x2C);\n    payload =', 1).replace('if (*(s8 *)(owner + 0x2C) >= 2)', 'if (state >= 2)')
    yield 'negative-signed-fade', BASE.replace('(u32)((width - fraction)', '(s32)((width - fraction)')
    yield 'negative-return', BASE.replace('    return 1;', '    return 0;')


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
    script = out / 'record-ring-shaping.ld'
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
    out = root / 'conker/build/game-record-ring-shaping'
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
