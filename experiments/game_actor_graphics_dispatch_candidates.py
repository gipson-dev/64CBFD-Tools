"""Complete actor graphics forwarding and callback return-source recovery."""

import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x15147C4C, 0x1750FC, 52
FUNCTION = 'func_15147C4C'
ORIGINAL = 's32 func_15147C4C() {\n    return 0;\n}'
DECLARATIONS = '''u8 *func_151462C8(u8 *, void *, u8, u8 *, u8, s16, void *, u8, s32);
void func_1516972C(u8 *);
extern u8 *(*D_8008A2A4[])(u8 *, u8 *, s16);
'''
INSERT = DECLARATIONS + '\n'
SYMBOLS = dict(func_151462C8=0x151462C8, func_1516972C=0x1516972C, D_8008A2A4=0x8008A2A4)
BASE = '''u8 *func_15147C4C(u8 *commands, u8 *actor, s16 index) {
    s32 optional;
    u8 selector;

    if (*(u16 *)(actor + 0x1E) & 0x20) {
        optional = *(s32 *)(actor + 0x28);
    } else {
        optional = 0;
    }
    commands = func_151462C8(commands, actor + 0x34, 0, NULL, 0,
        index, actor + 0x54, 2, optional);
    selector = actor[0x31];
    if (selector >= 0x13) {
        func_1516972C(actor);
        return commands;
    }
    if (selector != 0) {
        return D_8008A2A4[selector](actor, commands, index);
    }
    return commands;
}'''
SELECTED = BASE


def candidates():
    yield 'baseline', BASE
    yield 'signed-selector', BASE.replace('u8 selector;', 's8 selector;')
    yield 'word-selector', BASE.replace('u8 selector;', 's32 selector;')
    yield 'word-index', BASE.replace('s16 index)', 's32 index)')
    yield 'unsigned-index', BASE.replace('s16 index)', 'u16 index)')
    yield 'nested-else', BASE.replace('    }\n    if (selector != 0)', '    } else if (selector != 0)')


def compile_candidate(root, output, name, body=SELECTED, profile='o2g3'):
    output.mkdir(exist_ok=True)
    source, obj, elf = (output / (name + suffix) for suffix in ('.c', '.o', '.elf'))
    source.write_text('#include <ultra64.h>\n' + DECLARATIONS + body + '\n')
    result = subprocess.run(['ido/ido5.3_recomp/cc', '-c', '-32', '-G', '0', '-Xfullwarn', '-Xcpluscomm',
        '-signed', '-nostdinc', '-non_shared', '-Wab,-r4300_mul', '-mips2', '-o32',
        '-I', 'conker/include', '-I', 'conker/include/2.0L', '-I', 'conker/include/2.0L/PR',
        '-I', 'conker/include/libc', '-D_LANGUAGE_C', '-D_FINALROM', '-DF3DEX_GBI_2',
        '-D_MIPS_SZLONG=32', *PROFILES[profile], '-o', str(obj.relative_to(root)),
        str(source.relative_to(root))], cwd=root, capture_output=True, text=True)
    if result.returncode or result.stdout or result.stderr:
        raise ValueError(result.stdout + result.stderr)
    script = output / 'dispatch.ld'
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
        relocations=relocations, diagnostics='',
        pool_bytes=sum(len(v[1]) for n, v in pools.items() if n in ('.rodata', '.data'))), words


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / 'conker/build/game-actor-graphics-dispatch'
    records = []
    for name, body in candidates():
        meta, _ = compile_candidate(root, output, name, body)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (output / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
