"""Screen the complete distance-to-level helper and retained source controls."""

import argparse
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151D8C00, 0x2060B0, 87
FUNCTION = 'func_151D8C00'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_205C90/func_151D8C00.s")'
DECLARATIONS = '''typedef struct {
    f32 x, y, z;
    f32 inner, width, inverseWidth;
    u8 player;
} RecordDistanceLevel;
f32 *func_15144B34(s32 player);
f32 func_15143E64(f32 *vector);
'''
SYMBOLS = {'func_15144B34': 0x15144B34, 'func_15143E64': 0x15143E64}
SELECTED = '''void func_151D8C00(u8 *owner, RecordDistanceLevel *parameters) {
    f32 *origin;
    f32 delta[3];
    f32 distance;
    f32 level;

    origin = func_15144B34(parameters->player);
    delta[0] = parameters->x - origin[0];
    delta[1] = parameters->y - origin[1];
    delta[2] = parameters->z - origin[2];
    distance = func_15143E64(delta);
    if (distance < parameters->inner) {
        level = 1.0f;
    } else if (parameters->inner + parameters->width < distance) {
        level = 0.0f;
    } else {
        level = 1.0f - (distance - parameters->inner) * parameters->inverseWidth;
    }
    owner[0x12] = (u32)(level * 8.0f);
}'''


def candidates():
    yield 'initial', SELECTED
    raw = SELECTED.replace('RecordDistanceLevel *parameters', 'u8 *parameters').replace('parameters->player', 'parameters[0x18]')
    for field,index in (('x',0),('y',1),('z',2),('inner',3),('width',4),('inverseWidth',5)):
        raw = raw.replace('parameters->'+field, '((f32 *)parameters)[%d]'%index)
    yield 'raw-byte-parameters', raw
    yield 'volatile-parameters', SELECTED.replace('RecordDistanceLevel *parameters', 'RecordDistanceLevel *volatile parameters')
    yield 'volatile-owner', SELECTED.replace('u8 *owner', 'u8 *volatile owner')
    yield 'volatile-both', SELECTED.replace('u8 *owner', 'u8 *volatile owner').replace(
        'RecordDistanceLevel *parameters', 'RecordDistanceLevel *volatile parameters')
    yield 'delta-first-local', SELECTED.replace('    f32 *origin;\n    f32 delta[3];', '    f32 delta[3];\n    f32 *origin;')
    yield 'unsigned-long-cast', SELECTED.replace('(u32)(level', '(unsigned long)(level')
    yield 'signed-cast-control', SELECTED.replace('(u32)(level', '(s32)(level')
    yield 'byte-cast-control', SELECTED.replace('(u32)(level', '(u8)(level')
    yield 'named-scaled-level', SELECTED.replace('    f32 level;', '    f32 level;\n    f32 scaled;').replace(
        '    owner[0x12] = (u32)(level * 8.0f);', '    scaled = level * 8.0f;\n    owner[0x12] = (u32)scaled;')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    out.mkdir(exist_ok=True)
    source, obj, elf = (out / (name + suffix) for suffix in ('.c', '.o', '.elf'))
    source.write_text('#include <ultra64.h>\n' + DECLARATIONS + '\n' + body + '\n')
    result = subprocess.run(['ido/ido5.3_recomp/cc', '-c', '-32', '-G', '0', '-Xfullwarn', '-Xcpluscomm',
        '-signed', '-nostdinc', '-non_shared', '-Wab,-r4300_mul', '-mips2', '-o32',
        '-I', 'conker/include', '-I', 'conker/include/2.0L', '-I', 'conker/include/2.0L/PR',
        '-D_LANGUAGE_C', '-D_FINALROM', '-DF3DEX_GBI_2', '-D_MIPS_SZLONG=32', *PROFILES[profile],
        '-o', str(obj.relative_to(root)), str(source.relative_to(root))], cwd=root, capture_output=True, text=True)
    if result.returncode or result.stdout or result.stderr:
        raise ValueError(result.stdout + result.stderr)
    script = out / 'record-distance-level.ld'
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % ENTRY)
    subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', FUNCTION,
        *['--defsym=%s=0x%X' % item for item in SYMBOLS.items()],
        '-o', str(elf), str(obj)], check=True, capture_output=True)
    _, functions, relocs = parse_object(obj)
    meta, pools = functions[FUNCTION], sections(elf)
    words = list(struct.unpack_from('>%dI' % (meta['size'] // 4), pools['.text'][1], meta['value']))
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    assert not any(words[end:])
    words = words[:end]
    retail = struct.unpack_from('>%dI' % WORDS, (root / 'conker/conker.us.bin').read_bytes(), ROM)
    frames = [(-word) & 65535 for word in words if word & 0xFFFF0000 == 0x27BD0000 and word & 0x8000]
    return dict(name=name, profile=profile, body_words=end, frame=frames[0] if frames else 0,
        differences=sum(a != b for a, b in itertools.zip_longest(words, retail, fillvalue=0)),
        diagnostics='', relocations=relocs, pool_bytes=sum(len(v[1]) for n, v in pools.items()
            if n in ('.rodata', '.data'))), words


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-record-distance-level'
    forms = [('profile-' + p, SELECTED, p) for p in PROFILES] if args.profiles else (
        [(name, body, 'o2g3') for name, body in candidates()])
    records = []
    for name, body, profile in forms:
        record, _ = compile_candidate(root, out, name, body, profile)
        records.append(record)
        print(name, record['body_words'], hex(record['frame']), record['differences'], flush=True)
    (out / ('profiles.json' if args.profiles else 'measurements.json')).write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
