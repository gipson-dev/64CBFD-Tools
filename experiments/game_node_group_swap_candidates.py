"""Recover the full-word key comparisons and byte writes of the node group swap."""

import argparse
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x15033EC4, 0x61374, 18
FUNCTION = 'func_15033EC4'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_5D2C0/func_15033EC4.s")'
DECLARATIONS = 'extern u8 *D_800C3EE0;\n'
SYMBOLS = {'D_800C3EE0': 0x800C3EE0}
FIRST = '''void func_15033EC4(s32 first, s32 second) {
    u8 *node;
    u8 *next;
    s32 group;

    node = D_800C3EE0;
    while (node != 0) {
        group = node[0];
        next = *(u8 **)(node + 0x54);
        if (first == group) {
            node[0] = second;
        } else if (second == group) {
            node[0] = first;
        }
        node = next;
    }
}'''
SELECTED = '''void func_15033EC4(s32 first, s32 second) {
    u8 *node;
    u8 *next;
    s32 group;
    s32 firstKey;

    firstKey = first;
    node = D_800C3EE0;
    while (node != 0) {
        next = *(u8 **)(node + 0x54);
        group = node[0];
        if (firstKey == group) {
            node[0] = second;
        } else if (second == group) {
            node[0] = firstKey;
        }
        node = next;
    }
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'initial-group-first', FIRST
    yield 'initial-next-first', FIRST.replace('        group = node[0];\n        next = *(u8 **)(node + 0x54);',
        '        next = *(u8 **)(node + 0x54);\n        group = node[0];')
    yield 'byte-group-local', SELECTED.replace('s32 group;', 'u8 group;')
    yield 'for-cursor', SELECTED.replace('    node = D_800C3EE0;\n    while (node != 0)',
        '    for (node = D_800C3EE0; node != 0; node = next)').replace('        node = next;\n', '')
    yield 'explicit-store-narrowing', SELECTED.replace('node[0] = second;', 'node[0] = (u8)second;').replace(
        'node[0] = firstKey;', 'node[0] = (u8)firstKey;')
    yield 'next-after-store-control', SELECTED.replace('        next = *(u8 **)(node + 0x54);\n', '').replace(
        '        node = next;', '        node = *(u8 **)(node + 0x54);')
    yield 'negative-narrowed-keys', SELECTED.replace('s32 first, s32 second', 'u8 first, u8 second')
    yield 'negative-independent-if', SELECTED.replace('} else if (second == group)', '}\n        if (second == group)')
    yield 'negative-signed-group', SELECTED.replace('group = node[0];', 'group = *(s8 *)node;')
    yield 'negative-wrong-group-offset', SELECTED.replace('node[0]', 'node[1]')
    yield 'negative-wrong-next-offset', SELECTED.replace('node + 0x54', 'node + 0x50')
    yield 'negative-halfword-stores', SELECTED.replace('node[0] = second;', '*(u16 *)node = second;').replace(
        'node[0] = firstKey;', '*(u16 *)node = firstKey;')
    yield 'negative-reread-second-test', SELECTED.replace('} else if (second == group)', '}\n        if (second == node[0])')


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
    script = out / 'group-swap.ld'
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
    out = root / 'conker/build/game-node-group-swap'
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
