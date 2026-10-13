"""Recover the indexed actor-type switch and its five-entry retail table."""
import itertools
import json
from pathlib import Path
import struct
import subprocess
import sys
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner as preprocess_owner

ENTRY, ROM, WORDS = 0x1503453C, 0x619EC, 42
FUNCTION = 'func_1503453C'
SOURCE = 'conker/src/game/generated_61490.c'
TABLE, TABLE_ROM = 0x80097D20, 0x23C7E0
ANCHOR = 'jtbl_80097D20_game'
SYMBOLS = {'D_800CC2D4': 0x800CC2D4, 'func_1503B9BC': 0x1503B9BC}
DECLARATIONS = 'extern u8 D_800CC2D4[];\nvoid func_1503B9BC(s32 index);\n'
ORIGINAL = 's32 func_1503453C() {\n    return 0;\n}'
SELECTED = '''void func_1503453C(s32 index) {
    switch (D_800CC2D4[(u32)index * 0x32C]) {
        case 0:
        case 1:
        case 2:
        case 3:
        case 4:
        case 0x80:
        case 0xB0:
            func_1503B9BC(index);
            break;
    }
}'''


def recovered_owner(source):
    if source.count(ORIGINAL) == 1:
        source = source.replace(ORIGINAL, SELECTED)
    elif source.count(SELECTED) != 1:
        raise ValueError('Expected the known dispatcher placeholder or complete body')
    if DECLARATIONS not in source:
        source = source.replace('extern u8 D_800CC2D0[];', DECLARATIONS + '\nextern u8 D_800CC2D0[];', 1)
    return source


def compile_owner(root, out, source, name):
    obj, warnings = preprocess_owner(root, out, source, name)
    result = subprocess.run([sys.executable, str(root / 'tools/asm-processor/asm_processor.py'),
        '-O2', '-g3', str((out / (name + '.c')).relative_to(root / 'conker')), '--post-process',
        str(obj.relative_to(root / 'conker')), '--assembler',
        'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
        '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=root / 'conker', capture_output=True, text=True)
    if result.returncode or result.stdout or result.stderr:
        raise ValueError(result.stdout + result.stderr)
    return obj, warnings


def candidates():
    yield 'selected', SELECTED
    yield 'signed-index', SELECTED.replace('(u32)index', 'index')
    for kind in ('s32', 'u32', 'u8'):
        yield kind + '-selector', SELECTED.replace('    switch (D_800CC2D4[(u32)index * 0x32C]) {',
            '    %s type = D_800CC2D4[(u32)index * 0x32C];\n    switch (type) {' % kind)


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
                        RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        record, _ = compiler.compile_candidate(root, out, name, body, profile)
    script = out / (name + '.ld')
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } '
        '.rodata 0x%X : SUBALIGN(4) { *(.rodata) } }\n' % (ENTRY, TABLE))
    subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', FUNCTION,
        *['--defsym=%s=0x%X' % item for item in SYMBOLS.items()], '-o', str(out / (name + '.elf')),
        str(out / (name + '.o'))], check=True, capture_output=True)
    pools = sections(out / (name + '.elf'))
    words = list(struct.unpack_from('>%dI' % record['body_words'], pools['.text'][1]))
    retail = struct.unpack_from('>%dI' % WORDS, (root / 'conker/conker.us.bin').read_bytes(), ROM)
    record['differences'] = sum(a != b for a, b in itertools.zip_longest(words, retail, fillvalue=0))
    pool = pools.get('.rodata', (TABLE, b''))[1]
    record['pool_bytes'] = len(pool)
    return record, words, pool


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-actor-type-dispatch'
    records = []
    for name, body in candidates():
        record, _, pool = compile_candidate(root, out, name, body)
        records.append(record)
        print(name, record['body_words'], hex(record['frame']), record['differences'], pool.hex(), flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
