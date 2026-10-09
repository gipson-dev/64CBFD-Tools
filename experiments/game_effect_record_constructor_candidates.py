"""Recover the complete fifteen-word effect-record construction interface."""

import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x15147DA0, 0x175250, 70
FUNCTION = 'func_15147DA0'
ORIGINAL = 's32 func_15147DA0() {\n    return 0;\n}'
RENDER = '''typedef struct { s32 words[8]; } RenderRecord15147DA0;
'''
DECLARATIONS = '''u8 *func_15147A80(void *, s32, s32, s32, s32, s32, s32, s32, s32, u8, s32);
void *memcpy(void *, const void *, unsigned int);
'''
SYMBOLS = dict(func_15147A80=0x15147A80, memcpy=0x10022EC0)
BASE = '''u8 *func_15147DA0(void *request, void *descriptor, s32 payloadBytes,
    s32 active, s32 first, s32 second, s32 third, s32 fourth, s32 fifth,
    s32 fadeFlag, s32 fadeAlpha, void *render, s32 extraBytes, u8 channel, s32 context) {
    u8 *created;
    u8 *payload;

    *(s32 *)((u8 *)request + 0x10) = 1;
    created = func_15147A80(request, (u32)payloadBytes + 0x48, 0x14, 1, 0, 1,
        fadeFlag, fadeAlpha, extraBytes, channel, context);
    if (created == NULL) {
        return NULL;
    }
    payload = *(u8 **)(created + 0x98);
    memcpy(payload, descriptor, 32);
    payload[0x20] = active;
    payload[0x21] = first;
    payload[0x22] = second;
    payload[0x23] = third;
    payload[0x24] = fourth;
    payload[0x25] = fifth;
    *(RenderRecord15147DA0 *)(payload + 0x28) = *(RenderRecord15147DA0 *)render;
    return created;
}'''
SELECTED = BASE
INSERT = RENDER + DECLARATIONS.split('void *memcpy', 1)[0] + '\n'
CALLER_ORIGINAL = '''u8 *func_15147DA0(void *, void *, s32, u8, u8, u8, u8, u8, u8,
    u8, u8, void *, s32, u8, s32);'''
CALLER_SELECTED = '''u8 *func_15147DA0(void *, void *, s32, s32, s32, s32, s32, s32, s32,
    s32, s32, void *, s32, u8, s32);'''


def candidates():
    yield 'baseline', BASE
    yield 'payload-first', BASE.replace('    u8 *created;\n    u8 *payload;', '    u8 *payload;\n    u8 *created;')
    for narrow in (False, True):
        body = BASE
        if narrow:
            for name in ('active', 'first', 'second', 'third', 'fourth', 'fifth', 'fadeFlag', 'fadeAlpha'):
                body = body.replace('s32 ' + name, 'u8 ' + name)
        yield 'narrow%d' % narrow, body
    copy = '    *(RenderRecord15147DA0 *)(payload + 0x28) = *(RenderRecord15147DA0 *)render;\n'
    for anchor in ('    payload[0x20]', '    payload[0x23]', '    return created;'):
        yield 'render-before-' + anchor.strip().split()[0], BASE.replace(copy, '').replace(anchor, copy + anchor, 1)
    yield 'inline-render-loop', BASE.replace('    u8 *payload;', '    u8 *payload;\n    s32 i;').replace(copy,
        '    for (i = 0; i < 8; i++) {\n        ((s32 *)(payload + 0x28))[i] = ((s32 *)render)[i];\n    }\n')
    yield 'copy-cast', BASE.replace('    u8 *created;', '    void *created;').replace('created + 0x98', '(u8 *)created + 0x98')


def compile_candidate(root, output, name, body=SELECTED, profile='o2g3'):
    output.mkdir(exist_ok=True)
    source, obj, elf = (output / (name + suffix) for suffix in ('.c', '.o', '.elf'))
    source.write_text('#include <ultra64.h>\n' + RENDER + DECLARATIONS + body + '\n')
    result = subprocess.run(['ido/ido5.3_recomp/cc', '-c', '-32', '-G', '0', '-Xfullwarn', '-Xcpluscomm',
        '-signed', '-nostdinc', '-non_shared', '-Wab,-r4300_mul', '-mips2', '-o32',
        '-I', 'conker/include', '-I', 'conker/include/2.0L', '-I', 'conker/include/2.0L/PR',
        '-I', 'conker/include/libc', '-D_LANGUAGE_C', '-D_FINALROM', '-DF3DEX_GBI_2',
        '-D_MIPS_SZLONG=32', *PROFILES[profile], '-o', str(obj.relative_to(root)),
        str(source.relative_to(root))], cwd=root, capture_output=True, text=True)
    if result.returncode or result.stdout or result.stderr:
        raise ValueError(result.stdout + result.stderr)
    script = output / 'constructor.ld'
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
    retail = struct.unpack_from('>70I', (root / 'conker/conker.us.bin').read_bytes(), ROM)
    return dict(name=name, profile=profile, body_words=end, frame=(-words[0]) & 65535,
        differences=sum(a != b for a, b in itertools.zip_longest(words, retail, fillvalue=0)),
        relocations=relocations, diagnostics='',
        pool_bytes=sum(len(v[1]) for n, v in pools.items() if n in ('.rodata', '.data'))), words


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / 'conker/build/game-effect-record-constructor'
    records = []
    for name, body in candidates():
        meta, _ = compile_candidate(root, output, name, body)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (output / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
