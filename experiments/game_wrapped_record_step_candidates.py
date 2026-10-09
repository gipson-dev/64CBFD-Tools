"""Complete backwards-wrapped record integration with live time reloads."""

import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x15148AF4, 0x175FA4, 44
FUNCTION = 'func_15148AF4'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_175250/func_15148AF4.s")'
DECLARATIONS = '''typedef struct {
    f32 x, y, z, velocityY, reserved;
} MotionRecord15148AF4;
extern f32 D_800BE9A4;
'''
SYMBOLS = dict(D_800BE9A4=0x800BE9A4)
BASE = '''s32 func_15148AF4(u8 *actor) {
    MotionRecord15148AF4 *records = *(MotionRecord15148AF4 **)(actor + 0x94);
    u8 *payload = *(u8 **)(actor + 0x98);
    s32 index = *(s8 *)(actor + 0x2E) - 1;
    MotionRecord15148AF4 *record;

    do {
        if (index < 0) {
            index = actor[0x25] - 1;
        }
        record = records + index;
        record->velocityY -= *(f32 *)(payload + 0x10) * D_800BE9A4;
        record->x += *(f32 *)(payload + 0x04) * D_800BE9A4;
        record->y += record->velocityY * D_800BE9A4;
        record->z += *(f32 *)(payload + 0x0C) * D_800BE9A4;
    } while (index-- != *(s8 *)(actor + 0x2D));
    return 1;
}'''
SELECTED = BASE.replace('s32 index = *(s8 *)(actor + 0x2E) - 1;',
    's32 index = *(s8 *)(actor + 0x2E);').replace('    do {', '    do {\n        index--;').replace(
    'while (index-- !=', 'while (index !=')
PATCHES = ((16, 0x01C23021, 0x004E3021),)


def normalize(words):
    assert len(words) == WORDS
    result = list(words)
    for index, expected, replacement in PATCHES:
        assert result[index] == expected, (index, hex(result[index]))
        result[index] = replacement
    return result


def guard_rows():
    return [dict(filename='generated_175250', function=FUNCTION, offset='0x40',
        expected='0x01C23021', replacement='0x004E3021', expected_relocations='-', replacement_relocations='-',
        note='Normalize commutative wrapped record pointer addition', insert_after='',
        insert_after_relocations='', omit='false')]


def candidates():
    yield 'baseline', BASE
    yield 'top-decrement', SELECTED
    yield 'indexed-record', BASE.replace('record = records + index;', 'record = &records[index];')
    for kind in ('s16', 's8', 'u8', 'u32'):
        yield 'index-' + kind, BASE.replace('s32 index', kind + ' index')
    yield 'explicit-loop-decrement', BASE.replace('    } while (index-- != *(s8 *)(actor + 0x2D));',
        '        if (index == *(s8 *)(actor + 0x2D)) {\n            break;\n        }\n        index--;\n    } while (1);')
    yield 'for-loop', BASE.replace('    do {', '    for (;;) {').replace(
        '    } while (index-- != *(s8 *)(actor + 0x2D));',
        '        if (index == *(s8 *)(actor + 0x2D)) {\n            break;\n        }\n        index--;\n    }')
    declarations = ('MotionRecord15148AF4 *records = *(MotionRecord15148AF4 **)(actor + 0x94);',
        'u8 *payload = *(u8 **)(actor + 0x98);', 's32 index = *(s8 *)(actor + 0x2E) - 1;',
        'MotionRecord15148AF4 *record;')
    original = '\n'.join('    ' + d for d in declarations)
    for index, order in enumerate(itertools.permutations(declarations)):
        yield 'declaration-order-%d' % index, BASE.replace(original, '\n'.join('    ' + d for d in order))
    yield 'reverse-add', SELECTED.replace('records + index', 'index + records')
    for reverse in (False, True):
        yield 'byte-base-%d' % reverse, SELECTED.replace(
            'MotionRecord15148AF4 *records = *(MotionRecord15148AF4 **)', 'u8 *records = *(u8 **)').replace(
            'record = records + index;', 'record = (MotionRecord15148AF4 *)(%s);' %
            ('index * 20 + records' if reverse else 'records + index * 20'))


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
    script = output / 'record-step.ld'
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % ENTRY)
    subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', FUNCTION,
        *['--defsym=%s=0x%X' % item for item in SYMBOLS.items()], '-o', str(elf), str(obj)],
        check=True, capture_output=True)
    _, functions, relocations = parse_object(obj)
    meta, pools = functions[FUNCTION], sections(elf)
    words = list(struct.unpack_from('>%dI' % (meta['size'] // 4), pools['.text'][1], meta['value']))
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    assert not any(words[end:]); words = words[:end]
    retail = struct.unpack_from('>%dI' % WORDS, (root / 'conker/conker.us.bin').read_bytes(), ROM)
    frames = [(-w) & 65535 for w in words if w & 0xFFFF0000 == 0x27BD0000 and w & 0x8000]
    return dict(name=name, profile=profile, body_words=end, frame=frames[0] if frames else 0,
        differences=sum(a != b for a, b in itertools.zip_longest(words, retail, fillvalue=0)),
        relocations=relocations, diagnostics='',
        pool_bytes=sum(len(v[1]) for n, v in pools.items() if n in ('.rodata', '.data'))), words


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / 'conker/build/game-wrapped-record-step'
    records = []
    for name, body in candidates():
        meta, _ = compile_candidate(root, output, name, body)
        records.append(meta)
        print(name, meta['body_words'], meta['frame'], meta['differences'], flush=True)
    (output / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
