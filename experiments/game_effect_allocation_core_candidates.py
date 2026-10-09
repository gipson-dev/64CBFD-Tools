"""Complete eleven-word effect allocation core and live resource-count fitting."""

import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x15147A80, 0x174F30, 115
FUNCTION = 'func_15147A80'
ORIGINAL = 's32 func_15147A80() {\n    return 0;\n}'
RECORD = '''typedef struct { s32 words[9]; } EffectOptional15147A80;
typedef struct {
    u8 prefix[0x10], request[0x1C];
    u8 flags[6], padding32[2];
    s32 resourceBytes;
    u8 state, padding39[3];
    u8 *entries[4], *trailing;
    s32 value;
    f32 position[3];
    EffectOptional15147A80 optional;
    u8 cleared[0x10];
    u8 *end, *payload;
    s32 padding9C;
} EffectCore15147A80;
'''
DECLARATIONS = '''extern s32 D_80082FA0;
void *func_15167A68(s32, s32, s32, s32, u8, u8);
u8 *func_1515D480(s32);
u8 *func_1515D440(void);
void *memcpy(void *, const void *, unsigned int);
void bzero(void *, int);
'''
INSERT = RECORD + '\n' + DECLARATIONS.split('void *memcpy', 1)[0].replace('extern s32 D_80082FA0;\n', '') + '\n'
SYMBOLS = dict(D_80082FA0=0x80082FA0, func_15167A68=0x15167A68,
    func_1515D480=0x1515D480, func_1515D440=0x1515D440, memcpy=0x10022EC0, bzero=0x100226F0)
BASE = '''u8 *func_15147A80(void *request, s32 payloadBytes, s32 entryBytes,
    s32 active, s32 first, s32 second, s32 resourceBytes, s32 value,
    void *optional, u8 channel, s32 context) {
    u8 *created;
    s32 kind;
    s32 i;

    kind = 0x22;
    if (*(u16 *)((u8 *)request + 0xE) & 0x40) {
        kind = 0x4D;
    }
    created = func_15167A68(kind, context,
        (u32)payloadBytes + (u32)((u8 *)request)[0x15] * (u32)entryBytes + 0xA0,
        1, channel, 1);
    if (created == NULL) {
        return NULL;
    }
    *(u8 **)(created + 0x98) = created + 0xA0;
    *(u8 **)(created + 0x94) = created + 0xA0 + payloadBytes;
    memcpy(created + 0x10, request, 28);
    created[0x2C] = 0;
    created[0x2D] = 0;
    created[0x2E] = 0;
    created[0x2F] = active;
    created[0x30] = first;
    created[0x31] = second;
    if (optional != NULL) {
        *(EffectOptional15147A80 *)(created + 0x60) = *(EffectOptional15147A80 *)optional;
    } else {
        created[0x7C] = 0;
    }
    *(s32 *)(created + 0x34) = resourceBytes;
    created[0x38] = 0;
    *(s32 *)(created + 0x50) = value;
    for (i = 0; i < 4; i++) {
        *(s32 *)(created + 0x3C + i * 4) = 0;
    }
    *(s32 *)(created + 0x4C) = 0;
    if (resourceBytes != 0) {
        for (i = 0; i <= D_80082FA0; i++) {
            *(u8 **)(created + 0x3C + i * 4) = func_1515D480(resourceBytes);
        }
        *(u8 **)(created + 0x4C) = func_1515D440();
    }
    *(f32 *)(created + 0x54) = 0.0f;
    *(f32 *)(created + 0x58) = 0.0f;
    *(f32 *)(created + 0x5C) = 0.0f;
    bzero(created + 0x84, 0x10);
    return created;
}'''


def count_first(body=BASE):
    product = '(u32)((u8 *)request)[0x15] * (u32)entryBytes'
    return body.replace(product, 'extra').replace('    s32 i;',
        '    s32 i;\n    u32 extra;').replace('    kind = 0x22;',
        '    extra = ' + product + ';\n    kind = 0x22;')


def complete_fitting():
    for explicit_else, payload_local, zero_early in itertools.product((False, True), repeat=3):
        body = count_first()
        if explicit_else:
            body = body.replace('        kind = 0x4D;\n    }', '        kind = 0x4D;\n    } else {\n        kind = 0x22;\n    }')
        if payload_local:
            body = body.replace('    u8 *created;', '    u8 *created;\n    u8 *payload;').replace(
                '    *(u8 **)(created + 0x98) = created + 0xA0;\n    *(u8 **)(created + 0x94) = created + 0xA0 + payloadBytes;',
                '    payload = created + 0xA0;\n    *(u8 **)(created + 0x98) = payload;\n    *(u8 **)(created + 0x94) = payload + payloadBytes;')
        if zero_early:
            body = body.replace('    created[0x38] = 0;\n', '').replace('    *(s32 *)(created + 0x34)',
                '    created[0x38] = 0;\n    *(s32 *)(created + 0x34)', 1)
        yield 'fit-else%d-payload%d-zero%d' % (explicit_else, payload_local, zero_early), body


def pointer_fitting():
    body = dict(complete_fitting())['fit-else1-payload1-zero0']
    for pointer_load, kind_volatile, add_cast in itertools.product((False, True), repeat=3):
        edited = body
        if pointer_load:
            edited = edited.replace('payload + payloadBytes;', '*(u8 **)(created + 0x98) + payloadBytes;')
        if kind_volatile:
            edited = edited.replace('    s32 kind;', '    volatile s32 kind;')
        if add_cast:
            edited = edited.replace('    payload = created + 0xA0;', '    payload = (u8 *)((u32)created + 0xA0);').replace(
                'payload + payloadBytes;', '(u8 *)((u32)payload + (u32)payloadBytes);')
        yield 'pointer-load%d-kind%d-cast%d' % (pointer_load, kind_volatile, add_cast), edited


def opening_fitting():
    body = dict(complete_fitting())['fit-else1-payload1-zero0']
    product = '    extra = (u32)((u8 *)request)[0x15] * (u32)entryBytes;\n'
    for kind_first, extra_type, shared_pointer in itertools.product((False, True), ('u32', 's32'), (False, True)):
        edited = body.replace('    u32 extra;', '    %s extra;' % extra_type)
        if kind_first:
            edited = edited.replace(product + '    kind = 0x22;', '    kind = 0x22;\n' + product.rstrip())
        if shared_pointer:
            edited = edited.replace('payload + payloadBytes;', '*(u8 **)(created + 0x98) + payloadBytes;')
        yield 'opening-kind%d-%s-shared%d' % (kind_first, extra_type, shared_pointer), edited


def layout_fitting():
    body = dict(complete_fitting())['fit-else1-payload1-zero0']
    for pointer_type, initial_kind, total_local in itertools.product(('u8 *', 'void *'), (False, True), (False, True)):
        edited = body.replace('    u8 *payload;', '    %s payload;' % pointer_type)
        if pointer_type == 'void *':
            edited = edited.replace('payload + payloadBytes;', '(u8 *)payload + payloadBytes;')
        if initial_kind:
            edited = edited.replace('    kind = 0x22;\n', '', 1)
        if total_local:
            edited = edited.replace('    u32 extra;', '    u32 extra;\n    u32 total;').replace(
                '    created = func_15167A68(kind, context,\n        (u32)payloadBytes + extra + 0xA0,',
                '    total = (u32)payloadBytes + extra + 0xA0;\n    created = func_15167A68(kind, context,\n        total,')
        yield 'layout-%s-kind%d-total%d' % (pointer_type.split()[0], initial_kind, total_local), edited
    for pointer_reload, reverse_order in itertools.product((False, True), repeat=2):
        edited = body
        if pointer_reload:
            edited = edited.replace('    payload = created + 0xA0;', '    payload = created;\n    payload += 0xA0;')
        if reverse_order:
            edited = edited.replace('    *(u8 **)(created + 0x98) = payload;\n    *(u8 **)(created + 0x94) = payload + payloadBytes;',
                '    *(u8 **)(created + 0x94) = payload + payloadBytes;\n    *(u8 **)(created + 0x98) = payload;')
        yield 'publish-split%d-reverse%d' % (pointer_reload, reverse_order), edited


def typed_fitting():
    body = dict(complete_fitting())['fit-else1-payload1-zero0']
    for complete, from_field in itertools.product((False, True), repeat=2):
        edited = body.replace('    u8 *created;', '    EffectCore15147A80 *created;').replace(
            '    created = func_15167A68(', '    created = (EffectCore15147A80 *)func_15167A68(').replace(
            '    payload = created + 0xA0;', '    payload = (u8 *)(created + 1);').replace(
            '*(u8 **)(created + 0x98)', 'created->payload').replace('*(u8 **)(created + 0x94)', 'created->end').replace(
            '    return created;', '    return (u8 *)created;')
        if from_field:
            edited = edited.replace('created->end = payload + payloadBytes;', 'created->end = created->payload + payloadBytes;')
        if complete:
            edited = edited.replace('memcpy(created + 0x10', 'memcpy(created->request').replace(
                '*(EffectOptional15147A80 *)(created + 0x60)', 'created->optional').replace(
                'created[0x7C]', '((u8 *)&created->optional)[0x1C]').replace(
                '*(s32 *)(created + 0x34)', 'created->resourceBytes').replace('created[0x38]', 'created->state').replace(
                '*(s32 *)(created + 0x50)', 'created->value').replace('*(s32 *)(created + 0x3C + i * 4)',
                'created->entries[i]').replace('*(u8 **)(created + 0x3C + i * 4)', 'created->entries[i]').replace(
                '*(s32 *)(created + 0x4C)', 'created->trailing').replace('*(u8 **)(created + 0x4C)', 'created->trailing').replace(
                'bzero(created + 0x84', 'bzero(created->cleared')
            for i in range(6):
                edited = edited.replace('created[0x%X]' % (0x2C + i), 'created->flags[%d]' % i)
            for i in range(3):
                edited = edited.replace('*(f32 *)(created + 0x%X)' % (0x54 + i * 4), 'created->position[%d]' % i)
        else:
            edited = edited.replace('created + 0x', '(u8 *)created + 0x').replace('created[0x', '((u8 *)created)[0x')
        yield 'typed-complete%d-field%d' % (complete, from_field), edited


def kind_fitting():
    body = dict(typed_fitting())['typed-complete1-field1']
    for type_name in ('s8', 'u8', 's16', 'u16', 'u32', 's32'):
        yield 'kind-type-' + type_name, body.replace('    s32 kind;', '    %s kind;' % type_name)
    product = '    extra = (u32)((u8 *)request)[0x15] * (u32)entryBytes;\n'
    yield 'kind-reuse-entry', body.replace('    s32 kind;\n', '').replace('kind', 'entryBytes')
    yield 'kind-reuse-active', body.replace('    s32 kind;\n', '    s32 savedActive = active;\n').replace(
        'created->flags[3] = active;', 'created->flags[3] = savedActive;').replace('kind', 'active')
    yield 'kind-no-initial', body.replace('    kind = 0x22;\n', '', 1)
    yield 'kind-product-between', body.replace(product, '').replace('    kind = 0x22;', '    kind = 0x22;\n' + product.rstrip(), 1)
    yield 'kind-null-return-created', body.replace('        return NULL;', '        return (u8 *)created;')


def state_fitting():
    body = dict(kind_fitting())['kind-type-u8']
    fields = '    created->resourceBytes = resourceBytes;\n    created->state = 0;\n    created->value = value;\n'
    for order in itertools.permutations(fields.splitlines(keepends=True)):
        name = ''.join(str(fields.splitlines(keepends=True).index(line)) for line in order)
        yield 'state-' + name, body.replace(fields, ''.join(order))
    for before in (True, False):
        edited = body.replace('for (i = 0; i < 4; i++)', 'for (; i < 4; i++)')
        edited = edited.replace('    created->resourceBytes' if before else '    for (;',
            '    i = 0;\n' + ('    created->resourceBytes' if before else '    for (;'), 1)
        yield 'state-index-before%d' % before, edited


def candidates():
    yield 'baseline', BASE
    for early in (True, False):
        body = BASE.replace('    u8 *created;\n    s32 kind;\n    s32 i;',
            '    s32 i;\n    s32 kind;\n    u8 *created;' if early else '    s32 kind;\n    u8 *created;\n    s32 i;')
        yield 'declarations-%d' % early, body
    yield 'unsigned-kind-first', BASE.replace('    if (*(u16 *)((u8 *)request + 0xE) & 0x40)',
        '    if (((u8 *)request)[0xF] & 0x40)')
    for index in (0, 1):
        body = BASE
        for name in ('active', 'first', 'second'):
            body = body.replace('s32 ' + name, ('u8' if index else 'u32') + ' ' + name)
        yield 'flag-types-%d' % index, body
    yield 'request-count-first', count_first()
    yield 'conditional-kind', BASE.replace('    kind = 0x22;\n    if (*(u16 *)((u8 *)request + 0xE) & 0x40) {\n        kind = 0x4D;\n    }',
        '    kind = (*(u16 *)((u8 *)request + 0xE) & 0x40) ? 0x4D : 0x22;')
    yield 'pointer-clear-loop', BASE.replace('    s32 i;', '    s32 i;\n    u8 *cursor;').replace(
        '    for (i = 0; i < 4; i++) {\n        *(s32 *)(created + 0x3C + i * 4) = 0;\n    }',
        '    cursor = created;\n    for (i = 0; i < 4; i++) {\n        *(s32 *)(cursor + 0x3C) = 0;\n        cursor += 4;\n    }')
    yield from complete_fitting()
    yield from pointer_fitting()
    yield from opening_fitting()
    yield from layout_fitting()
    yield from typed_fitting()
    yield from kind_fitting()
    yield from state_fitting()


SELECTED = dict(state_fitting())['state-021']
CALLER_CHANGES = {
    'conker/src/game/generated_175250.c': ((
        'u8 *func_15147A80(void *, s32, s32, s32, s32, s32, s32, s32, s32, u8, s32);',
        'u8 *func_15147A80(void *, s32, s32, s32, s32, s32, s32, s32, void *, u8, s32);'), (
        '        fadeFlag, fadeAlpha, extraBytes, channel, context);',
        '        fadeFlag, fadeAlpha, (void *)extraBytes, channel, context);')),
    'conker/src/game_1897A0.c': ((
        'void *func_15147A80(void *arg0, void *arg1, s32 arg2, s32 arg3, s32 arg4, s32 arg5, s32 arg6, s32 arg7, s32 arg8, u8 arg9, s32 arg10);',
        'u8 *func_15147A80(void *, s32, s32, s32, s32, s32, s32, s32, void *, u8, s32);'), (
        'func_15147A80(arg0, arg1 + 0x40, 0x10, 8, 8, 8, 0, 0, arg3, arg4, arg5)',
        'func_15147A80(arg0, (u32)arg1 + 0x40, 0x10, 8, 8, 8, 0, 0, (void *)arg3, arg4, arg5)'))}


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
    script = output / 'core.ld'
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
    output = root / 'conker/build/game-effect-allocation-core'
    records = []
    for name, body in candidates():
        meta, _ = compile_candidate(root, output, name, body)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (output / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
