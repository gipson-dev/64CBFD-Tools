"""Complete signed-count gate and live forward record-phase shaping."""

import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x15148DE0, 0x176290, 70
FUNCTION = 'func_15148DE0'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_175250/func_15148DE0.s")'
DECLARATIONS = '''typedef struct {
    u32 words[4];
    u16 phase, reserved;
} PhaseRecord15148DE0;
'''
BASE = '''s32 func_15148DE0(u8 *actor) {
    u8 *payload;
    PhaseRecord15148DE0 *records;
    s32 index;
    u16 step;
    u16 phase;

    if (*(s8 *)(actor + 0x2C) < 3) {
        return 0;
    }
    (*(s8 *)(actor + 0x2C))--;
    payload = *(u8 **)(actor + 0x98);
    records = *(PhaseRecord15148DE0 **)(actor + 0x94);
    step = 0x1000 / *(s8 *)(actor + 0x2C);
    index = *(s8 *)(actor + 0x2D);
    phase = (payload[0x18] & 0x20) ? 0x1000 : 0;
    (*(s8 *)(actor + 0x2E))--;
    if (*(s8 *)(actor + 0x2E) < 0) {
        actor[0x2E] = actor[0x25] - 1;
    }
    while (index != *(s8 *)(actor + 0x2E)) {
        records[index].phase = phase;
        if (payload[0x18] & 0x20) {
            phase -= step;
        } else {
            phase += step;
        }
        if (++index == actor[0x25]) {
            index = 0;
        }
    }
    return 1;
}'''
POSITIVE = BASE.replace('    if (*(s8 *)(actor + 0x2C) < 3) {\n        return 0;\n    }',
    '    if (*(s8 *)(actor + 0x2C) >= 3) {').replace('    return 1;\n}', '    return 1;\n    }\n    return 0;\n}')
SELECTED = '''s32 func_15148DE0(u8 *actor) {
    u8 *payload;
    PhaseRecord15148DE0 *records;
    s32 index;
    u16 step;
    u16 phase;

    if (*(s8 *)(actor + 0x2C) >= 3) {
        (*(s8 *)(actor + 0x2C))--;
        records = *(PhaseRecord15148DE0 **)(actor + 0x94);
        payload = *(u8 **)(actor + 0x98);
        index = *(s8 *)(actor + 0x2D);
        step = 0x1000 / *(s8 *)(actor + 0x2C);
        phase = (payload[0x18] & 0x20) ? 0x1000 : 0;
        (*(s8 *)(actor + 0x2E))--;
        if (*(s8 *)(actor + 0x2E) < 0) {
            actor[0x2E] = actor[0x25] - 1;
        }
        while (index != *(s8 *)(actor + 0x2E)) {
            records[index].phase = phase;
            if (payload[0x18] & 0x20) {
                phase -= step;
            } else {
                phase += step;
            }
            if (++index == actor[0x25]) {
                index = 0;
            }
        }
        return 1;
    }
    return 0;
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'baseline', BASE
    yield 'positive-gate', POSITIVE
    yield 'pointer-add', BASE.replace('records[index].phase', '(records + index)->phase')
    for kind in ('u32', 's32'):
        yield 'step-' + kind, BASE.replace('u16 step;', kind + ' step;')
        yield 'phase-' + kind, BASE.replace('u16 phase;', kind + ' phase;')
    yield 'phase-if', BASE.replace('    phase = (payload[0x18] & 0x20) ? 0x1000 : 0;',
        '    if (payload[0x18] & 0x20) {\n        phase = 0x1000;\n    } else {\n        phase = 0;\n    }')
    yield 'byte-records', BASE.replace('PhaseRecord15148DE0 *records', 'u8 *records').replace(
        '*(PhaseRecord15148DE0 **)', '*(u8 **)').replace('records[index].phase', '*(u16 *)(records + index * 20 + 0x10)')
    declarations = ('u8 *payload;', 'PhaseRecord15148DE0 *records;', 's32 index;', 'u16 step;', 'u16 phase;')
    original = '\n'.join('    ' + d for d in declarations)
    for index, order in enumerate(itertools.islice(itertools.permutations(declarations), 12)):
        yield 'declaration-order-%d' % index, POSITIVE.replace(original, '\n'.join('    ' + d for d in order))
    setup = ('payload = *(u8 **)(actor + 0x98);', 'records = *(PhaseRecord15148DE0 **)(actor + 0x94);',
        'step = 0x1000 / *(s8 *)(actor + 0x2C);', 'index = *(s8 *)(actor + 0x2D);')
    original = '\n'.join('    ' + d for d in setup)
    for index, order in enumerate(itertools.permutations(setup)):
        yield 'setup-order-%d' % index, POSITIVE.replace(original, '\n'.join('    ' + d for d in order))


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
    script = output / 'record-phase.ld'
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % ENTRY)
    subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', FUNCTION,
        '-o', str(elf), str(obj)], check=True, capture_output=True)
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
    output = root / 'conker/build/game-record-phase-shaping'
    records = []
    for name, body in candidates():
        meta, _ = compile_candidate(root, output, name, body)
        records.append(meta)
        print(name, meta['body_words'], meta['frame'], meta['differences'], flush=True)
    (output / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
