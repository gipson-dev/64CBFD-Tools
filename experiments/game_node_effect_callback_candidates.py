"""Recover the seven-argument node effect callback and its sound lifecycle."""

import argparse
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.experiments.game_node_effect_registration_candidates import ALLOCATOR
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x15033BDC, 0x6108C, 137
FUNCTION = 'func_15033BDC'
STUB = 's32 func_15033BDC() {\n    return 0;\n}'
ADDED_DECLARATIONS = '''s32 func_150ADA20(void);
u16 func_10010FFC(s32, s32, u16, s16, u8, void *);
void func_100111C8(u16);
'''
DECLARATIONS = ADDED_DECLARATIONS + ALLOCATOR
SYMBOLS = {name: int(name[5:], 16) for name in ('func_150ADA20', 'func_10010FFC', 'func_100111C8', 'func_1000FA64', 'func_15033BDC')}
SELECTED = '''s32 func_15033BDC(u8 *packet, s32 *value, s32 *volume, s32 *pan,
    s32 *cents, s32 *fx, u16 *sound) {
    u8 *node;
    u8 *actor;
    u8 *state;
    s32 soundId;
    s32 cached;

    node = *(u8 **)(packet + 0x18);
    actor = *(u8 **)(packet + 0x1C);
    if ((node != 0) && (actor != 0) && (*(s32 *)actor != 0)) {
        *(s16 *)(packet + 2) = (s16)*(f32 *)(actor + 0x14);
        *(s16 *)(packet + 4) = (s16)*(f32 *)(actor + 0x18);
        *(s16 *)(packet + 6) = (s16)*(f32 *)(actor + 0x1C);
        if (*volume != 0) {
            if (node[1] == 0x37) {
                cached = *(s32 *)(node + 0x38);
                soundId = -1;
                if ((cached & 0xFFFF) != *(u16 *)(actor + 0x84)) {
                    if (*(u16 *)(actor + 0x84) == 0x15F) {
                        soundId = (func_150ADA20() & 3) + 0x444;
                    }
                }
                if (soundId != -1) {
                    func_10010FFC(0, soundId, 24000, 0, 0, actor);
                }
                *(s32 *)(node + 0x38) = *(u16 *)(actor + 0x84);
                return 0;
            } else {
                state = *(u8 **)(actor + 0x31C);
                if ((state != 0) && (*(u16 *)(state + 0x19C) < 120) &&
                    (*(s32 *)(node + 0x38) == 0x513)) {
                    *(s32 *)(node + 0x38) = 0x3A1;
                    *(s32 *)(node + 0x3C) = func_1000FA64(0x3A1,
                        (s16)*(f32 *)(actor + 0x14), (s16)*(f32 *)(actor + 0x18),
                        (s16)*(f32 *)(actor + 0x1C), 32000, 1000, 500,
                        (s32)func_15033BDC, node, (s32)actor, 0, 0);
                    return 1;
                }
                return 0;
            }
        } else if (node[1] == 0x37) {
            if (*(u16 *)(packet + 0x24) != 0) {
                func_100111C8(*(u16 *)(packet + 0x24));
                *(u16 *)(packet + 0x24) = 0;
            }
            *sound = 0;
            return 0;
        }
    }
    return 1;
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'inline-cached-expression', SELECTED.replace('    s32 cached;\n', '').replace(
        '                cached = *(s32 *)(node + 0x38);\n', '').replace('cached & 0xFFFF', '*(s32 *)(node + 0x38) & 0xFFFF')
    yield 's32-coordinate-stores', SELECTED.replace('= (s16)*(f32 *)', '= (s32)*(f32 *)')
    yield 'implicit-allocator-narrowing', SELECTED.replace('(s16)*(f32 *)(actor +', '(s32)*(f32 *)(actor +')
    yield 'combined-type-guard', SELECTED.replace(
        'if ((cached & 0xFFFF) != *(u16 *)(actor + 0x84)) {\n                    if (*(u16 *)(actor + 0x84) == 0x15F) {',
        'if (((cached & 0xFFFF) != *(u16 *)(actor + 0x84)) &&\n                    (*(u16 *)(actor + 0x84) == 0x15F)) {\n                    {')
    yield 'negative-wrong-volume', SELECTED.replace('*volume != 0', '*value != 0')
    yield 'negative-full-cached-type', SELECTED.replace('cached & 0xFFFF', 'cached')
    yield 'negative-inclusive-counter', SELECTED.replace('< 120', '<= 120')
    yield 'negative-wrong-counter-width', SELECTED.replace('*(u16 *)(state + 0x19C)', 'state[0x19C]')
    yield 'negative-wrong-effect', SELECTED.replace('func_1000FA64(0x3A1,', 'func_1000FA64(0x3A0,')
    yield 'negative-state-after-allocation', SELECTED.replace('                    *(s32 *)(node + 0x38) = 0x3A1;\n', '').replace(
        '                    return 1;', '                    *(s32 *)(node + 0x38) = 0x3A1;\n                    return 1;')
    yield 'negative-wrong-random-mask', SELECTED.replace('func_150ADA20() & 3', 'func_150ADA20() & 1')
    yield 'negative-wrong-sound-amount', SELECTED.replace('24000, 0, 0, actor', '2400, 0, 0, actor')
    yield 'negative-clear-before-stop', SELECTED.replace('                func_100111C8(*(u16 *)(packet + 0x24));',
        '                *(u16 *)(packet + 0x24) = 0;\n                func_100111C8(*(u16 *)(packet + 0x24));')
    yield 'negative-word-sound-output', SELECTED.replace('*sound = 0;', '*(s32 *)sound = 0;')
    yield 'negative-inactive-default-zero', SELECTED.replace('    return 1;\n}', '    return 0;\n}')


def owner_guards():
    return [dict(filename='generated_5D2C0', function=FUNCTION, offset='0x%X' % offset,
        expected='0x%08X' % before, replacement='0x%08X' % after,
        expected_relocations='-', replacement_relocations='-',
        note='Normalize independent effect callback type-store and zero-return schedule',
        insert_after='', insert_after_relocations='', omit='false')
        for offset, before, after in ((0x108, 0x00001025, 0xAD0F0038), (0x110, 0xAD0F0038, 0x00001025))]


def normalize(words):
    result = list(words)
    assert len(result) == WORDS and result[67] == 0x10000041
    for row in owner_guards():
        index = int(row['offset'], 0) // 4
        assert result[index] == int(row['expected'], 0), ('stale scheduling word', index)
        result[index] = int(row['replacement'], 0)
    return result


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
    script = out / 'effect-callback.ld'
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
    out = root / 'conker/build/game-node-effect-callback'
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
