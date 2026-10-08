"""Recover fractional position sampling and live signed ring-state updates."""

import argparse
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151D7A38, 0x204EE8, 166
FUNCTION = 'func_151D7A38'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_204660/func_151D7A38.s")'
DECLARATIONS = '''typedef struct {
    f32 x, y, z;
} SamplingPosition151D7A38;

typedef struct {
    u8 *actor;
    SamplingPosition151D7A38 position;
    f32 time;
    f32 progress;
} SamplingPayload151D7A38;

extern f32 D_800BE9A4;
void func_151D8718(f32 *, f32 *, f32);
'''
SYMBOLS = {'D_800BE9A4': 0x800BE9A4, 'func_151D8718': 0x151D8718}
BASE = '''s32 func_151D7A38(u8 *owner) {
    SamplingPayload151D7A38 *payload;
    u8 *records;
    SamplingPosition151D7A38 current;
    SamplingPosition151D7A38 point;
    f32 fraction;
    f32 time;
    f32 timeStep;
    f32 xStep;
    f32 yStep;
    f32 zStep;
    u8 *record;

    payload = *(SamplingPayload151D7A38 **)(owner + 0x98);
    records = *(u8 **)(owner + 0x94);
    if ((payload->actor[0x2D] & 1) == 0) {
        return 0;
    }
    current = *(SamplingPosition151D7A38 *)(payload->actor + 0x30);
    *(SamplingPosition151D7A38 *)(owner + 0x10) = current;
    payload->progress += 0.25f * D_800BE9A4;
    if (payload->progress > 1.0f) {
        fraction = 1.0f / payload->progress;
        point = payload->position;
        time = payload->time + D_800BE9A4;
        timeStep = time * fraction;
        xStep = (current.x - payload->position.x) * fraction;
        yStep = (current.y - payload->position.y) * fraction;
        zStep = (current.z - payload->position.z) * fraction;
        do {
            record = records + *(s8 *)(owner + 0x2E) * 0x1C;
            *(SamplingPosition151D7A38 *)record = point;
            *(f32 *)(record + 0xC) = 0.0f;
            *(f32 *)(record + 0x10) = 0.0f;
            record[0x14] = 0;
            *(f32 *)(record + 0x18) = 0.0f;
            func_151D8718((f32 *)record, (f32 *)(record + 0xC), time);
            owner[0x2E]++;
            time -= timeStep;
            if (*(s8 *)(owner + 0x2E) == owner[0x25]) {
                owner[0x2E] = 0;
            }
            owner[0x2C]++;
            if (*(s8 *)(owner + 0x2D) == *(s8 *)(owner + 0x2E)) {
                owner[0x2D]++;
                if (*(s8 *)(owner + 0x2D) == owner[0x25]) {
                    owner[0x2D] = 0;
                }
                owner[0x2C]--;
            }
            point.x += xStep;
            point.y += yStep;
            point.z += zStep;
            payload->progress -= 1.0f;
        } while (payload->progress > 1.0f);
        payload->position = point;
        payload->time = time;
    }
    return 1;
}'''


def signed_updates(body):
    return body.replace('owner[0x2E]++;', 'owner[0x2E] = *(s8 *)(owner + 0x2E) + 1;').replace(
        'owner[0x2C]++;', 'owner[0x2C] = *(s8 *)(owner + 0x2C) + 1;').replace('owner[0x2D]++;',
        'owner[0x2D] = *(s8 *)(owner + 0x2D) + 1;').replace('owner[0x2C]--;', 'owner[0x2C] = *(s8 *)(owner + 0x2C) - 1;')


def staged(body, components=0, pointers=()):
    if components:
        body = body.replace('    f32 fraction;', '    f32 xDelta;\n    f32 yDelta;\n    f32 zDelta;\n    f32 fraction;')
        body = body.replace('        timeStep = time * fraction;',
            '        xDelta = current.x - payload->position.x;\n        yDelta = current.y - payload->position.y;\n        zDelta = current.z - payload->position.z;\n        timeStep = time * fraction;')
        for axis in 'xyz':
            body = body.replace('(current.' + axis + ' - payload->position.' + axis + ')', axis + 'Delta')
    for pointer in pointers:
        if pointer == 'actor':
            body = body.replace('    u8 *records;', '    u8 *records;\n    u8 *actor;').replace(
                '    if ((payload->actor[0x2D]', '    actor = payload->actor;\n    if ((actor[0x2D]').replace('payload->actor + 0x30', 'actor + 0x30')
        elif pointer == 'clock':
            body = body.replace('    f32 fraction;', '    f32 *clock;\n    f32 fraction;').replace(
                '    payload->progress +=', '    clock = &D_800BE9A4;\n    payload->progress +=').replace(
                '0.25f * D_800BE9A4', '0.25f * *clock').replace('payload->time + D_800BE9A4', 'payload->time + *clock')
        elif pointer == 'old':
            body = body.replace('    u8 *record;', '    u8 *record;\n    SamplingPosition151D7A38 *previous;').replace(
                '        point = payload->position;', '        previous = &payload->position;\n        point = *previous;').replace(
                'payload->position.', 'previous->').replace('        payload->position = point;', '        *previous = point;')
        elif pointer == 'point':
            body = body.replace('    u8 *record;', '    u8 *record;\n    SamplingPosition151D7A38 *output;').replace(
                '        point = payload->position;', '        output = &point;\n        point = payload->position;').replace(
                '        previous = &payload->position;\n        point = *previous;', '        output = &point;\n        previous = &payload->position;\n        point = *previous;').replace(
                '*(SamplingPosition151D7A38 *)record = point;', '*(SamplingPosition151D7A38 *)record = *output;')
    return body


def fitted_base():
    body = staged(signed_updates(BASE), 1, ('old', 'point'))
    body = body.replace('        output = &point;\n', '').replace('    current =', '    output = &point;\n    current =', 1)
    body = body.replace('    SamplingPosition151D7A38 point;\n', '').replace(
        '    f32 zStep;', '    SamplingPosition151D7A38 point;\n    f32 zStep;')
    return body


SELECTED = fitted_base().replace('        point = *previous;\n        time = payload->time + D_800BE9A4;',
    '        time = payload->time + D_800BE9A4;\n        point = *previous;')


def candidates():
    yield 'selected', SELECTED
    yield 'natural', BASE
    yield 'position-first', BASE.replace('    SamplingPayload151D7A38 *payload;\n    u8 *records;\n', '').replace(
        '    f32 fraction;', '    SamplingPayload151D7A38 *payload;\n    u8 *records;\n    f32 fraction;')
    yield 'point-first', BASE.replace('    SamplingPosition151D7A38 current;\n    SamplingPosition151D7A38 point;',
        '    SamplingPosition151D7A38 point;\n    SamplingPosition151D7A38 current;')
    yield 'time-last', BASE.replace('    f32 time;\n', '').replace('    u8 *record;', '    f32 time;\n    u8 *record;')
    yield 'explicit-byte-increments', signed_updates(BASE)
    yield 'signed-byte-increments', BASE.replace('owner[0x2E]++;', '(*(s8 *)(owner + 0x2E))++;').replace(
        'owner[0x2C]++;', '(*(s8 *)(owner + 0x2C))++;').replace('owner[0x2D]++;',
        '(*(s8 *)(owner + 0x2D))++;').replace('owner[0x2C]--;', '(*(s8 *)(owner + 0x2C))--;')
    for component in (0, 1):
        for pointers in ((), ('actor',), ('clock',), ('old',), ('point',),
                         ('actor', 'clock'), ('old', 'point'), ('actor', 'clock', 'old', 'point')):
            yield 'staged-%d-%s' % (component, '-'.join(pointers) or 'none'), staged(signed_updates(BASE), component, pointers)
    ordered = staged(signed_updates(BASE), 1, ('old', 'point'))
    ordered = ordered.replace('        output = &point;\n', '').replace(
        '    current =', '    output = &point;\n    current =', 1)
    for field in ('xDelta', 'yDelta', 'zDelta', 'fraction', 'time', 'timeStep', 'xStep', 'yStep', 'zStep', 'record'):
        decl = '    u8 *record;' if field == 'record' else '    f32 ' + field + ';'
        moved = ordered.replace('    SamplingPosition151D7A38 point;\n', '').replace(
            decl, '    SamplingPosition151D7A38 point;\n' + decl)
        yield 'point-before-' + field, moved
    yield 'early-point-pointer', ordered
    fitted = fitted_base()
    yield 'fitted-base', fitted
    yield 'fitted-count-first', fitted.replace('*(s8 *)(owner + 0x2E) == owner[0x25]',
        'owner[0x25] == *(s8 *)(owner + 0x2E)').replace('*(s8 *)(owner + 0x2D) == owner[0x25]',
        'owner[0x25] == *(s8 *)(owner + 0x2D)')
    yield 'fitted-time-before-copy', fitted.replace('        point = *previous;\n        time = payload->time + D_800BE9A4;',
        '        time = payload->time + D_800BE9A4;\n        point = *previous;')
    yield 'fitted-while', fitted.replace('        do {', '        while (payload->progress > 1.0f) {').replace(
        '        } while (payload->progress > 1.0f);', '        }')
    for early in (False, True):
        current = fitted.replace('    u8 *record;', '    SamplingPosition151D7A38 *currentPosition;\n    u8 *record;').replace(
            '    current =', '    currentPosition = &current;\n    current =', 1).replace(
            '= current;', '= *currentPosition;').replace('current.', 'currentPosition->')
        if early:
            current = current.replace('    output = &point;\n', '').replace('    payload =', '    output = &point;\n    payload =', 1)
        yield 'fitted-current-pointer-%d' % early, current
    yield 'fitted-old-style', fitted.replace('s32 func_151D7A38(u8 *owner)', 's32 func_151D7A38(owner)\nu8 *owner;')
    for pointers in ((), ('actor',), ('clock',), ('old',), ('point',), ('actor', 'old'), ('actor', 'point'), ('clock', 'old'), ('clock', 'point'), ('old', 'point')):
        tuned = staged(signed_updates(BASE), 1, pointers)
        tuned = tuned.replace('    SamplingPosition151D7A38 point;\n', '').replace(
            '    f32 zStep;', '    SamplingPosition151D7A38 point;\n    f32 zStep;')
        if 'point' in pointers:
            tuned = tuned.replace('        output = &point;\n', '').replace('    current =', '    output = &point;\n    current =', 1)
        assignment = '        point = *previous;' if 'old' in pointers else '        point = payload->position;'
        tuned = tuned.replace(assignment + '\n        time = payload->time + D_800BE9A4;',
            '        time = payload->time + D_800BE9A4;\n' + assignment)
        yield 'time-copy-%s' % ('-'.join(pointers) or 'none'), tuned
    time_first = fitted.replace('        point = *previous;\n        time = payload->time + D_800BE9A4;',
        '        time = payload->time + D_800BE9A4;\n        point = *previous;')
    yield 'time-copy-index-local', time_first.replace('    u8 *record;', '    s32 index;\n    u8 *record;').replace(
        '            record = records + *(s8 *)(owner + 0x2E) * 0x1C;',
        '            index = *(s8 *)(owner + 0x2E);\n            record = records + index * 0x1C;')
    yield 'time-copy-count-first', time_first.replace('*(s8 *)(owner + 0x2E) == owner[0x25]',
        'owner[0x25] == *(s8 *)(owner + 0x2E)').replace('*(s8 *)(owner + 0x2D) == owner[0x25]',
        'owner[0x25] == *(s8 *)(owner + 0x2D)')
    yield 'negative-unsigned-current', BASE.replace('records + *(s8 *)(owner + 0x2E)', 'records + owner[0x2E]')
    yield 'negative-signed-count', BASE.replace('== owner[0x25]', '== *(s8 *)(owner + 0x25)')
    yield 'negative-live-buffer', BASE.replace('record = records +', 'record = *(u8 **)(owner + 0x94) +')
    yield 'negative-threshold', BASE.replace('progress > 1.0f', 'progress >= 1.0f')
    yield 'negative-quarter', BASE.replace('0.25f', '0.5f')
    yield 'negative-velocity-offset', BASE.replace('(f32 *)(record + 0xC), time', '(f32 *)(record + 0x10), time')
    yield 'negative-cached-current', SELECTED.replace('    u8 *record;', '    s32 index;\n    u8 *record;').replace(
        '            record = records + *(s8 *)(owner + 0x2E) * 0x1C;',
        '            index = *(s8 *)(owner + 0x2E);\n            record = records + index * 0x1C;').replace(
        'owner[0x2E] = *(s8 *)(owner + 0x2E) + 1;', 'owner[0x2E] = index + 1;')
    yield 'negative-live-payload', SELECTED.replace('            owner[0x2E] =',
        '            payload = *(SamplingPayload151D7A38 **)(owner + 0x98);\n            owner[0x2E] =', 1)
    yield 'negative-cached-progress', SELECTED.replace('    f32 fraction;', '    f32 counter;\n    f32 fraction;').replace(
        '        do {', '        counter = payload->progress;\n        do {').replace(
        '            payload->progress -= 1.0f;', '            counter -= 1.0f;\n            payload->progress = counter;').replace(
        '} while (payload->progress > 1.0f);', '} while (counter > 1.0f);')
    yield 'negative-no-state-decrement', SELECTED.replace('                owner[0x2C] = *(s8 *)(owner + 0x2C) - 1;\n', '')
    yield 'negative-uncleared-field', SELECTED.replace('            *(f32 *)(record + 0x18) = 0.0f;\n', '')


def owner_guards():
    pairs = (
        (0x74, 0x8C590034, 0x8C480034), (0x80, 0xAC790004, 0xAC680004),
        (0x94, 0x8C690004, 0x8C6B0004), (0x98, 0xAE090014, 0xAE0B0014),
        (0xEC, 0x8C4B0004, 0x8C4D0004), (0xF8, 0xAE8B0004, 0xAE8D0004),
        (0x130, 0xAFA20074, 0xAFA20070), (0x148, 0x820C002E, 0x820E002E),
        (0x154, 0x01920019, 0x01D20019), (0x158, 0x00006812, 0x00007812),
        (0x15C, 0x01B32021, 0x01F32021), (0x164, 0x8E980004, 0x8E880004),
        (0x16C, 0xAC980004, 0xAC880004), (0x190, 0x8219002E, 0x820A002E),
        (0x198, 0x92090025, 0x920B0025), (0x19C, 0x27280001, 0x25490001),
        (0x1A0, 0xA208002E, 0xA209002E), (0x1AC, 0x54490004, 0x55620004),
        (0x1B0, 0x820A002C, 0x820C002C), (0x1BC, 0x820A002C, 0x820C002C),
        (0x1C4, 0x254B0001, 0x258D0001), (0x1CC, 0xA20B002C, 0xA20D002C),
        (0x1D0, 0x246C0001, 0x246E0001), (0x1D4, 0xA20C002D, 0xA20E002D),
        (0x1D8, 0x820D002D, 0x8218002D), (0x1E0, 0x55AF0003, 0x55F80003),
        (0x1E4, 0x820E002C, 0x8219002C), (0x1EC, 0x820E002C, 0x8219002C),
        (0x1F0, 0x25D8FFFF, 0x2728FFFF), (0x1F4, 0xA218002C, 0xA208002C),
        (0x234, 0x4503FFC5, 0x4501FFC4), (0x238, 0x820C002E, 0x00000000),
        (0x23C, 0x8FB90074, 0x8FAA0070), (0x244, 0xAF210000, 0xAD410000),
        (0x248, 0x8E890004, 0x8E8B0004), (0x24C, 0xAF290004, 0xAD4B0004),
        (0x254, 0xAF210008, 0xAD410008),
    )
    return [dict(filename='generated_204660', function=FUNCTION, offset='0x%X' % offset,
        expected='0x%08X' % before, replacement='0x%08X' % after,
        expected_relocations='-', replacement_relocations='-',
        note='Normalize closed sampling copy registers captured position spill and loop delay schedule',
        insert_after='', insert_after_relocations='', omit='false') for offset, before, after in pairs]


def normalize(words):
    result = list(words)
    assert len(result) == WORDS and result[0] == 0x27BDFF38
    for row in owner_guards():
        index = int(row['offset'], 0) // 4
        assert result[index] == int(row['expected'], 0), ('stale sampling schedule', index)
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
    script = out / 'record-ring-sampling.ld'
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
    out = root / 'conker/build/game-record-ring-sampling'
    forms = [('profile-' + p, SELECTED, p) for p in PROFILES] if args.profiles else [
        (name, body, 'o2g3') for name, body in candidates() if args.candidate is None or name == args.candidate]
    records = []
    for name, body, profile in forms:
        record, _ = compile_candidate(root, out, name, body, profile)
        records.append(record)
        print(name, record['body_words'], hex(record['frame']), record['differences'], flush=True)
    filename = 'profiles.json' if args.profiles else args.candidate + '-measurement.json' if args.candidate else 'measurements.json'
    (out / filename).write_text(json.dumps(records, indent=2) + '\n')
    print(out.relative_to(root) / filename)


if __name__ == '__main__':
    main()
