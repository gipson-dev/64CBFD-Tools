"""Recover the callback forwarding a record and its embedded +0x18 parameters."""

import argparse
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151D8BE0, 0x206090, 8
FUNCTION = 'func_151D8BE0'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_205C90/func_151D8BE0.s")'
DECLARATIONS = 's32 func_151D8C00();\n'
SYMBOLS = {'func_151D8C00': 0x151D8C00}
SELECTED = '''void func_151D8BE0(u8 *record) {
    func_151D8C00(record, record + 0x18);
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'explicit-discard', SELECTED.replace('    func_', '    (void)func_')
    yield 'indexed-address', SELECTED.replace('record + 0x18', '&record[0x18]')
    yield 'return-forward-control', SELECTED.replace('void func_', 's32 func_').replace('    func_', '    return func_')
    yield 'negative-wrong-offset', SELECTED.replace('record + 0x18', 'record + 0x14')
    yield 'negative-scaled-offset', SELECTED.replace('record + 0x18', '(u8 *)((s32 *)record + 0x18)')
    yield 'negative-swapped-arguments', SELECTED.replace('record, record + 0x18', 'record + 0x18, record')
    yield 'negative-shifted-base', SELECTED.replace('record, record + 0x18', 'record + 4, record + 0x18')
    yield 'negative-null-gate', SELECTED.replace('    func_', '    if (record != 0) func_')
    yield 'negative-double-call', SELECTED.replace('    func_151D8C00(record, record + 0x18);',
        '    func_151D8C00(record, record + 0x18);\n    func_151D8C00(record, record + 0x18);')
    yield 'negative-forced-zero-return', SELECTED.replace('void func_', 's32 func_').replace('\n}', '\n    return 0;\n}')


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
    script = out / 'record-callback.ld'
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
    out = root / 'conker/build/game-record-embedded-callback'
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
