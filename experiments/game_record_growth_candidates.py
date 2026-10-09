"""Complete live record integration, insertion and phase-shaping callback."""

import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151488C4, 0x175D74, 140
FUNCTION = 'func_151488C4'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_175250/func_151488C4.s")'
DECLARATIONS = '''typedef struct {
    f32 x, y, z, velocityY;
    u16 phase, reserved;
} GrowthRecord151488C4;
'''
BASE = '''s32 func_151488C4(u8 *actor) {
    s32 index = *(s8 *)(actor + 0x2D);
    s32 head = *(s8 *)(actor + 0x2E);
    GrowthRecord151488C4 *records = *(GrowthRecord151488C4 **)(actor + 0x94);
    u8 *payload = *(u8 **)(actor + 0x98);
    GrowthRecord151488C4 *record;
    s32 active;
    u16 step;
    u16 phase;
    s32 count;

    while (index != head) {
        record = records + index;
        index++;
        record->velocityY -= *(f32 *)(payload + 0x10) * D_800BE9A4;
        record->x += *(f32 *)(payload + 0x04) * D_800BE9A4;
        record->y += record->velocityY * D_800BE9A4;
        record->z += *(f32 *)(payload + 0x0C) * D_800BE9A4;
        if (index == actor[0x25]) {
            index = 0;
        }
        head = *(s8 *)(actor + 0x2E);
    }
    active = *(s8 *)(actor + 0x2C);
    if (active < actor[0x25] - 1) {
        phase = (payload[0x18] & 0x20) ? 0x1000 : 0;
        /* Retail leaves the stack step untouched when active is zero. */
        if (active != 0) {
            step = 0x1000 / active;
        }
        actor[0x2C] = active + 1;
        *(ActorPosition15147EB8 *)(records + head) = *(ActorPosition15147EB8 *)(actor + 0x10);
        records[*(s8 *)(actor + 0x2E)].velocityY = *(f32 *)(payload + 0x08);
        count = actor[0x25];
        (*(s8 *)(actor + 0x2E))++;
        if (*(s8 *)(actor + 0x2E) == count) {
            actor[0x2E] = 0;
        }
        index = *(s8 *)(actor + 0x2D);
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
    } else {
        payload[0x20] = (payload[0x18] & 0x17) ? 3 : 2;
    }
    return 1;
}'''

SELECTED = '''s32 func_151488C4(u8 *actor) {
    s32 index;
    u8 *payload;
    GrowthRecord151488C4 *records;
    u16 phase;
    u16 step;
    s32 active;

    records = *(GrowthRecord151488C4 **)(actor + 0x94);
    payload = *(u8 **)(actor + 0x98);
    index = *(s8 *)(actor + 0x2D);
    while (index != *(s8 *)(actor + 0x2E)) {
        records[index].velocityY -= *(f32 *)(payload + 0x10) * D_800BE9A4;
        records[index].x += *(f32 *)(payload + 0x04) * D_800BE9A4;
        records[index].y += records[index].velocityY * D_800BE9A4;
        records[index].z += *(f32 *)(payload + 0x0C) * D_800BE9A4;
        if (++index == actor[0x25]) {
            index = 0;
        }
    }
    active = *(s8 *)(actor + 0x2C);
    if (active < actor[0x25] - 1) {
        phase = (payload[0x18] & 0x20) ? 0x1000 : 0;
        /* Retail leaves the stack step untouched when active is zero. */
        if (active != 0) {
            step = 0x1000 / active;
        }
        actor[0x2C] = active + 1;
        *(ActorPosition15147EB8 *)(records + *(s8 *)(actor + 0x2E)) = *(ActorPosition15147EB8 *)(actor + 0x10);
        records[*(s8 *)(actor + 0x2E)].velocityY = *(f32 *)(payload + 0x08);
        if (actor[0x25] == ++(*(s8 *)(actor + 0x2E))) {
            actor[0x2E] = 0;
        }
        index = *(s8 *)(actor + 0x2D);
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
    } else {
        if (payload[0x18] & 0x17) {
            payload[0x20] = 3;
        } else {
            payload[0x20] = 2;
        }
    }
    return 1;
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'late-index', SELECTED.replace('        index++;\n', '').replace(
        '        if (index == actor[0x25])', '        if (++index == actor[0x25])')
    yield 'phase-if', SELECTED.replace('        phase = (payload[0x18] & 0x20) ? 0x1000 : 0;',
        '        phase = 0;\n        if (payload[0x18] & 0x20) {\n            phase = 0x1000;\n        }')
    yield 'selector-if', SELECTED.replace('        payload[0x20] = (payload[0x18] & 0x17) ? 3 : 2;',
        '        if (payload[0x18] & 0x17) {\n            payload[0x20] = 3;\n        } else {\n            payload[0x20] = 2;\n        }')
    opening = BASE[BASE.index('    s32 index'):BASE.index('    while (index')]
    declarations = ('GrowthRecord151488C4 *records;', 'u8 *payload;', 's32 index;', 's32 head;')
    setup = '''    index = *(s8 *)(actor + 0x2D);
    head = *(s8 *)(actor + 0x2E);
    records = *(GrowthRecord151488C4 **)(actor + 0x94);
    payload = *(u8 **)(actor + 0x98);
'''
    for number, order in enumerate(itertools.permutations(declarations)):
        prelude = '\n'.join('    ' + item for item in order)
        prelude += '\n    u16 phase;\n    u16 step;\n    s32 active;\n    GrowthRecord151488C4 *record;\n\n' + setup
        body = BASE.replace(opening, prelude).replace('        count = actor[0x25];\n', '').replace(
            '        (*(s8 *)(actor + 0x2E))++;\n        if (*(s8 *)(actor + 0x2E) == count)',
            '        if (++(*(s8 *)(actor + 0x2E)) == actor[0x25])')
        yield 'decl-%d' % number, body
    body = body.replace('u16 phase;\n    u16 step;', 'u16 step;\n    u16 phase;')
    assignments = setup.strip().splitlines()
    assignments = [line.strip() for line in assignments]
    for number, order in enumerate(itertools.permutations(assignments)):
        yield 'setup-%d' % number, body.replace(setup, '\n'.join('    ' + item for item in order) + '\n')
    pointer_first = '\n'.join('    ' + assignments[i] for i in (2, 3, 0, 1)) + '\n'
    body = body.replace(setup, pointer_first)
    yield 'indexed', body.replace('    GrowthRecord151488C4 *record;\n', '').replace(
        '        record = records + index;\n        index++;\n', '').replace('record->', 'records[index].').replace(
        '        if (index == actor[0x25])', '        if (++index == actor[0x25])')
    yield 'byte-base', body.replace('GrowthRecord151488C4 *records;', 'u8 *records;').replace(
        '*(GrowthRecord151488C4 **)', '*(u8 **)').replace('record = records + index;',
        'record = (GrowthRecord151488C4 *)(records + index * 20);').replace(
        '(ActorPosition15147EB8 *)(records + head)', '(ActorPosition15147EB8 *)(records + head * 20)').replace(
        'records[*(s8 *)(actor + 0x2E)].velocityY', '*(f32 *)(records + *(s8 *)(actor + 0x2E) * 20 + 0x0C)').replace(
        'records[index].phase', '*(u16 *)(records + index * 20 + 0x10)')
    no_head = body.replace('    s32 head;\n', '').replace('    head = *(s8 *)(actor + 0x2E);\n', '').replace(
        'while (index != head)', 'while (index != *(s8 *)(actor + 0x2E))').replace(
        'records + head', 'records + *(s8 *)(actor + 0x2E)')
    for indexed, phase_kind, repeat_active in itertools.product((False, True), ('u16', 'u32'), (False, True)):
        trial = no_head.replace('u16 phase;', phase_kind + ' phase;')
        if indexed:
            trial = trial.replace('    GrowthRecord151488C4 *record;\n', '').replace(
                '        record = records + index;\n        index++;\n', '').replace('record->', 'records[index].').replace(
                '        if (index == actor[0x25])', '        if (++index == actor[0x25])')
        if repeat_active:
            trial = trial.replace('    s32 active;\n', '').replace('    active = *(s8 *)(actor + 0x2C);\n', '').replace(
                'active', '(*(s8 *)(actor + 0x2C))')
        yield 'compact-%d-%s-%d' % (indexed, phase_kind, repeat_active), trial
        if indexed and phase_kind == 'u16' and not repeat_active:
            fitted = trial.replace('u16 step;\n    u16 phase;', 'u16 phase;\n    u16 step;').replace(
                '++(*(s8 *)(actor + 0x2E)) == actor[0x25]', 'actor[0x25] == ++(*(s8 *)(actor + 0x2E))').replace(
                '        payload[0x20] = (payload[0x18] & 0x17) ? 3 : 2;',
                '        if (payload[0x18] & 0x17) {\n            payload[0x20] = 3;\n        } else {\n            payload[0x20] = 2;\n        }')
            yield 'fitted', fitted


def compile_candidate(root, output, name, body=SELECTED, profile='o2g3'):
    output.mkdir(exist_ok=True)
    source, obj, elf = (output / (name + suffix) for suffix in ('.c', '.o', '.elf'))
    source.write_text('#include <ultra64.h>\nextern f32 D_800BE9A4;\n'
        'typedef struct { u32 words[3]; } ActorPosition15147EB8;\n' + DECLARATIONS + body + '\n')
    result = subprocess.run(['ido/ido5.3_recomp/cc', '-c', '-32', '-G', '0', '-Xfullwarn', '-Xcpluscomm',
        '-signed', '-nostdinc', '-non_shared', '-Wab,-r4300_mul', '-mips2', '-o32',
        '-I', 'conker/include', '-I', 'conker/include/2.0L', '-I', 'conker/include/2.0L/PR',
        '-I', 'conker/include/libc', '-D_LANGUAGE_C', '-D_FINALROM', '-DF3DEX_GBI_2',
        '-D_MIPS_SZLONG=32', *PROFILES[profile], '-o', str(obj.relative_to(root)),
        str(source.relative_to(root))], cwd=root, capture_output=True, text=True)
    if result.returncode or result.stdout or result.stderr:
        raise ValueError(result.stdout + result.stderr)
    script = output / 'record-growth.ld'
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % ENTRY)
    subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', FUNCTION,
        '--defsym', 'D_800BE9A4=0x800BE9A4', '-o', str(elf), str(obj)], check=True, capture_output=True)
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
    output = root / 'conker/build/game-record-growth'
    receipts = []
    for name, body in candidates():
        meta, _ = compile_candidate(root, output, name, body)
        receipts.append(meta)
        print(name, meta['body_words'], meta['frame'], meta['differences'], flush=True)
    (output / 'measurements.json').write_text(json.dumps(receipts, indent=2) + '\n')


if __name__ == '__main__':
    main()
