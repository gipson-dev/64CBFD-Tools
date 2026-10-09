"""Recover the complete 18-argument table-driven trail effect constructor."""

import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151DA6F8, 0x207BA8, 144
FUNCTION = 'func_151DA6F8'
ORIGINAL = 's32 func_151DA6F8() {\n    return 0;\n}'
OLD_DECLARATION = 's32 func_151DA6F8();'
DECLARATION = '''u8 *func_151DA6F8(void *, void *, f32, s16, u8, f32, s32, u8,
    f32, f32, u8, u8, s32, s16, s16, s32, u8, s32);'''
TYPES = '''typedef struct { f32 x, y, z; } TrailPosition151DA6F8;
typedef struct {
    TrailPosition151DA6F8 position;
    s16 duration, kind;
    s32 active;
    u8 mode, selector, padding[2];
    s32 value;
} TrailRequest151DA6F8;
typedef struct {
    f32 time;
    TrailPosition151DA6F8 velocity;
    f32 scale, limit;
    u8 flags, kind, alpha, mode;
    s16 first, second;
} TrailDescriptor151DA6F8;
typedef struct {
    f32 first, second;
    u8 selector, padding[3];
} TrailPayload151DA6F8;
typedef struct {
    s32 zero, command, mode, kind, width, alpha, count;
    u8 flags, payloadBytes, padding[2];
    u8 unused[16];
} TrailRender151DA6F8;
'''
DECLARATIONS = '''extern u8 D_800AB404[], D_800AB330[], D_800AB3F4[];
extern f32 D_800AB498;
u8 *func_15147DA0(void *, void *, s32, u8, u8, u8, u8, u8, u8,
    u8, u8, void *, s32, u8, s32);
void *memcpy(void *, const void *, unsigned int);
'''
SYMBOLS = dict(D_800AB404=0x800AB404, D_800AB330=0x800AB330,
    D_800AB3F4=0x800AB3F4, D_800AB498=0x800AB498,
    func_15147DA0=0x15147DA0, memcpy=0x10022EC0)
BASE = '''u8 *func_151DA6F8(void *position, void *velocity, f32 scale, s16 duration,
    u8 mode, f32 time, s32 requestSelector, u8 opaque, f32 first, f32 second,
    u8 fade, u8 selector, s32 extraBytes, s16 firstValue, s16 secondValue,
    s32 requestValue, u8 channel, s32 context) {
    u8 *created;
    TrailRequest151DA6F8 request;
    TrailDescriptor151DA6F8 descriptor;
    TrailPayload151DA6F8 payload;
    TrailRender151DA6F8 render;
    u8 flags;
    s32 firstFlag, secondFlag, fadeFlag, fadeAlpha;

    request.position = *(TrailPosition151DA6F8 *)position;
    request.duration = duration + 16;
    request.kind = 53;
    request.active = 1;
    request.mode = 255;
    request.selector = requestSelector;
    request.value = requestValue;
    descriptor.time = time;
    descriptor.velocity = *(TrailPosition151DA6F8 *)velocity;
    descriptor.scale = scale;
    descriptor.limit = D_800AB498;
    flags = 0x48;
    if (D_800AB404[selector]) {
        flags |= 0x20;
    }
    if (D_800AB330[selector]) {
        flags |= 0x80;
    }
    descriptor.kind = D_800AB3F4[selector];
    descriptor.alpha = 255;
    descriptor.mode = mode;
    descriptor.first = firstValue;
    descriptor.second = secondValue;
    if (opaque) {
        descriptor.flags = flags | 3;
        firstFlag = 7;
        secondFlag = 4;
    } else {
        descriptor.flags = flags;
        firstFlag = 0;
        secondFlag = 0;
    }
    payload.first = first;
    payload.second = second;
    payload.selector = selector;
    render.zero = 0;
    render.command = 0x220005;
    render.mode = 0x50600;
    render.kind = 3;
    render.width = 70;
    render.alpha = 128;
    render.count = 32;
    render.flags = 0;
    render.payloadBytes = 12;
    if (fade) {
        fadeFlag = 2;
        fadeAlpha = 255;
    } else {
        fadeFlag = 0;
        fadeAlpha = 0;
    }
    created = func_15147DA0(&request, &descriptor, 16, 1, 0, 0,
        firstFlag, secondFlag, 0, fadeFlag, fadeAlpha, &render,
        extraBytes, channel, context);
    if (created != NULL) {
        memcpy(*(u8 **)(created + 0x98) + 0x48, &payload, sizeof(payload));
    }
    return created;
}'''
SPLIT = BASE.replace('    u8 flags;', '    u8 flags;\n    s32 firstContribution, secondContribution;').replace(
    '    request.position =', '    request.selector = requestSelector;\n    request.position =', 1).replace(
    '    request.selector = requestSelector;\n    request.value', '    request.value').replace(
    'request.mode = 255;', 'request.mode = -1;').replace(
    '    flags = 0x48;\n', '    firstContribution = 0;\n').replace('        flags |= 0x20;',
    '        firstContribution = 0x20;').replace('    if (D_800AB330[selector])',
    '    secondContribution = 0;\n    if (D_800AB330[selector])').replace(
    '        flags |= 0x80;', '        secondContribution = 0x80;').replace(
    '    descriptor.kind =', '    flags = (firstContribution | secondContribution | 8) | 0x40;\n    descriptor.kind =', 1)


def focused_candidates():
    types = TYPES.replace('    u8 mode, selector, padding[2];',
        '    s8 mode;\n    u8 selector, padding[2];')
    for narrow, first_else, flag_shape, flag_type in itertools.product(
            (False, True), ('empty', 'none'), ('sequence', 'combined', 'cast', 'masked'), ('u8', 's8')):
        body = SPLIT.replace('    u8 flags;', '    %s flags;' % flag_type)
        if narrow:
            body = body.replace('    s32 firstContribution, secondContribution;',
                '    u8 firstContribution, secondContribution;').replace(
                '    s32 firstFlag, secondFlag, fadeFlag, fadeAlpha;',
                '    u8 firstFlag, secondFlag, fadeFlag, fadeAlpha;')
        if first_else == 'empty':
            body = body.replace('    }\n    secondContribution = 0;',
                '    } else {\n    }\n    secondContribution = 0;')
        body = body.replace('    }\n    flags =',
            '    } else {\n    }\n    flags =')
        expression = {
            'sequence': 'flags = secondContribution | 8;\n    flags |= firstContribution;\n    flags |= 0x40;',
            'combined': 'flags = (secondContribution | 8) | firstContribution;\n    flags |= 0x40;',
            'cast': 'flags = (u8)(secondContribution | 8) | firstContribution;\n    flags |= 0x40;',
            'masked': 'flags = ((secondContribution | 8) | firstContribution) & 255;\n    flags |= 0x40;',
        }[flag_shape]
        body = body.replace('flags = (firstContribution | secondContribution | 8) | 0x40;', expression)
        yield 'focused-n%d-%s-%s-%s' % (narrow, first_else, flag_shape, flag_type), body, types if narrow else types.replace('    u8 unused[16];\n', '')


def flag_candidates():
    for narrow, update, use in itertools.product((False, True), ('or', 'ternary'), ('field', 'merged', 'normal', 'register')):
        body = SPLIT.replace('firstContribution = 0x20;', 'firstContribution |= 0x20;').replace(
            'secondContribution = 0x80;', 'secondContribution |= 0x80;')
        if update == 'ternary':
            body = body.replace('    firstContribution = 0;\n    if (D_800AB404[selector]) {\n        firstContribution |= 0x20;\n    }',
                '    firstContribution = D_800AB404[selector] ? 0x20 : 0;').replace(
                '    secondContribution = 0;\n    if (D_800AB330[selector]) {\n        secondContribution |= 0x80;\n    }',
                '    secondContribution = D_800AB330[selector] ? 0x80 : 0;')
        if narrow:
            body = body.replace('    s32 firstContribution, secondContribution;',
                '    u8 firstContribution, secondContribution;').replace('    s32 firstFlag, secondFlag, fadeFlag, fadeAlpha;',
                '    u8 firstFlag, secondFlag, fadeFlag, fadeAlpha;')
        if use == 'field':
            body = body.replace('    flags = (firstContribution | secondContribution | 8) | 0x40;',
                '    descriptor.flags = (secondContribution | 8) | firstContribution;\n    descriptor.flags |= 0x40;').replace(
                'descriptor.flags = flags | 3;', 'descriptor.flags |= 3;').replace('        descriptor.flags = flags;\n', '')
        elif use == 'merged':
            body = body.replace('        descriptor.flags = flags | 3;', '        flags |= 3;').replace(
                '        descriptor.flags = flags;\n', '').replace('    payload.first =', '    descriptor.flags = flags;\n    payload.first =')
        elif use == 'register':
            body = body.replace('    u8 flags;', '    register u8 flags;')
        types = TYPES.replace('    u8 mode, selector, padding[2];', '    s8 mode;\n    u8 selector, padding[2];')
        yield 'flags-n%d-%s-%s' % (narrow, update, use), body, types if narrow else types.replace('    u8 unused[16];\n', '')


def layout_candidates():
    _, body, types = next(c for c in flag_candidates() if c[0] == 'flags-n0-ternary-field')
    lines = ('    TrailRender151DA6F8 render;\n', '    u8 flags;\n',
        '    s32 firstContribution, secondContribution;\n',
        '    s32 firstFlag, secondFlag, fadeFlag, fadeAlpha;\n')
    original = ''.join(lines)
    assert original in body
    for index, order in enumerate(itertools.permutations(lines)):
        yield 'layout-%02d' % index, body.replace(original, ''.join(order)), types


def complete_candidates():
    _, body, types = next(c for c in flag_candidates() if c[0] == 'flags-n0-ternary-field')
    used = body.replace('    descriptor.flags = (secondContribution | 8) | firstContribution;\n    descriptor.flags |= 0x40;',
        '    flags = (secondContribution | 8) | firstContribution;\n    flags |= 0x40;\n    descriptor.flags = flags;')
    yield 'complete-field', used, types
    yield 'complete-no-unused', body.replace('    u8 flags;\n', ''), types
    yield 'complete-split-flags', used.replace('    flags |= 0x40;\n    descriptor.flags = flags;',
        '    descriptor.flags = flags | 0x40;'), types


def candidates():
    yield 'baseline', BASE
    for flags_type in ('u8', 'u32', 's32'):
        yield 'split-' + flags_type, SPLIT.replace('    u8 flags;', '    %s flags;' % flags_type), TYPES.replace(
            '    u8 unused[16];\n', '')
    for size, flags_type in itertools.product((0, 16), ('u8', 'u32', 's32')):
        body = BASE.replace('    u8 flags;', '    %s flags;' % flags_type)
        if size == 0:
            types = TYPES.replace('    u8 unused[16];\n', '')
        else:
            types = TYPES
        yield 'render%d-flags%s' % (size, flags_type), body, types
    for size, narrow, contribution_type, explicit_else in itertools.product((0, 16), (False, True), ('s32', 'u8'), (False, True)):
        body = SPLIT.replace('    s32 firstContribution, secondContribution;',
            '    %s firstContribution, secondContribution;' % contribution_type)
        if narrow:
            body = body.replace('    s32 firstFlag, secondFlag, fadeFlag, fadeAlpha;',
                '    u8 firstFlag, secondFlag, fadeFlag, fadeAlpha;')
        if explicit_else:
            body = body.replace('    }\n    secondContribution = 0;', '    } else {\n        firstContribution = 0;\n    }\n    secondContribution = 0;').replace(
                '    }\n    flags =', '    } else {\n        secondContribution = 0;\n    }\n    flags =')
        body = body.replace('(firstContribution | secondContribution | 8) | 0x40',
            '(secondContribution | 8) | firstContribution').replace('    descriptor.kind =',
            '    flags |= 0x40;\n    descriptor.kind =', 1)
        yield 'split-r%d-n%d-%s-e%d' % (size, narrow, contribution_type, explicit_else), body, TYPES.replace(
            '    u8 unused[16];\n', '') if size == 0 else TYPES


_, SELECTED, SELECTED_TYPES = next(complete_candidates())
INSERT = SELECTED_TYPES + DECLARATIONS.split('void *memcpy', 1)[0] + '\n'


def compile_candidate(root, output, name, body=SELECTED, types=SELECTED_TYPES, profile='o2g3'):
    output.mkdir(exist_ok=True)
    source, obj, elf = (output / (name + suffix) for suffix in ('.c', '.o', '.elf'))
    source.write_text('#include <ultra64.h>\n' + types + DECLARATIONS + body + '\n')
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
    retail = struct.unpack_from('>%dI' % WORDS, (root / 'conker/conker.us.bin').read_bytes(), ROM)
    return dict(name=name, profile=profile, body_words=end, frame=(-words[0]) & 65535,
        differences=sum(a != b for a, b in itertools.zip_longest(words, retail, fillvalue=0)),
        relocations=relocations, diagnostics='',
        pool_bytes=sum(len(v[1]) for n, v in pools.items() if n in ('.rodata', '.data'))), words


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / 'conker/build/game-trail-effect-constructor'
    records = []
    for candidate in itertools.chain(candidates(), focused_candidates(), flag_candidates(), layout_candidates(), complete_candidates()):
        name, body = candidate[:2]
        types = candidate[2] if len(candidate) == 3 else TYPES
        meta, _ = compile_candidate(root, output, name, body, types)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (output / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
