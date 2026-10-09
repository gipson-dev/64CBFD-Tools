"""Fit the complete signed-halfword timer and mixed-ABI random effect callback."""

import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151D9EB0, 0x207360, 68
FUNCTION = 'func_151D9EB0'
ORIGINAL = 's32 func_151D9EB0() {\n    return 0;\n}'
OLD_DECLARATION = 's32 func_151D9EB0();'
DECLARATION = 'void func_151D9EB0(u8 *owner);'
OLD_EFFECT = ('s32 func_151D9014(' + ', '.join('s32 arg%d' % i for i in range(16)) + ');')
EFFECT = '''void *func_151D9014(void *, f32 *, u8, f32, s16, u8, f32, u8,
    f32, f32, u8, s32, u8, u8, u8, s32);'''
DECLARATIONS = '''extern s32 D_800BE9E4;
extern f32 D_800AB464, D_800AB468, D_800A5480;
f32 func_150ADA68(void);
s32 func_150ADA20(void);
''' + EFFECT + '\n'
RECORD = '''typedef struct {
    s16 timer;
    u16 padding;
    f32 scale;
    f32 position[3];
    u8 kind, mode, selector, tail;
} RandomEffectTimerRecord;
'''
SYMBOLS = dict(D_800BE9E4=0x800BE9E4, D_800AB464=0x800AB464, D_800AB468=0x800AB468,
    D_800A5480=0x800A5480, func_150ADA68=0x150ADA68, func_150ADA20=0x150ADA20,
    func_151D9014=0x151D9014)
BASE = '''void func_151D9EB0(u8 *owner) {
    u8 *record;
    f32 random;
    u32 value;

    *(s16 *)(owner + 0x28) -= (u32)D_800BE9E4;
    if (*(s16 *)(owner + 0x28) < 0) {
        random = func_150ADA68();
        value = func_150ADA20();
        record = owner + 0x28;
        func_151D9014(record + 8, &D_800A5480, record[0x16],
            random * D_800AB464 + D_800AB468, value % 41U + 35,
            record[0x14], *(f32 *)(record + 4), 0, 1.0f, 1.0f,
            record[0x15], 0, 1, 0, owner[0xC], owner[1]);
        *(s16 *)record = func_150ADA20() % 111U + 30;
    }
}'''
EARLY = BASE.replace('    *(s16 *)(owner', '    record = owner + 0x28;\n    *(s16 *)(owner', 1).replace(
    '        record = owner + 0x28;\n', '')
SELECTED = EARLY.replace('    f32 random;\n    u32 value;', '    u32 value;\n    f32 random;')
TYPED = BASE.replace('u8 *record;', 'RandomEffectTimerRecord *record;').replace(
    'record = owner + 0x28;', 'record = (RandomEffectTimerRecord *)(owner + 0x28);').replace(
    'record + 8,', 'record->position,').replace('record[0x16]', 'record->selector').replace(
    'record[0x14]', 'record->kind').replace('*(f32 *)(record + 4)', 'record->scale').replace(
    'record[0x15]', 'record->mode').replace('*(s16 *)record', 'record->timer')


def candidates():
    yield 'selected', SELECTED
    yield 'baseline', BASE
    for declarations in itertools.permutations(('u8 *record;', 'f32 random;', 'u32 value;')):
        body = BASE.replace('    u8 *record;\n    f32 random;\n    u32 value;',
            '\n'.join('    ' + d for d in declarations))
        for volatile in (False, True):
            if volatile:
                body = body.replace('*(s16 *)(owner + 0x28)', '*(volatile s16 *)(owner + 0x28)')
            yield '-'.join(d.split()[0] for d in declarations) + '-v%d' % volatile, body
    for declarations in itertools.permutations(('u8 *record;', 'f32 random;', 'u32 value;')):
        yield 'early-' + '-'.join(d.split()[0] for d in declarations), EARLY.replace(
            '    u8 *record;\n    f32 random;\n    u32 value;', '\n'.join('    ' + d for d in declarations))
    yield 'typed', TYPED
    yield 'record-volatile-pointer', BASE.replace('u8 *record;', 'u8 * volatile record;')
    yield 'typed-volatile-pointer', TYPED.replace('RandomEffectTimerRecord *record;', 'RandomEffectTimerRecord * volatile record;')
    yield 'typed-volatile-target', TYPED.replace('RandomEffectTimerRecord *record;', 'volatile RandomEffectTimerRecord *record;').replace(
        'record->position,', '(void *)record->position,')
    yield 'negative-zero-step', BASE.replace(' -= (u32)D_800BE9E4', ' -= 0')
    yield 'negative-nonnegative-gate', BASE.replace(' < 0)', ' <= 0)')
    yield 'negative-short-random-range', BASE.replace('% 41U', '% 40U')
    yield 'negative-fixed-reset', BASE.replace('func_150ADA20() % 111U + 30', '30')
    yield 'negative-wrong-float', BASE.replace('random * D_800AB464 + D_800AB468', 'random + D_800AB468')


def compile_candidate(root, output, name, body=SELECTED, profile='o2g3'):
    output.mkdir(exist_ok=True)
    source, obj, elf = (output / (name + suffix) for suffix in ('.c', '.o', '.elf'))
    source.write_text('#include <ultra64.h>\n' + RECORD + DECLARATIONS + body + '\n')
    result = subprocess.run(['ido/ido5.3_recomp/cc', '-c', '-32', '-G', '0', '-Xfullwarn', '-Xcpluscomm',
        '-signed', '-nostdinc', '-non_shared', '-Wab,-r4300_mul', '-mips2', '-o32',
        '-I', 'conker/include', '-I', 'conker/include/2.0L', '-I', 'conker/include/2.0L/PR',
        '-I', 'conker/include/libc', '-D_LANGUAGE_C', '-D_FINALROM', '-DF3DEX_GBI_2',
        '-D_MIPS_SZLONG=32', *PROFILES[profile], '-o', str(obj.relative_to(root)),
        str(source.relative_to(root))], cwd=root, capture_output=True, text=True)
    if result.returncode or result.stdout or result.stderr:
        raise ValueError(result.stdout + result.stderr)
    script = output / 'timer.ld'
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
    output = root / 'conker/build/game-random-effect-timer'
    records = []
    for name, body in candidates():
        meta, _ = compile_candidate(root, output, name, body)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (output / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
