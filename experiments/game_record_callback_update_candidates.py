"""Recover complete callback-driven attachment lifetime and distance gating."""

import argparse
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151D7264, 0x204714, 81
FUNCTION = 'func_151D7264'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_204660/func_151D7264.s")'
DECLARATIONS = '''typedef struct { f32 x, y, z; } CallbackPosition151D7264;
typedef struct {
    u8 *attached;
    u8 selector, flags, padding[2];
    CallbackPosition151D7264 position;
    f32 threshold;
} CallbackRecord151D7264;
typedef struct { u8 padding[0x28]; CallbackRecord151D7264 record; } CallbackOwner151D7264;
extern s32 (*D_8008FCA0[])(u8 *);
f32 func_15143E64(f32 *);
void func_151D77C8(u8 *);
void func_151D7830(u8 *);
'''
SYMBOLS = dict(D_8008FCA0=0x8008FCA0, func_15143E64=0x15143E64,
    func_151D77C8=0x151D77C8, func_151D7830=0x151D7830)
BASE = '''void func_151D7264(u8 *owner) {
    CallbackPosition151D7264 previous;
    CallbackPosition151D7264 delta;
    u8 priorFlag;
    u8 *record;

    previous = *(CallbackPosition151D7264 *)(owner + 0x30);
    priorFlag = owner[0x2D] & 1;
    if (!D_8008FCA0[owner[0x2C]](owner)) {
        *(s16 *)(owner + 0xE) = -1;
        owner[0xD] |= 1;
    } else {
        record = owner + 0x28;
        if (record[5] & 1) {
            if (priorFlag) {
                delta.x = *(f32 *)(record + 8) - previous.x;
                delta.y = *(f32 *)(record + 12) - previous.y;
                delta.z = *(f32 *)(record + 16) - previous.z;
                if (func_15143E64((f32 *)&delta) < *(f32 *)(record + 20)) {
                    if (*(u8 **)record == NULL) {
                        func_151D7830(owner);
                    }
                } else {
                    func_151D77C8(owner);
                }
            } else {
                func_151D77C8(owner);
            }
        } else {
            func_151D77C8(owner);
        }
    }
}'''
def record_fields(body):
    body = body.replace('u8 *record;', 'CallbackRecord151D7264 *record;').replace(
        'record = owner + 0x28;', 'record = (CallbackRecord151D7264 *)(owner + 0x28);').replace(
        'record[5]', 'record->flags').replace('*(u8 **)record', 'record->attached').replace(
        '*(f32 *)(record + 20)', 'record->threshold')
    for offset, axis in zip((8, 12, 16), 'xyz'):
        body = body.replace('*(f32 *)(record + %d)' % offset, 'record->position.' + axis)
    return body


def pointer_first(body, kind):
    body = body.replace('    u8 priorFlag;', '    CallbackPosition151D7264 *point;\n    u8 priorFlag;')
    body = body.replace('    previous =', '    point = &' + kind + ';\n    previous =', 1)
    if kind == 'delta':
        body = body.replace('delta.', 'point->').replace('(f32 *)&delta', '(f32 *)point')
    else:
        body = body.replace('previous =', '*point =').replace('previous.', 'point->')
    return body


def fitted_body():
    body = record_fields(BASE)
    original = ('    CallbackPosition151D7264 previous;\n    CallbackPosition151D7264 delta;\n'
        '    u8 priorFlag;\n    CallbackRecord151D7264 *record;')
    return body.replace(original, '    CallbackRecord151D7264 *record;\n'
        '    CallbackPosition151D7264 previous;\n    u8 priorFlag;\n    CallbackPosition151D7264 delta;')


SELECTED = fitted_body()


def normalize(words):
    if len(words) != WORDS or words[0] != 0x27BDFFC0:
        raise ValueError('wrong complete callback-update extent/frame')
    result = list(words)
    start = 0x78 // 4
    expected = (0x90AF002D, 0x93A8002F, 0x31EE0001, 0x11C00029, 0,
        0x11000023, 0x24A20028, 0xC4440008, 0xC7A60030)
    if tuple(result[start:start + 9]) != expected:
        raise ValueError('stale complete callback predicate block')
    flag_load = (expected[0] & 0xFC1F0000) | (2 << 21) | 5
    # Hoist only the pure record address; move both gates with retargeted branches.
    result[start:start + 9] = (expected[6], flag_load, expected[1], expected[2],
        expected[3] - 1, expected[4], expected[5] - 1, expected[8], expected[7])
    return result


def owner_guards(words):
    derived = normalize(words)
    return [dict(filename='generated_204660', function=FUNCTION, offset='0x%X' % (i * 4),
        expected='0x%08X' % a, replacement='0x%08X' % b,
        expected_relocations='-', replacement_relocations='-',
        note='Normalize closed callback record address flag gates and private coordinate load order',
        insert_after='', insert_after_relocations='', omit='false')
        for i, (a, b) in enumerate(zip(words, derived)) if a != b]


def candidates():
    yield 'selected', SELECTED
    yield 'flag-between-points', BASE.replace('    u8 priorFlag;\n', '').replace(
        '    CallbackPosition151D7264 delta;', '    u8 priorFlag;\n    CallbackPosition151D7264 delta;')
    yield 'delta-first', BASE.replace('    CallbackPosition151D7264 previous;\n', '').replace(
        '    CallbackPosition151D7264 delta;', '    CallbackPosition151D7264 delta;\n    CallbackPosition151D7264 previous;')
    yield 'volatile-owner', BASE.replace('u8 *owner)', 'u8 * volatile owner)')
    yield 'combined-flags', BASE.replace('''        if (record[5] & 1) {
            if (priorFlag) {''', '''        if ((record[5] & 1) && priorFlag) {''').replace(
        '''            } else {
                func_151D77C8(owner);
            }
        } else {''', '''        } else {''')
    yield 'early-failure', BASE.replace('''        owner[0xD] |= 1;
    } else {''', '''        owner[0xD] |= 1;
        return;
    }
    {''')
    for typed in (False, True):
        body = record_fields(BASE) if typed else BASE
        yield 'fields-%d' % typed, body
        for kind in ('delta', 'previous'):
            yield 'fields-%d-early-%s' % (typed, kind), pointer_first(body, kind)
    typed = record_fields(BASE)
    array = typed.replace('CallbackPosition151D7264 delta;', 'f32 delta[3];').replace(
        '(f32 *)&delta', 'delta')
    for index, axis in enumerate('xyz'):
        array = array.replace('delta.' + axis, 'delta[%d]' % index)
    for name, body in (('typed', typed), ('array', array)):
        yield name + '-delta-array', body
        yield name + '-volatile-record-fields', body.replace('CallbackRecord151D7264 *record;',
            'volatile CallbackRecord151D7264 *record;')
        yield name + '-named-distance', body.replace('    u8 priorFlag;', '    f32 distance;\n    u8 priorFlag;').replace(
            'if (func_15143E64(' + ('delta' if name == 'array' else '(f32 *)&delta') + ') < record->threshold)',
            'distance = func_15143E64(' + ('delta' if name == 'array' else '(f32 *)&delta') + ');\n                if (distance < record->threshold)')
        yield name + '-flag-first', body.replace('    u8 priorFlag;\n', '').replace(
            '    CallbackPosition151D7264 previous;', '    u8 priorFlag;\n    CallbackPosition151D7264 previous;')
        yield name + '-byte-array-flag', body.replace('u8 priorFlag;', 'u8 priorFlag[1];').replace(
            'priorFlag =', 'priorFlag[0] =').replace('if (priorFlag)', 'if (priorFlag[0])')
        yield name + '-wide-flag', body.replace('u8 priorFlag;', 's32 priorFlag;')
    declarations = ('CallbackPosition151D7264 previous;', 'CallbackPosition151D7264 delta;',
        'u8 priorFlag;', 'CallbackRecord151D7264 *record;')
    original = '\n'.join('    ' + declaration for declaration in declarations)
    for order in itertools.permutations(range(4)):
        yield 'locals-' + ''.join(map(str, order)), typed.replace(original,
            '\n'.join('    ' + declarations[i] for i in order))
    fitted = fitted_body()
    yield 'fitted', fitted
    yield 'fitted-typed-owner', fitted.replace('u8 *owner)', 'CallbackOwner151D7264 *owner)').replace(
        '(owner + 0x30)', '&owner->record.position').replace('owner[0x2D]', 'owner->record.flags').replace(
        'owner[0x2C]', 'owner->record.selector').replace(
        'record = (CallbackRecord151D7264 *)(owner + 0x28);', 'record = &owner->record;').replace(
        '(owner + 0xE)', '((u8 *)owner + 0xE)').replace('owner[0xD]', '((u8 *)owner)[0xD]').replace(
        '(owner);', '((u8 *)owner);').replace(']](owner)', ']]((u8 *)owner)').replace(
        '](owner)', ']((u8 *)owner)')
    yield 'fitted-integer-address', fitted.replace('(owner + 0x28)', '((u32)owner + 0x28)')
    yield 'fitted-address-union', fitted.replace('record = (CallbackRecord151D7264 *)(owner + 0x28);',
        'record = &((CallbackOwner151D7264 *)owner)->record;')
    yield 'fitted-volatile-owner-fields', fitted.replace(
        'record = (CallbackRecord151D7264 *)(owner + 0x28);',
        'record = &((volatile CallbackOwner151D7264 *)owner)->record;').replace(
        'CallbackRecord151D7264 *record;', 'volatile CallbackRecord151D7264 *record;')
    yield 'negative-live-old-flag', BASE.replace('if (priorFlag)', 'if (owner[0x2D] & 1)')
    yield 'negative-reversed-distance', BASE.replace(' < *(f32 *)(record + 20)', ' >= *(f32 *)(record + 20)')
    yield 'negative-equal-distance', BASE.replace(' < *(f32 *)(record + 20)', ' <= *(f32 *)(record + 20)')
    yield 'negative-signed-selector', BASE.replace('D_8008FCA0[owner[0x2C]]', 'D_8008FCA0[*(s8 *)(owner + 0x2C)]')
    yield 'negative-overwrite-failure-flags', BASE.replace('owner[0xD] |= 1', 'owner[0xD] = 1')
    yield 'negative-live-position', BASE.replace(' - previous.x', ' - *(f32 *)(owner + 0x30)').replace(
        ' - previous.y', ' - *(f32 *)(owner + 0x34)').replace(' - previous.z', ' - *(f32 *)(owner + 0x38)')
    yield 'negative-eager-record', BASE.replace('    u8 *record;', '    u8 *record;\n    u8 *attached;').replace(
        '    previous =', '    attached = *(u8 **)(owner + 0x28);\n    previous =', 1).replace(
        'if (*(u8 **)record == NULL)', 'if (attached == NULL)')


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
    script = out / 'callback-update.ld'
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
    parser.add_argument('--form', choices=[name for name, _ in candidates()])
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-record-callback-update'
    records = []
    for name, body in candidates():
        if args.form and name != args.form:
            continue
        for profile in PROFILES if args.profiles else ('o2g3',):
            record, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(record)
            print(record['name'], record['body_words'], hex(record['frame']), record['differences'], flush=True)
    (out / ('profiles.json' if args.profiles else 'measurements.json')).write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
