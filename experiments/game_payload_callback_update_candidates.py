"""Complete captured-payload callback, fade and actor-position recovery."""

import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x15147EB8, 0x175368, 97
FUNCTION = 'func_15147EB8'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_175250/func_15147EB8.s")'
DECLARATIONS = '''typedef struct { u32 words[3]; } ActorPosition15147EB8;
extern s32 (*D_8008A3E0[])(u8 *);
extern s32 (*D_8008A3F8[])(u8 *);
extern s32 (*D_8008A42C[])(u8 *);
'''
SYMBOLS = dict(D_8008A3E0=0x8008A3E0, D_8008A3F8=0x8008A3F8, D_8008A42C=0x8008A42C)
BASE = '''s8 func_15147EB8(u8 *actor) {
    u8 *payload = *(u8 **)(actor + 0x98);
    s8 failed = 0;
    s32 success;
    s32 selector;
    s32 value;

    selector = payload[0x20];
    if (selector != 0) {
        if (D_8008A3E0[selector](actor) == 0) {
            failed = 1;
        }
    }
    selector = payload[0x21];
    if (selector != 0 && !failed) {
        if (D_8008A3F8[selector](actor) == 0) {
            failed = 1;
        }
    }
    if (payload[0x18] & 0x40) {
        if (!failed) {
            value = *(s16 *)(actor + 0x1C);
            if (value < *(s16 *)(payload + 0x1C)) {
                value = (u32)value * (u32)*(s16 *)(payload + 0x1E);
                if (value < payload[0x1B]) {
                    payload[0x1B] = value;
                }
            }
        }
    }
    success = !failed;
    if (failed) {
        selector = payload[0x22];
        if (selector != 0) {
            D_8008A42C[selector](actor);
        }
    }
    if (*(s8 *)(actor + 0x2C) > 0) {
        *(ActorPosition15147EB8 *)(actor + 0x54) = *(ActorPosition15147EB8 *)(
            *(u8 **)(actor + 0x94) + *(s8 *)(actor + 0x2D) * 20);
    } else {
        *(f32 *)(actor + 0x54) = 0.0f;
        *(f32 *)(actor + 0x58) = 0.0f;
        *(f32 *)(actor + 0x5C) = 0.0f;
    }
    return success;
}'''
SELECTED = '''s32 func_15147EB8(u8 *actor) {
    u8 *payload = *(u8 **)(actor + 0x98);
    s8 failed = 0;
    s32 success;
    s32 selector;
    s32 value;
    u8 *records;

    selector = payload[0x20];
    if (selector != 0) {
        if (D_8008A3E0[selector](actor) == 0) {
            failed = 1;
        }
    }
    selector = payload[0x21];
    if (selector != 0 && !failed) {
        if (D_8008A3F8[selector](actor) == 0) {
            failed = 1;
        }
    }
    if ((payload[0x18] & 0x40) && !failed) {
        value = *(s16 *)(actor + 0x1C);
        if (value < *(s16 *)(payload + 0x1C)) {
            s32 product;
            product = (u32)value * (u32)*(s16 *)(payload + 0x1E);
            if (product < payload[0x1B]) {
                payload[0x1B] = product;
            }
        }
    }
    success = !failed;
    if (failed) {
        selector = payload[0x22];
        if (selector != 0) {
            D_8008A42C[selector](actor);
        }
    }
    records = *(u8 **)(actor + 0x94);
    if (*(s8 *)(actor + 0x2C) > 0) {
        *(ActorPosition15147EB8 *)(actor + 0x54) = *(ActorPosition15147EB8 *)(
            records + *(s8 *)(actor + 0x2D) * 20);
    } else {
        *(f32 *)(actor + 0x54) = 0.0f;
        *(f32 *)(actor + 0x58) = 0.0f;
        *(f32 *)(actor + 0x5C) = 0.0f;
    }
    return (s8)success;
}'''
PATCHES = (
    (0, 0x27BDFFE0, 0x27BDFFD0),
    (10, 0xAFA3001C, 0xAFA3002C), (11, 0xAFA40020, 0xAFA40030),
    (13, 0xA3A0001B, 0xA3A0002B), (14, 0x8FA3001C, 0x8FA3002C),
    (15, 0x8FA40020, 0x8FA40030), (17, 0x83A6001B, 0x83A6002B),
    (27, 0xAFA3001C, 0xAFA3002C), (28, 0xAFA40020, 0xAFA40030),
    (30, 0xA3A6001B, 0xA3A6002B), (31, 0x8FA3001C, 0x8FA3002C),
    (32, 0x8FA40020, 0x8FA40030), (34, 0x83A6001B, 0x83A6002B),
    (49, 0x01420019, 0x004A0019),
    (55, 0x50C0000E, 0x10C0000D), (56, 0x808D002C, 0x2CC50001),
    (63, 0xAFA40020, 0xAFA40030), (64, 0xA3A6001B, 0xAFA50018),
    (67, 0x8FA40020, 0x8FA40030), (68, 0x83A6001B, 0x8FA50018),
    (77, 0x01E2C021, 0x004FC021),
    (90, 0x2CC20001, 0x00051600), (91, 0x00025600, 0x00025603),
    (92, 0x000A1603, 0x01401025), (94, 0x27BD0020, 0x27BD0030),
)


def normalize(words):
    assert len(words) == WORDS
    result = list(words)
    for index, expected, replacement in PATCHES:
        assert result[index] == expected, (index, hex(result[index]))
        result[index] = replacement
    return result


def guard_rows():
    return [dict(filename='generated_175250', function=FUNCTION, offset='0x%X' % (i * 4),
        expected='0x%08X' % a, replacement='0x%08X' % b, expected_relocations='-', replacement_relocations='-',
        note='Normalize closed payload callback frame and boolean return lifetime', insert_after='',
        insert_after_relocations='', omit='false') for i, a, b in PATCHES]


def fitting_forms():
    for combined, product, record, success in itertools.product((False, True), repeat=4):
        body = BASE
        if combined:
            body = body.replace('if (payload[0x18] & 0x40) {\n        if (!failed) {',
                'if ((payload[0x18] & 0x40) && !failed) {').replace(
                '        }\n    }\n    success', '    }\n    success')
        if product:
            body = body.replace('    s32 value;', '    s32 value;\n    s32 product;').replace(
                '                value = (u32)value', '                product = (u32)value').replace(
                'if (value < payload[0x1B])', 'if (product < payload[0x1B])').replace(
                'payload[0x1B] = value;', 'payload[0x1B] = product;')
        if record:
            body = body.replace('    s32 value;', '    s32 value;\n    u8 *records;').replace(
                '    if (*(s8 *)(actor + 0x2C) > 0)',
                '    records = *(u8 **)(actor + 0x94);\n    if (*(s8 *)(actor + 0x2C) > 0)').replace(
                '*(u8 **)(actor + 0x94) +', 'records +')
        if success:
            body = body.replace('success = !failed;\n    if (failed) {',
                'success = 1;\n    if (failed) {\n        success = 0;')
        yield 'fit-%d%d%d%d' % (combined, product, record, success), body


def lifetime_forms():
    base = dict(fitting_forms())['fit-1110']
    for kind, expression, result in itertools.product(('s32', 's8', 'u8'),
            ('!failed', '(u32)failed < 1', '(u8)failed < 1', '(failed ^ 1)', '(failed == 0)'),
            ('s8', 's32')):
        body = base.replace('s32 success;', kind + ' success;').replace('success = !failed;',
            'success = %s;' % expression).replace('s8 func_15147EB8', result + ' func_15147EB8')
        if result == 's32':
            body = body.replace('return success;', 'return (s8)success;')
        yield 'life-%s-%s-%s' % (kind, str(expression).translate(str.maketrans({' ': '', '(': '', ')': '', '^': 'xor', '<': 'lt', '!': 'not', '=': 'eq'})), result), body


def expression_forms():
    base = dict(fitting_forms())['fit-1110']
    for index, expression in enumerate(('1 - failed', '1 - (u32)failed', 'failed < 1',
            'failed <= 0', '(s8)!failed', '(u32)failed == 0', '(u8)failed == 0')):
        yield 'return-expression-%d' % index, base.replace('success = !failed;', 'success = %s;' % expression)
    for index, expression in enumerate(('failed == 1', '(u8)failed', '(u32)failed != 0')):
        yield 'failure-expression-%d' % index, base.replace('if (failed) {', 'if (%s) {' % expression)
    yield 'scoped-product', base.replace('    s32 product;\n', '').replace(
        '            if (value < *(s16 *)(payload + 0x1C)) {',
        '            if (value < *(s16 *)(payload + 0x1C)) {\n                s32 product;')
    yield 'single-value', base.replace('    s32 product;\n', '').replace(
        'product = (u32)value', 'success = (u32)value').replace('product <', 'success <').replace('= product;', '= success;')
    yield 'three-fade-conditions', base.replace('if ((payload[0x18] & 0x40) && !failed) {\n            value = *(s16 *)(actor + 0x1C);\n            if (value < *(s16 *)(payload + 0x1C)) {',
        'if ((payload[0x18] & 0x40) && !failed && (value = *(s16 *)(actor + 0x1C)) < *(s16 *)(payload + 0x1C)) {').replace(
        '            }\n    }\n    success', '    }\n    success')
    for kind in ('u8', 's32', 'u32'):
        yield 'fit-failed-' + kind, base.replace('s8 failed', kind + ' failed')


def scoped_forms():
    base = dict(expression_forms())['scoped-product']
    for timer_scope, success_scope, result_kind in itertools.product((False, True), (False, True), ('s32', 's8', 'u8')):
        body = base
        if timer_scope:
            body = body.replace('    s32 value;\n', '').replace(
                '            value = *(s16 *)(actor + 0x1C);', '            s32 value = *(s16 *)(actor + 0x1C);')
        if success_scope:
            body = body.replace('    s32 success;\n', '').replace('    success = !failed;',
                '    {\n    %s success = !failed;' % result_kind).replace('    return success;\n}', '    return success;\n    }\n}')
        else:
            body = body.replace('s32 success;', result_kind + ' success;')
        yield 'scope-%d%d-%s' % (timer_scope, success_scope, result_kind), body


def final_forms():
    base = dict(expression_forms())['scoped-product']
    nested = '''    if (failed) {
        selector = payload[0x22];
        if (selector != 0) {
            D_8008A42C[selector](actor);
        }
    }'''
    for name, fragment in (
            ('combined-failure', '''    if (failed && (selector = payload[0x22]) != 0) {
        D_8008A42C[selector](actor);
    }'''),
            ('failure-else-success', '''    if (failed) {
        success = 0;
        selector = payload[0x22];
        if (selector != 0) {
            D_8008A42C[selector](actor);
        }
    } else {
        success = 1;
    }'''),
            ('return-status-condition', '''    if (!success) {
        selector = payload[0x22];
        if (selector != 0) {
            D_8008A42C[selector](actor);
        }
    }''')):
        body = base.replace(nested, fragment)
        if name == 'failure-else-success':
            body = body.replace('    success = !failed;\n', '')
        for local in ('s32', 's8', 'u8'):
            yield name + '-' + local, body.replace('s32 success;', local + ' success;')


def candidates():
    yield 'baseline', BASE
    yield 'selected', SELECTED
    yield from fitting_forms()
    yield from lifetime_forms()
    yield from expression_forms()
    yield from scoped_forms()
    yield from final_forms()
    for kind in ('u8', 's8'):
        yield 'selector-' + kind, BASE.replace('s32 selector;', kind + ' selector;')
    for kind in ('s8', 'u8'):
        yield 'success-' + kind, BASE.replace('s32 success;', kind + ' success;')
    for kind in ('s32', 'u8'):
        yield 'failed-' + kind, BASE.replace('s8 failed', kind + ' failed')
    yield 'direct-index', BASE.replace('    s32 selector;\n', '').replace(
        '    selector = payload[0x20];\n    if (selector != 0)', '    if (payload[0x20] != 0)').replace(
        '    selector = payload[0x21];\n    if (selector != 0', '    if (payload[0x21] != 0').replace(
        '        selector = payload[0x22];\n        if (selector != 0)', '        if (payload[0x22] != 0)').replace(
        'D_8008A3E0[selector]', 'D_8008A3E0[payload[0x20]]').replace(
        'D_8008A3F8[selector]', 'D_8008A3F8[payload[0x21]]').replace(
        'D_8008A42C[selector]', 'D_8008A42C[payload[0x22]]')
    yield 'signed-product', BASE.replace('(u32)value * (u32)*(s16 *)(payload + 0x1E)',
        'value * *(s16 *)(payload + 0x1E)')
    yield 'combined-fade-gate', dict(fitting_forms())['fit-1000']


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
    script = output / 'payload-callback.ld'
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
    output = root / 'conker/build/game-payload-callback-update'
    records = []
    for name, body in candidates():
        meta, _ = compile_candidate(root, output, name, body)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (output / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
