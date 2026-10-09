"""Recover the complete record factory and mixed integer/float O32 ABI."""

import argparse
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151D71B0, 0x204660, 45
FUNCTION = 'func_151D71B0'
ORIGINAL = 's32 func_151D71B0() {\n    return 0;\n}'
RECORD = '''typedef struct {
    u8 *attached;
    u8 selector, flags, padding[2];
    struct { f32 x, y, z; } position;
    f32 threshold;
} CallbackRecord151D7264;
'''
DECLARATIONS = '''void *func_15149130(s16, s8, s8, s8, u8, u8, s32, u8, s32);
void *memcpy(void *, const void *, unsigned int);
'''
SYMBOLS = dict(func_15149130=0x15149130, memcpy=0x10022EC0)
BASE = '''u8 *func_151D71B0(s16 duration, u8 active, u8 selector, f32 threshold,
    s32 extraBytes, u8 slot, s32 context) {
    CallbackRecord151D7264 record;
    u8 *created;

    record.attached = NULL;
    record.selector = selector;
    record.flags = 0;
    record.position.x = 0.0f;
    record.position.y = 0.0f;
    record.position.z = 0.0f;
    record.threshold = threshold;
    created = func_15149130(duration, -1, 0x42, -1, active, 0x36,
        extraBytes + sizeof(record), slot, context);
    if (created != NULL) {
        memcpy(created + 0x28, &record, sizeof(record));
    }
    return created;
}'''
SELECTED = BASE.replace('    CallbackRecord151D7264 record;\n    u8 *created;',
    '    u8 *created;\n    CallbackRecord151D7264 record;')
CALLER_ORIGINAL = '''void func_151D74B0(u8 *arg0, u8 arg1, s8 arg2, u8 arg3, s32 arg4) {
    struct { u8 *word0; u8 byte0; u8 byte1; s8 byte2; } rec;
    s32 temp_v0;

    rec.word0 = arg0;
    rec.byte0 = arg0[0x3B];
    rec.byte1 = arg1;
    rec.byte2 = arg2;
    temp_v0 = func_151D71B0(0x12C, 0, 0, 0x41400000, 8, arg3, arg4);
    if (temp_v0 != 0) {
        memcpy((u8 *)(temp_v0 + 0x40), &rec, 8);
    }
}'''
CALLER_SELECTED = CALLER_ORIGINAL.replace('s32 temp_v0;', 'u8 *temp_v0;').replace(
    '0x41400000, 8', '12.0f, 8')


def candidates():
    yield 'selected', SELECTED
    yield 'record-first', BASE
    for types in itertools.product(('s16', 's32', 'volatile s16', 'volatile s32'),
            ('u8', 'u32', 'volatile u8', 'volatile u32')):
        body = SELECTED.replace('s16 duration', types[0] + ' duration').replace('u8 active', types[1] + ' active').replace(
            'u8 selector', types[1] + ' selector').replace('u8 slot', types[1] + ' slot')
        yield 'types-' + '-'.join(t.replace(' ', '_') for t in types), body
    yield 'signed-size', SELECTED.replace('extraBytes + sizeof(record)', 'extraBytes + 0x18')
    yield 'negative-wrong-kind', SELECTED.replace('0x42, -1', '0x43, -1')
    yield 'negative-zero-active', SELECTED.replace('active, 0x36', '0, 0x36')
    yield 'negative-zero-threshold', SELECTED.replace('record.threshold = threshold', 'record.threshold = 0.0f')
    yield 'negative-short-copy', SELECTED.replace('memcpy(created + 0x28, &record, sizeof(record))',
        'memcpy(created + 0x28, &record, 20)')
    yield 'negative-reloaded-result', SELECTED.replace('memcpy(created + 0x28, &record, sizeof(record));',
        'created = memcpy(created + 0x28, &record, sizeof(record));')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    out.mkdir(exist_ok=True)
    source, obj, elf = (out / (name + suffix) for suffix in ('.c', '.o', '.elf'))
    source.write_text('#include <ultra64.h>\n' + RECORD + DECLARATIONS + '\n' + body + '\n')
    result = subprocess.run(['ido/ido5.3_recomp/cc', '-c', '-32', '-G', '0', '-Xfullwarn', '-Xcpluscomm',
        '-signed', '-nostdinc', '-non_shared', '-Wab,-r4300_mul', '-mips2', '-o32',
        '-I', 'conker/include', '-I', 'conker/include/2.0L', '-I', 'conker/include/2.0L/PR',
        '-I', 'conker/include/libc', '-D_LANGUAGE_C', '-D_FINALROM', '-DF3DEX_GBI_2',
        '-D_MIPS_SZLONG=32', *PROFILES[profile], '-o', str(obj.relative_to(root)),
        str(source.relative_to(root))], cwd=root, capture_output=True, text=True)
    if result.returncode or result.stdout or result.stderr:
        raise ValueError(result.stdout + result.stderr)
    script = out / 'constructor.ld'
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
    out = root / 'conker/build/game-record-constructor'
    records = []
    for name, body in candidates():
        for profile in PROFILES if args.profiles else ('o2g3',):
            meta, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
