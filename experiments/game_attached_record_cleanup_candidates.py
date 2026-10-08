"""Recover the attached-record unlinker and its live owner-slot reloads."""

import argparse
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151D77C8, 0x204C78, 26
FUNCTION = 'func_151D77C8'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_204660/func_151D77C8.s")'
DECLARATIONS = ''
SYMBOLS = {}
PROTOTYPE = 'void func_151D77C8(u8 *owner);'
OLD_PROTOTYPE = 's32 func_151D77C8();'
SELECTED = '''void func_151D77C8(u8 *owner) {
    u8 **slot = (u8 **)(owner + 0x28);
    s32 *nested;

    if (*slot != NULL) {
        nested = *(s32 **)(*slot + 0x98);
        (*slot)[0x30] = 0;
        *(u16 *)(*slot + 0x1E) &= 0xFFFD;
        *(u16 *)(*slot + 0x1E) |= 8;
        *(u16 *)(*slot + 0x1E) |= 1;
        *(u16 *)(*slot + 0x1C) = 20;
        *nested = 0;
        *slot = NULL;
    }
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'volatile-slot', SELECTED.replace('u8 **slot =', 'u8 * volatile *slot =')
    yield 'signed-flags', SELECTED.replace('(u16 *)', '(s16 *)')
    yield 'unsigned-nested', SELECTED.replace('s32 *nested', 'u32 *nested').replace('(s32 **)', '(u32 **)')
    yield 'register-slot', SELECTED.replace('u8 **slot', 'register u8 **slot')
    yield 'nested-in-block', SELECTED.replace('    s32 *nested;\n', '').replace('        nested =', '        s32 *nested =')
    yield 'no-null-spelling', SELECTED.replace('NULL', '0')
    yield 'old-style-pointer', SELECTED.replace('void func_151D77C8(u8 *owner)', 'void func_151D77C8(owner)\nu8 *owner;')
    yield 'return-slot-probe', SELECTED.replace('void func_151D77C8', 'u8 **func_151D77C8').replace('    }\n}', '    }\n    return slot;\n}')
    yield 'negative-cached-record', SELECTED.replace('    s32 *nested;', '    s32 *nested;\n    u8 *record;').replace('        nested =', '        record = *slot;\n        nested =').replace('*slot +', 'record +').replace('(*slot)[', 'record[')
    yield 'negative-combined-flags', SELECTED.replace('        *(u16 *)(*slot + 0x1E) &= 0xFFFD;\n        *(u16 *)(*slot + 0x1E) |= 8;\n        *(u16 *)(*slot + 0x1E) |= 1;', '        *(u16 *)(*slot + 0x1E) = (*(u16 *)(*slot + 0x1E) & 0xFFFD) | 9;')
    yield 'negative-keep-bit-two', SELECTED.replace('&= 0xFFFD', '&= 0xFFFF')
    yield 'negative-no-active', SELECTED.replace('        *(u16 *)(*slot + 0x1E) |= 1;\n', '')
    yield 'negative-short-timer', SELECTED.replace('= 20;', '= 19;')
    yield 'negative-late-nested', SELECTED.replace('        nested = *(s32 **)(*slot + 0x98);\n', '').replace('        *nested = 0;', '        nested = *(s32 **)(*slot + 0x98);\n        *nested = 0;')
    yield 'negative-owner-first', SELECTED.replace('        *nested = 0;\n        *slot = NULL;', '        *slot = NULL;\n        *nested = 0;')
    yield 'negative-no-nested-clear', SELECTED.replace('        *nested = 0;', '        (void)nested;')


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
    script = out / 'attached-record-cleanup.ld'
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
    out = root / 'conker/build/game-attached-record-cleanup'
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
