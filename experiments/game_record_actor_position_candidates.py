"""Recover the complete actor-backed record position callback."""

import argparse
import hashlib
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151D75C4, 0x204A74, 88
FUNCTION = 'func_151D75C4'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_204660/func_151D75C4.s")'
DECLARATIONS = '''extern f32 D_800AB280[][3];
extern u8 D_800AB2D4[];
extern s32 (*D_8008FCA8[])(u8 *);
void func_15143134(f32 *, f32 *, u8 *);
'''
SYMBOLS = dict(D_800AB280=0x800AB280, D_800AB2D4=0x800AB2D4,
    D_8008FCA8=0x8008FCA8, func_15143134=0x15143134)
BASE = '''s32 func_151D75C4(u8 *owner) {
    u8 *actor;
    u8 *binding;
    u8 *record;
    u8 *matrices;
    u8 *secondary;
    s32 index;

    actor = *(u8 **)(owner + 0x40);
    binding = owner + 0x40;
    if (!*(s32 *)actor || binding[4] != actor[0x3B]) {
        return 0;
    }
    matrices = *(u8 **)(actor + 0x1D4);
    record = owner + 0x28;
    if (matrices == NULL) {
        record[5] &= ~1;
        return 1;
    }
    secondary = *(u8 **)(actor + 0x31C);
    if (secondary != NULL && secondary[0x197] && *(u8 **)(actor + 0x318) != NULL) {
        record = owner + 0x28;
        record[5] &= ~1;
        return 1;
    }
    if (actor[7] != 0xFF) {
        record = owner + 0x28;
        record[5] &= ~1;
        return 1;
    }
    index = binding[5];
    record = owner + 0x28;
    func_15143134(D_800AB280[index], (f32 *)(record + 8),
        matrices + D_800AB2D4[index] * 0x40);
    record[5] |= 1;
    index = *(s8 *)(binding + 6);
    if (index != -1) {
        return D_8008FCA8[index](owner);
    }
    return 1;
}'''


SHARED = BASE.replace('        record = owner + 0x28;\n', '').replace(
    '    index = binding[5];\n    record = owner + 0x28;', '    index = binding[5];')
SELECTED = SHARED


def normalize(words):
    if len(words) != WORDS:
        raise ValueError('wrong complete actor-position extent')
    relocated = (0xA0, 0xA8, 0xC8, 0xD4, 0xFC, 0x118, 0x134)
    masked = [word & (~(0x3FFFFFF if i * 4 == 0xFC else 0xFFFF) & 0xFFFFFFFF)
        if i * 4 in relocated else word for i, word in enumerate(words)]
    if hashlib.sha256(struct.pack('>88I', *masked)).hexdigest() != '0ea420bbf1dcdd9d19793777724c0051565686c7d51f6d3c7f12dae6c8e8e844':
        raise ValueError('stale complete actor-position source')
    expected = {0: 0x27BDFFC8, 0xF4: 0xAFA30018, 0x100: 0xAFA70038,
        0x104: 0x8FA30018, 0x10C: 0x8FA70038, 0x154: 0x27BD0038}
    if any(words[o // 4] != w for o, w in expected.items()):
        raise ValueError('stale actor-position frame mapping')
    # Map the owned frame only: record 0x18 -> 0x20, incoming home 0x38 -> 0x30.
    result = list(words)
    for offset, value in expected.items():
        change = 8 if offset in (0, 0xF4, 0x104) else -8
        result[offset // 4] = (value & 0xFFFF0000) | ((value + change) & 65535)
    return result


def owner_guards(words):
    result = normalize(words)
    return [dict(filename='generated_204660', function=FUNCTION, offset='0x%X' % (i * 4),
        expected='0x%08X' % a, replacement='0x%08X' % b,
        expected_relocations='-', replacement_relocations='-',
        note='Normalize closed actor position owned frame and pointer home mapping',
        insert_after='', insert_after_relocations='', omit='false')
        for i, (a, b) in enumerate(zip(words, result)) if a != b]


def candidates():
    yield 'selected', SELECTED
    yield 'split-active-gates', BASE.replace(
        'if (!*(s32 *)actor || binding[4] != actor[0x3B]) {',
        'if (!*(s32 *)actor) { return 0; }\n    if (binding[4] != actor[0x3B]) {')
    yield 'direct-owner', BASE.replace('    binding = owner + 0x40;\n', '').replace(
        'binding[4]', 'owner[0x44]').replace('binding[5]', 'owner[0x45]').replace(
        '(binding + 6)', '(owner + 0x46)')
    yield 'unsigned-local-index', BASE.replace('s32 index;', 'u8 index;').replace(
        'if (index != -1)', 'if ((s8)index != -1)').replace('D_8008FCA8[index]', 'D_8008FCA8[(s8)index]')
    yield 'volatile-owner', SELECTED.replace('u8 *owner)', 'u8 * volatile owner)')
    yield 'shared-record', SHARED
    yield 'shared-byte-index', SHARED.replace('s32 index;', 'u8 index;').replace(
        'if (index != -1)', 'if ((s8)index != -1)').replace('D_8008FCA8[index]', 'D_8008FCA8[(s8)index]')
    yield 'shared-separate-indices', SHARED.replace('s32 index;', 'u8 index;\n    s8 callback;').replace(
        'index = *(s8 *)(binding + 6);', 'callback = *(s8 *)(binding + 6);').replace(
        'if (index != -1)', 'if (callback != -1)').replace('D_8008FCA8[index]', 'D_8008FCA8[callback]')
    declarations = ('u8 *binding;', 'u8 *record;', 'u8 *secondary;', 's32 index;')
    old = '\n'.join('    ' + d for d in ('u8 *actor;', 'u8 *binding;', 'u8 *record;',
        'u8 *matrices;', 'u8 *secondary;', 's32 index;'))
    for order in itertools.permutations(range(4)):
        yield 'locals-' + ''.join(map(str, order)), SHARED.replace(old,
            '    u8 *actor;\n    u8 *matrices;\n' + '\n'.join('    ' + declarations[i] for i in order))
    yield 'reuse-secondary', BASE.replace('    u8 *secondary;\n', '').replace(
        'secondary =', 'record =').replace('secondary !=', 'record !=').replace('secondary[', 'record[')
    yield 'negative-signed-joint', SELECTED.replace('index = binding[5]', 'index = *(s8 *)(binding + 5)')
    yield 'negative-unsigned-callback', SELECTED.replace('index = *(s8 *)(binding + 6)', 'index = binding[6]').replace(
        'index != -1', 'index != 255')
    yield 'negative-dead-flag', SELECTED.replace('record[5] |= 1', 'record[5] = 1')
    yield 'negative-fixed-return', SELECTED.replace('return D_8008FCA8[index](owner);',
        'D_8008FCA8[index](owner);\n        return 1;')
    yield 'negative-early-secondary', SELECTED.replace('    index = binding[5];',
        '    secondary = (u8 *)(s32)*(s8 *)(binding + 6);\n    index = binding[5];').replace(
        'index = *(s8 *)(binding + 6);', 'index = (s32)secondary;')


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
    script = out / 'actor-position.ld'
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
        differences=sum(a != b for a, b in itertools.zip_longest(words, retail, fillvalue=0)),
        diagnostics='', relocations=relocations,
        pool_bytes=sum(len(v[1]) for n, v in pools.items() if n in ('.rodata', '.data'))), words


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-record-actor-position'
    records = []
    for name, body in candidates():
        for profile in PROFILES if args.profiles else ('o2g3',):
            record, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(record)
            print(record['name'], record['body_words'], hex(record['frame']), record['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
