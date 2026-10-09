"""Complete timer, live actor selector and three callback-stage recovery."""

import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x15147740, 0x174BF0, 100
FUNCTION = 'func_15147740'
ORIGINAL = 's32 func_15147740() {\n    return 0;\n}'
DECLARATIONS = '''extern s32 D_800BE9E4;
extern s32 (*D_8008A200[])(u8 *);
extern s32 (*D_8008A23C[])(u8 *);
extern s32 (*D_8008A284[])(u8 *);
void func_1516972C(u8 *);
'''
INSERT = DECLARATIONS.split('void func_', 1)[0] + '\n'
SYMBOLS = dict(D_800BE9E4=0x800BE9E4, D_8008A200=0x8008A200,
    D_8008A23C=0x8008A23C, D_8008A284=0x8008A284, func_1516972C=0x1516972C)
BASE = '''void func_15147740(u8 *actor) {
    s8 expired = 0;
    s32 selector;

    if (*(u16 *)(actor + 0x1E) & 1) {
        *(s16 *)(actor + 0x1C) = (u32)*(s16 *)(actor + 0x1C) - (u32)D_800BE9E4;
        if (*(s16 *)(actor + 0x1C) < 0) {
            expired = 1;
        }
    }
    selector = actor[0x2F];
    if (selector >= 15) {
        func_1516972C(actor);
        return;
    }
    if (selector != 0 && !expired) {
        if (D_8008A200[selector](actor) == 0) {
            expired = 1;
        }
    }
    selector = actor[0x30];
    if (selector >= 18) {
        func_1516972C(actor);
        return;
    }
    if (selector != 0 && !expired) {
        if (D_8008A23C[selector](actor) == 0) {
            expired = 1;
        }
    }
    if (*(u16 *)(actor + 0x1E) & 0x10) {
        selector = *(s8 *)(actor + 0x24);
        if (selector < -1 || selector >= 8) {
            func_1516972C(actor);
            return;
        }
        if (selector != -1 && !expired) {
            if (D_8008A284[selector](actor) == 0) {
                expired = 1;
            }
        }
    }
    if (expired) {
        func_1516972C(actor);
    }
}'''


def byte_selectors(body=BASE):
    head, tail = body.split('    if (*(u16 *)(actor + 0x1E) & 0x10)', 1)
    return head.replace('s32 selector;', 'u8 selector;\n    s8 action;') + '    if (*(u16 *)(actor + 0x1E) & 0x10)' + tail.replace('selector', 'action')


def range_first(body):
    for offset, bound in (('2F', 15), ('30', 18)):
        body = body.replace('    selector = actor[0x%s];\n    if (selector >= %d)' % (offset, bound),
            '    if (actor[0x%s] >= %d)' % (offset, bound))
        marker = '    if (selector != 0 && !expired)'
        position = body.index(marker, body.index('    if (actor[0x%s] >= %d)' % (offset, bound)))
        body = body[:position] + '    selector = actor[0x%s];\n' % offset + body[position:]
    return body


def separate_selectors():
    body = byte_selectors().replace('u8 selector;', 'u8 first;\n    u8 second;')
    first, rest = body.split('    selector = actor[0x30];', 1)
    second, last = rest.split('    if (*(u16 *)(actor + 0x1E) & 0x10)', 1)
    return first.replace('selector', 'first') + '    second = actor[0x30];' + second.replace('selector', 'second') + '    if (*(u16 *)(actor + 0x1E) & 0x10)' + last


SELECTED = separate_selectors()
PATCHES = tuple((i, 0xA3A5001F if i in (32, 55, 85) else 0x83A5001F,
    0xA3A5001B if i in (32, 55, 85) else 0x83A5001B) for i in (32, 37, 55, 60, 85, 90))


def normalize(words):
    assert len(words) == WORDS and words[0] == 0x27BDFFE0
    result = list(words)
    for index, expected, replacement in PATCHES:
        assert result[index] == expected, (index, hex(result[index]))
        result[index] = replacement
    return result


def guard_rows():
    return [dict(filename='generated_174BF0', function=FUNCTION, offset='0x%X' % (i * 4),
        expected='0x%08X' % a, replacement='0x%08X' % b, expected_relocations='-', replacement_relocations='-',
        note='Normalize closed actor callback failure flag private spill slot', insert_after='',
        insert_after_relocations='', omit='false') for i, a, b in PATCHES]


def candidates():
    yield 'baseline', BASE
    yield 'byte-selectors', byte_selectors()
    for label, body in (('word', BASE), ('byte', byte_selectors())):
        yield label + '-range-first', range_first(body)
        yield label + '-live-table-index', range_first(body).replace('D_8008A200[selector]',
            'D_8008A200[actor[0x2F]]').replace('D_8008A23C[selector]', 'D_8008A23C[actor[0x30]]')
    separate = separate_selectors()
    yield 'separate-stage-bytes', separate
    declarations = ('s8 expired = 0;', 'u8 first;', 'u8 second;', 's8 action;')
    original = '\n'.join('    ' + d for d in declarations)
    for index, order in enumerate(itertools.permutations(declarations)):
        yield 'declaration-order-%d' % index, separate.replace(original, '\n'.join('    ' + d for d in order))
    yield 'separate-explicit-initialization', separate.replace('s8 expired = 0;', 's8 expired;').replace(
        '    if (*(u16 *)(actor + 0x1E) & 1)', '    expired = 0;\n    if (*(u16 *)(actor + 0x1E) & 1)', 1)
    timer = separate.replace('    s8 action;', '    s8 action;\n    s16 timer;').replace(
        '        *(s16 *)(actor + 0x1C) = (u32)*(s16 *)(actor + 0x1C) - (u32)D_800BE9E4;',
        '        timer = (u32)*(s16 *)(actor + 0x1C) - (u32)D_800BE9E4;\n        *(s16 *)(actor + 0x1C) = timer;')
    yield 'timer-local-reload', timer
    yield 'timer-local-use', timer.replace('if (*(s16 *)(actor + 0x1C) < 0)', 'if (timer < 0)')
    flags = separate.replace('    s8 action;', '    s8 action;\n    u16 flags;').replace(
        '    if (*(u16 *)(actor + 0x1E) &', '    flags = *(u16 *)(actor + 0x1E);\n    if (flags &')
    yield 'flags-local-reload', flags
    result = separate.replace('    s8 action;', '    s8 action;\n    s32 result;')
    for table, local in (('D_8008A200', 'first'), ('D_8008A23C', 'second'), ('D_8008A284', 'action')):
        result = result.replace('if (%s[%s](actor) == 0)' % (table, local),
            'result = %s[%s](actor);\n        if (result == 0)' % (table, local))
    yield 'callback-result-local', result
    for kind in ('u8', 's32', 'u32'):
        yield 'byte-selectors-expired-' + kind, byte_selectors().replace('s8 expired', kind + ' expired')
    for kind in ('u8', 's32', 'u32'):
        yield 'expired-' + kind, BASE.replace('s8 expired', kind + ' expired')
    yield 'signed-subtraction', BASE.replace('(u32)*(s16 *)(actor + 0x1C) - (u32)D_800BE9E4',
        '*(s16 *)(actor + 0x1C) - D_800BE9E4')
    yield 'compound-subtraction', BASE.replace('*(s16 *)(actor + 0x1C) = (u32)*(s16 *)(actor + 0x1C) - (u32)D_800BE9E4;',
        '*(s16 *)(actor + 0x1C) -= D_800BE9E4;')


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
    script = output / 'timer-callbacks.ld'
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
    output = root / 'conker/build/game-actor-timer-callbacks'
    records = []
    for name, body in candidates():
        meta, _ = compile_candidate(root, output, name, body)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (output / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
