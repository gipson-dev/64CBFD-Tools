"""Recover the complete attachment request/payload construction and copy flow."""

import argparse
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151D7830, 0x204CE0, 63
FUNCTION = 'func_151D7830'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_204660/func_151D7830.s")'
DECLARATIONS = '''typedef struct {
    f32 x, y, z;
} AttachmentPosition151D7830;

typedef struct {
    AttachmentPosition151D7830 position;
    u16 duration;
    u16 flags;
    s32 kind;
    u8 mode;
    u8 count;
    s32 value;
} AttachmentRequest151D7830;

typedef struct {
    u8 *owner;
    AttachmentPosition151D7830 position;
    AttachmentPosition151D7830 velocity;
} AttachmentPayload151D7830;

u8 *func_15147A80(void *, s32, s32, s32, s32, s32, s32, s32, void *, u8, s32);
void *memcpy(void *, const void *, unsigned int);
'''
SYMBOLS = {'func_15147A80': 0x15147A80, 'memcpy': 0x10022EC0}
BASE = '''void func_151D7830(u8 *owner) {
    AttachmentRequest151D7830 request;
    AttachmentPayload151D7830 payload;
    u8 *record;

    payload.owner = owner;
    payload.position = *(AttachmentPosition151D7830 *)(owner + 0x30);
    payload.velocity.x = 0.0f;
    payload.velocity.y = 0.0f;
    payload.velocity.z = 0.0f;
    request.count = 25;
    request.position = *(AttachmentPosition151D7830 *)(owner + 0x30);
    request.duration = 300;
    request.flags = 0x76;
    request.kind = 0x12;
    request.mode = 4;
    request.value = 0;
    record = func_15147A80(&request, 0x20, sizeof(payload), 0xD, 0x10, 0x10, 0, 0, NULL, owner[0xC], owner[1]);
    if (record != NULL) {
        memcpy(*(void **)(record + 0x98), &payload, sizeof(payload));
        *(u8 **)(owner + 0x28) = record;
    }
}'''

SELECTED = BASE.replace('    AttachmentRequest151D7830 request;\n    AttachmentPayload151D7830 payload;\n    u8 *record;',
    '    u8 *record;\n    AttachmentPayload151D7830 payload;\n    AttachmentRequest151D7830 request;\n    AttachmentPosition151D7830 *position;').replace(
    '    payload.owner = owner;', '    position = (AttachmentPosition151D7830 *)(owner + 0x30);\n    payload.owner = owner;').replace(
    '*(AttachmentPosition151D7830 *)(owner + 0x30)', '*position')


def candidates():
    yield 'selected', SELECTED
    yield 'no-position-pointer', BASE
    yield 'payload-first', BASE.replace('    AttachmentRequest151D7830 request;\n    AttachmentPayload151D7830 payload;',
        '    AttachmentPayload151D7830 payload;\n    AttachmentRequest151D7830 request;')
    yield 'record-first', BASE.replace('    u8 *record;\n', '').replace('    AttachmentRequest', '    u8 *record;\n    AttachmentRequest', 1)
    yield 'assigned-zeros', BASE.replace('    payload.velocity.x = 0.0f;\n    payload.velocity.y = 0.0f;\n    payload.velocity.z = 0.0f;',
        '    payload.velocity.x = payload.velocity.y = payload.velocity.z = 0.0f;')
    yield 'request-count-last', BASE.replace('    request.count = 25;\n', '').replace('    request.value = 0;', '    request.value = 0;\n    request.count = 25;')
    yield 'request-first', BASE.replace(
        '    payload.owner = owner;\n    payload.position = *(AttachmentPosition151D7830 *)(owner + 0x30);\n    payload.velocity.x = 0.0f;\n    payload.velocity.y = 0.0f;\n    payload.velocity.z = 0.0f;\n', '').replace(
        '    record = func_', '    payload.owner = owner;\n    payload.position = *(AttachmentPosition151D7830 *)(owner + 0x30);\n    payload.velocity.x = 0.0f;\n    payload.velocity.y = 0.0f;\n    payload.velocity.z = 0.0f;\n    record = func_', 1)
    yield 'position-pointer', BASE.replace('    u8 *record;', '    u8 *record;\n    AttachmentPosition151D7830 *position;').replace(
        '    payload.owner = owner;', '    position = (AttachmentPosition151D7830 *)(owner + 0x30);\n    payload.owner = owner;').replace('*(AttachmentPosition151D7830 *)(owner + 0x30)', '*position')
    declarations = ('AttachmentRequest151D7830 request;', 'AttachmentPayload151D7830 payload;',
                    'u8 *record;', 'AttachmentPosition151D7830 *position;')
    pointer = BASE.replace('    u8 *record;', '    u8 *record;\n    AttachmentPosition151D7830 *position;').replace(
        '    payload.owner = owner;', '    position = (AttachmentPosition151D7830 *)(owner + 0x30);\n    payload.owner = owner;').replace('*(AttachmentPosition151D7830 *)(owner + 0x30)', '*position')
    old = '\n'.join('    ' + declaration for declaration in declarations)
    for order in itertools.permutations(range(4)):
        yield 'position-order-' + ''.join(map(str, order)), pointer.replace(old,
            '\n'.join('    ' + declarations[i] for i in order))
    yield 'payload-no-chain', BASE.replace('sizeof(payload)', '0x1C')
    yield 'negative-count', BASE.replace('request.count = 25;', 'request.count = 24;')
    yield 'negative-duration', BASE.replace('request.duration = 300;', 'request.duration = 299;')
    yield 'negative-flags', BASE.replace('request.flags = 0x76;', 'request.flags = 0x36;')
    yield 'negative-payload-reload', BASE.replace('        memcpy(', '        payload.position = *(AttachmentPosition151D7830 *)(owner + 0x30);\n        memcpy(')
    yield 'negative-attach-before-copy', BASE.replace('        memcpy(*(void **)(record + 0x98), &payload, sizeof(payload));\n        *(u8 **)(owner + 0x28) = record;',
        '        *(u8 **)(owner + 0x28) = record;\n        memcpy(*(void **)(record + 0x98), &payload, sizeof(payload));')
    yield 'negative-short-copy', BASE.replace('&payload, sizeof(payload)', '&payload, sizeof(payload) - 4')
    yield 'negative-signed-byte', BASE.replace('owner[0xC]', '*(s8 *)(owner + 0xC)')
    yield 'negative-copy-return-owner', BASE.replace('        memcpy(*(void **)(record + 0x98), &payload, sizeof(payload));',
        '        record = memcpy(*(void **)(record + 0x98), &payload, sizeof(payload));')


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
    script = out / 'attachment-allocation.ld'
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
    out = root / 'conker/build/game-attachment-allocation'
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
