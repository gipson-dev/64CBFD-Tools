"""Recover the optional proximity call and delayed node effect allocation."""

import argparse
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.experiments.game_node_effect_registration_candidates import ALLOCATOR
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x15033AD8, 0x60F88, 65
FUNCTION = 'func_15033AD8'
STUB = 's32 func_15033AD8() {\n    return 0;\n}'
ADDED_DECLARATIONS = 'extern u8 D_800BE616;\nvoid func_1508B20C(f32, f32, f32, f32);\n'
DECLARATIONS = ADDED_DECLARATIONS + 'extern s32 D_800BE9E4;\ns32 func_15033BDC();\n' + ALLOCATOR
SYMBOLS = {name: int(name[5:], 16) for name in ('func_1508B20C', 'func_15033BDC', 'func_1000FA64')}
SYMBOLS.update(D_800BE616=0x800BE616, D_800BE9E4=0x800BE9E4)
SELECTED = '''s32 func_15033AD8(u8 *node, u8 *actor) {
    if (D_800BE616 != 0) {
        func_1508B20C(*(f32 *)(actor + 0x14), *(f32 *)(actor + 0x18),
            *(f32 *)(actor + 0x1C), 900.0f);
    }
    if (*(s32 *)(node + 0x38) == 0) {
        if (*(s32 *)(node + 0x3C) < 30) {
            *(s32 *)(node + 0x3C) += D_800BE9E4;
        } else {
            *(s32 *)(node + 0x3C) = func_1000FA64(0x513,
                (s16)*(f32 *)(actor + 0x14), (s16)*(f32 *)(actor + 0x18),
                (s16)*(f32 *)(actor + 0x1C), 32000, 1000, 500,
                (s32)func_15033BDC, node, (s32)actor, 0, 0);
            *(s32 *)(node + 0x38) = 0x513;
        }
    }
    return 0;
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'register-both', SELECTED.replace('u8 *node, u8 *actor)', 'register u8 *node, register u8 *actor)')
    yield 'unsigned-wrap', SELECTED.replace('*(s32 *)(node + 0x3C) += D_800BE9E4',
        '*(u32 *)(node + 0x3C) += (u32)D_800BE9E4')
    yield 'implicit-narrowing', SELECTED.replace('(s16)*(f32 *)', '(s32)*(f32 *)')
    yield 'negative-skip-proximity', SELECTED.replace('D_800BE616 != 0', 'D_800BE616 == 0')
    yield 'negative-byte-state', SELECTED.replace('*(s32 *)(node + 0x38)', 'node[0x38]')
    yield 'negative-unsigned-timer', SELECTED.replace('*(s32 *)(node + 0x3C) < 30', '*(u32 *)(node + 0x3C) < 30')
    yield 'negative-inclusive-threshold', SELECTED.replace('< 30', '<= 30')
    yield 'negative-wrong-step', SELECTED.replace('+= D_800BE9E4', '+= 1')
    yield 'negative-high-handle-bit', SELECTED.replace('node, (s32)actor, 0, 0);', 'node, (s32)actor, 0, 0) | 0x80000000;')
    yield 'negative-wrong-effect', SELECTED.replace('func_1000FA64(0x513,', 'func_1000FA64(0x448,')
    yield 'negative-wrong-state', SELECTED.replace('= 0x513;', '= 0x448;')
    yield 'negative-wrong-radius', SELECTED.replace('900.0f', '90.0f')
    yield 'negative-integer-coordinates', SELECTED.replace('(s16)*(f32 *)', '(s16)*(s32 *)')


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
    script = out / 'delayed-effect.ld'
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
    out = root / 'conker/build/game-node-delayed-effect'
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
