"""Recover the mixed-ABI, alias-sensitive vertical velocity integrator."""

import argparse
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151D8718, 0x205BC8, 19
FUNCTION = 'func_151D8718'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_204660/func_151D8718.s")'
DECLARATIONS = 'extern f32 D_800AB2EC;\nextern f32 D_800AB2F0;\n'
SYMBOLS = {'D_800AB2EC': 0x800AB2EC, 'D_800AB2F0': 0x800AB2F0}
SELECTED = '''void func_151D8718(f32 *position, f32 *velocity, f32 delta) {
    f32 oldVelocity = *velocity;

    *velocity = oldVelocity + D_800AB2EC * delta;
    position[1] += oldVelocity * delta + D_800AB2F0 * (delta * delta);
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'assigned', SELECTED.replace('f32 oldVelocity = *velocity;', 'f32 oldVelocity;\n    oldVelocity = *velocity;')
    yield 'register', SELECTED.replace('f32 oldVelocity', 'register f32 oldVelocity')
    yield 'product-first', SELECTED.replace('oldVelocity + D_800AB2EC * delta', 'D_800AB2EC * delta + oldVelocity')
    yield 'indexed-velocity', SELECTED.replace('= *velocity', '= velocity[0]').replace('    *velocity =', '    velocity[0] =')
    yield 'pointer-position', SELECTED.replace('position[1]', '*(position + 1)')
    yield 'square-local', SELECTED.replace('    f32 oldVelocity', '    f32 square = delta * delta;\n    f32 oldVelocity').replace('(delta * delta)', 'square')
    yield 'step-local', SELECTED.replace('    f32 oldVelocity', '    f32 step;\n    f32 oldVelocity').replace('    *velocity =', '    step = D_800AB2EC * delta;\n    *velocity =').replace('oldVelocity + D_800AB2EC * delta', 'oldVelocity + step')
    yield 'value-copy', SELECTED.replace('    *velocity = oldVelocity + D_800AB2EC * delta;', '    f32 value = oldVelocity + D_800AB2EC * delta;\n    *velocity = value;')
    yield 'square-left', SELECTED.replace('D_800AB2F0 * (delta * delta)', '(delta * delta) * D_800AB2F0')
    yield 'velocity-multiply-left', SELECTED.replace('oldVelocity * delta', 'delta * oldVelocity')
    yield 'negative-position-expanded', SELECTED.replace('position[1] +=', 'position[1] = position[1] +')
    yield 'old-style', SELECTED.replace('void func_151D8718(f32 *position, f32 *velocity, f32 delta)', 'void func_151D8718(position, velocity, delta)\nf32 *position;\nf32 *velocity;\nf32 delta;')
    yield 'negative-updated-velocity', SELECTED.replace('oldVelocity * delta', '*velocity * delta')
    yield 'negative-no-square', SELECTED.replace('(delta * delta)', 'delta')
    yield 'negative-position-zero', SELECTED.replace('position[1]', 'position[0]')
    yield 'negative-half-first', SELECTED.replace('D_800AB2F0 * (delta * delta)', '(D_800AB2F0 * delta) * delta')
    yield 'negative-position-first', SELECTED.replace('    *velocity = oldVelocity + D_800AB2EC * delta;\n', '').replace('    position[1] += oldVelocity * delta + D_800AB2F0 * (delta * delta);', '    position[1] += oldVelocity * delta + D_800AB2F0 * (delta * delta);\n    *velocity = oldVelocity + D_800AB2EC * delta;')
    yield 'negative-cached-position', SELECTED.replace('    f32 oldVelocity', '    f32 height = position[1];\n    f32 oldVelocity').replace('position[1] +=', 'position[1] = height +')
    yield 'negative-cached-half', SELECTED.replace('    f32 oldVelocity', '    f32 half = D_800AB2F0;\n    f32 oldVelocity').replace('D_800AB2F0 * (delta', 'half * (delta')


def owner_guards():
    return [dict(filename='generated_204660', function=FUNCTION, offset='0x%X' % offset,
        expected='0x%08X' % before, replacement='0x%08X' % after,
        expected_relocations='-', replacement_relocations='-',
        note='Normalize captured velocity FP register and retain retail add operand order',
        insert_after='', insert_after_relocations='', omit='false')
        for offset, before, after in ((0xC, 0xC4A00000, 0xC4A20000),
                                     (0x18, 0x46003200, 0x46061200),
                                     (0x34, 0x460C0102, 0x460C1102))]


def normalize(words):
    result = list(words)
    assert len(result) == WORDS and result[0] == 0x44866000
    for row in owner_guards():
        index = int(row['offset'], 0) // 4
        assert result[index] == int(row['expected'], 0), ('stale captured velocity allocation', index)
        result[index] = int(row['replacement'], 0)
    return result


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
    script = out / 'record-velocity.ld'
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
    out = root / 'conker/build/game-record-velocity'
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
