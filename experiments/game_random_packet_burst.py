"""Recover the fourteen-argument random debris burst against frozen retail words."""
import argparse
import hashlib
import json
import itertools
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_table_debris_match as previous
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests import table_debris_match_checkpoint as checkpoint

SCREEN_BUILD = 'conker/build/game-random-packet-burst'
BUILD = 'conker/build/game-random-packet-burst-match'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19E040', 'func_15171200', 0x15171200, 0x19E6B0, 256
RANDOM, LOOKUP, SUBMIT = 0x150ADA20, 0x1518C900, 0x15168BE4
PATHS = dict(previous.PATHS, retail_rom='conker/conker.us.bin',
    random_burst_caller_owner='conker/src/game/generated_197120.c',
    random_burst_constants='conker/asm/data/24B770.rodata.s',
    integer_rng_original='conker/asm/nonmatchings/game_DAE50/func_150ADA20.s')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    retail_rom='f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
    random_burst_caller_owner='b434d517213dfe8ba93ca299675b9b15188dd252f39ba91c1d275e78f8643c26',
    random_burst_constants='4738048ab7bf9d07ebda55dae6facf353589405d9ca2b2870c61d0d9759a8fd0',
    integer_rng_original='64b478aa7a866ba3793982326254c86aad25a0e378e364497ea1a32b4eb2f50a')
build = previous.build
POOL_ANCHOR = previous.POOL_ANCHOR

INITIAL = '''/* Emit randomized debris; kind stays word-wide for lookup, byte-wide in packets.
 * Fixed fields are initialized once; reserved packet bytes remain untouched. */
void func_15171200(s32 count, s32 kind, f32 x, f32 y, f32 z,
                  f32 verticalBase, f32 minimumScale, f32 maximumScale,
                  f32 spread, s32 variant, s32 lifetime, f32 coefficient,
                  u8 flags, s32 context) {
    DebrisPacket19E040 packet;
    f32 positionScale;
    f32 scaleRange;
    f32 verticalSpread;
    f32 thirdScale;
    s32 index;

    positionScale = spread * 0.0000152587890625f;
    scaleRange = maximumScale - minimumScale;
    verticalSpread = verticalBase * 0.000006103515625f;
    packet.rotation[0] = 0.0f;
    packet.rotation[1] = 0.0f;
    packet.rotation[2] = 0.0f;
    packet.coefficient[0] = coefficient * -0.75f;
    packet.coefficient[1] = coefficient;
    packet.coefficient[2] = -0.2f;
    packet.mode = 2;
    packet.alpha = 255;
    packet.zero56 = 0;
    packet.zero57 = 0;
    packet.zero58 = 0;
    packet.kind = kind;
    packet.variant = variant;
    packet.control5C = 1;
    packet.control5D = 1;
    packet.lifetime = lifetime;
    index = 0;
    if (count > 0) {
        verticalBase *= 0.8f;
        do {
            packet.position[0] = (f32)(func_150ADA20() >> 16) * positionScale + x;
            packet.position[1] = (f32)(func_150ADA20() >> 16) * positionScale + y;
            packet.position[2] = (f32)(func_150ADA20() >> 16) * positionScale + z;
            packet.asset = func_1518C900(kind);
            packet.velocity[0] = (f32)(func_150ADA20() >> 16) * 0.0002288818359375f;
            packet.velocity[1] = (f32)((u32)func_150ADA20() & 65535) * verticalSpread + verticalBase;
            packet.velocity[2] = (f32)(func_150ADA20() >> 16) * 0.0002288818359375f;
            packet.spin[0] = (f32)(func_150ADA20() >> 16) * 0.000152587890625f;
            packet.spin[1] = (f32)(func_150ADA20() >> 16) * 0.000152587890625f;
            packet.spin[2] = (f32)(func_150ADA20() >> 16) * 0.000152587890625f;
            packet.scale[0] = ((f32)((u32)func_150ADA20() & 65535) * 0.0000152587890625f) * scaleRange + minimumScale;
            packet.scale[1] = ((f32)((u32)func_150ADA20() & 65535) * 0.0000152587890625f) * scaleRange + minimumScale;
            thirdScale = ((f32)((u32)func_150ADA20() & 65535) * 0.0000152587890625f) * scaleRange + minimumScale;
            packet.duration = (u32)(((packet.scale[0] + packet.scale[1]) + thirdScale) * 6.666666666666667f + 20.0f);
            packet.scale[2] = thirdScale;
            func_15168BE4(&packet, flags, context);
            index += 1;
        } while (index != count);
    }
}
'''
ORDERED = INITIAL.replace('    verticalSpread = verticalBase * 0.000006103515625f;\n', '').replace(
    '    index = 0;', '    verticalSpread = verticalBase * 0.000006103515625f;\n    index = 0;').replace(
    '6.666666666666667f', '6.666667f')
SCREEN_LAYOUT = ORDERED.replace('    s32 index;\n', '').replace(
    '    DebrisPacket19E040 packet;', '    s32 index;\n    DebrisPacket19E040 packet;')


def forms():
    for first in (False, True):
        body = SCREEN_LAYOUT if first else ORDERED
        for number in (1, 2, 3):
            candidate = body.replace('    s32 index;', '    s32 index;\n' + ''.join(
                '    u32 draw%d;\n' % i for i in range(number)))
            start = candidate.index('            packet.scale[0]')
            prefix, tail = candidate[:start], candidate[start:]
            for i in range(number):
                marker = '            ' + ('packet.scale[%d]' % i if i < 2 else 'thirdScale') + ' ='
                tail = tail.replace(marker, '            draw%d = (u32)func_150ADA20() & 65535;\n' % i + marker, 1)
                at = tail.index(marker)
                tail = tail[:at] + tail[at:].replace('(u32)func_150ADA20() & 65535', 'draw%d' % i, 1)
            candidate = prefix + tail
            yield ('index-first' if first else 'packet-first') + '-draws-%d' % number, candidate
            yield ('index-first' if first else 'packet-first') + '-draws-%d-vertical-last' % number, candidate.replace(
                '    f32 verticalSpread;\n', '').replace('    f32 thirdScale;', '    f32 thirdScale;\n    f32 verticalSpread;')


def ordered_forms():
    body = dict(forms())['packet-first-draws-2']
    body = body.replace('    packet.coefficient[2] = -0.2f;\n', '').replace('    packet.variant = variant;\n', '').replace(
        '    packet.lifetime = lifetime;\n', '').replace('    index = 0;',
        '    index = 0;\n    packet.coefficient[2] = -0.2f;\n    packet.lifetime = lifetime;\n    packet.variant = variant;')
    for external in (False, True):
        candidate = body
        if external:
            candidate = 'extern f32 D_800A6FB0, D_800A6FB4, D_800A6FB8, D_800A6FBC;\n\n' + candidate
            for old, new in (('-0.2f', 'D_800A6FB0'), ('0.000006103515625f', 'D_800A6FB4'),
                    ('0.8f', 'D_800A6FB8'), ('6.666667f', 'D_800A6FBC')):
                candidate = candidate.replace(old, new)
        candidate = candidate.replace('    u32 draw0;\n    u32 draw1;\n', '').replace(
            '    f32 thirdScale;', '    f32 thirdScale;\n    u32 draw0;\n    u32 draw1;')
        for first in (False, True):
            c = candidate
            if first:
                c = c.replace('    s32 index;\n', '').replace('    DebrisPacket19E040 packet;',
                    '    s32 index;\n    DebrisPacket19E040 packet;')
            for order in (False, True):
                d = c if not order else c.replace('    f32 positionScale;\n    f32 scaleRange;',
                    '    f32 scaleRange;\n    f32 positionScale;')
                yield ('extern' if external else 'literal') + ('-index' if first else '-packet') + ('-range-first' if order else ''), d


def lifetime_forms():
    body = dict(ordered_forms())['literal-index']
    for old, new in (('positionScale', 'spread'), ('scaleRange', 'maximumScale')):
        candidate = body.replace('    f32 ' + old + ';\n', '').replace(old, new)
        yield 'parameter-' + new, candidate
    body = body.replace('    u32 draw0;\n    u32 draw1;\n', '    f32 sample0;\n    f32 sample1;\n')
    for index in range(2):
        body = body.replace('draw%d = (u32)func_150ADA20() & 65535' % index,
            'sample%d = (f32)((u32)func_150ADA20() & 65535)' % index).replace('(f32)(draw%d)' % index, 'sample%d' % index)
    for order in (False, True):
        c = body.replace('    f32 verticalSpread;\n', '').replace('    f32 sample1;', '    f32 sample1;\n    f32 verticalSpread;') if order else body
        yield 'float-samples' + ('-vertical-last' if order else ''), c
        yield 'float-samples-early-scale' + ('-vertical-last' if order else ''), c.replace(
            '    positionScale = spread * 0.0000152587890625f;\n', '').replace(
            '    index = 0;', '    positionScale = spread * 0.0000152587890625f;\n    index = 0;')


def scale_forms():
    for parameter in ('spread', 'maximumScale'):
        initial = dict(lifetime_forms())['parameter-' + parameter]
        initial = initial.replace('    packet.coefficient[2] = -0.2f;\n', '').replace(
            '    verticalSpread =', '    packet.coefficient[2] = -0.2f;\n    verticalSpread =', 1)
        for placement in ('before-packet', 'after-packet', 'last'):
            body = initial.replace('    DebrisPacket19E040 packet;',
                ('    f32 scaledVerticalBase;\n' if placement == 'before-packet' else '') +
                '    DebrisPacket19E040 packet;' + ('\n    f32 scaledVerticalBase;' if placement == 'after-packet' else ''))
            if placement == 'last':
                body = body.replace('    u32 draw1;', '    u32 draw1;\n    f32 scaledVerticalBase;')
            body = body.replace('    index = 0;', '    scaledVerticalBase = verticalBase * 0.8f;\n    index = 0;').replace(
                '        verticalBase *= 0.8f;', '        verticalBase = scaledVerticalBase;')
            yield parameter + '-scaled-' + placement, body
            yield parameter + '-scaled-' + placement + '-vertical-last', body.replace('    f32 verticalSpread;\n', '').replace(
                '    u32 draw1;', '    u32 draw1;\n    f32 verticalSpread;')


def draw_forms():
    for parameter in ('spread', 'maximumScale'):
        initial = dict(lifetime_forms())['parameter-' + parameter]
        initial = initial.replace('    packet.coefficient[2] = -0.2f;\n', '').replace(
            '    verticalSpread =', '    packet.coefficient[2] = -0.2f;\n    verticalSpread =', 1)
        for count in (3, 4):
            body = initial.replace('    u32 draw1;', '    u32 draw1;\n    u32 draw2;')
            body = body.replace('            thirdScale = ((f32)((u32)func_150ADA20() & 65535)',
                '            draw2 = (u32)func_150ADA20() & 65535;\n            thirdScale = ((f32)(draw2)')
            if count == 4:
                body = body.replace('    u32 draw2;', '    u32 draw2;\n    u32 verticalDraw;').replace(
                    '            packet.velocity[1] = (f32)((u32)func_150ADA20() & 65535)',
                    '            verticalDraw = (u32)func_150ADA20() & 65535;\n            packet.velocity[1] = (f32)verticalDraw')
            yield parameter + '-draws-%d' % count, body
            yield parameter + '-draws-%d-vertical-last' % count, body.replace('    f32 verticalSpread;\n', '').replace(
                '    u32 ' + ('verticalDraw' if count == 4 else 'draw2') + ';',
                '    u32 ' + ('verticalDraw' if count == 4 else 'draw2') + ';\n    f32 verticalSpread;')


def pool_forms():
    for parameter in ('spread', 'maximumScale'):
        initial = dict(draw_forms())[parameter + '-draws-4-vertical-last']
        for constants in (('0.8f',), ('0.8f', '6.666667f'),
                ('-0.2f', '0.000006103515625f', '0.8f', '6.666667f')):
            d = {'-0.2f': 'D_800A6FB0', '0.000006103515625f': 'D_800A6FB4',
                '0.8f': 'D_800A6FB8', '6.666667f': 'D_800A6FBC'}
            body = 'extern f32 ' + ', '.join(d[k] for k in constants) + ';\n\n' + initial
            for k in constants:
                body = body.replace(k, d[k])
            yield parameter + '-pool-%d' % len(constants), body


def hoist_forms():
    initial = dict(draw_forms())['spread-draws-4-vertical-last']
    initial = initial.replace('        verticalBase *= 0.8f;\n', '').replace(
        '    index = 0;', '    verticalBase *= 0.8f;\n    index = 0;')
    for pos in ('same', 'early-range', 'late-range', 'early-coefficients'):
        body = initial
        if pos == 'early-range':
            body = body.replace('    scaleRange = maximumScale - minimumScale;\n', '').replace(
                '    spread =', '    scaleRange = maximumScale - minimumScale;\n    spread =', 1)
        elif pos == 'late-range':
            body = body.replace('    scaleRange = maximumScale - minimumScale;\n', '').replace(
                '    index = 0;', '    scaleRange = maximumScale - minimumScale;\n    index = 0;')
        elif pos == 'early-coefficients':
            body = body.replace('    packet.coefficient[0] = coefficient * -0.75f;\n', '').replace(
                '    spread =', '    packet.coefficient[0] = coefficient * -0.75f;\n    spread =', 1)
        yield 'hoist-' + pos, body


def schedule_forms():
    initial = dict(hoist_forms())['hoist-early-range'].replace(
        '(packet.scale[0] + packet.scale[1])', '(packet.scale[1] + packet.scale[0])')
    for before in ('packet.rotation[0]', 'packet.coefficient[0]', 'packet.mode', 'packet.coefficient[2]'):
        body = initial.replace('    packet.lifetime = lifetime;\n', '').replace(
            '    ' + before + ' =', '    packet.lifetime = lifetime;\n    ' + before + ' =', 1)
        yield 'life-before-' + before.replace('.', '-').replace('[', '').replace(']', ''), body
        yield 'life-variant-before-' + before.replace('.', '-').replace('[', '').replace(']', ''), body.replace(
            '    packet.variant = variant;\n', '').replace('    packet.lifetime = lifetime;',
                '    packet.lifetime = lifetime;\n    packet.variant = variant;')


def opening_forms():
    initial = dict(schedule_forms())['life-before-packet-mode']
    for before in ('packet.rotation[0]', 'packet.coefficient[0]', 'packet.coefficient[1]'):
        body = initial.replace('    packet.coefficient[2] = -0.2f;\n', '').replace(
            '    ' + before + ' =', '    packet.coefficient[2] = -0.2f;\n    ' + before + ' =', 1)
        for move in ('same', 'late-spread', 'early-life'):
            c = body
            if move == 'late-spread':
                c = c.replace('    spread = spread * 0.0000152587890625f;\n', '').replace(
                    '    verticalSpread =', '    spread = spread * 0.0000152587890625f;\n    verticalSpread =', 1)
            elif move == 'early-life':
                c = c.replace('    packet.lifetime = lifetime;\n', '').replace(
                    '    scaleRange =', '    packet.lifetime = lifetime;\n    scaleRange =', 1)
            yield 'coeff2-' + before.replace('.', '-').replace('[', '').replace(']', '') + '-' + move, c


def byte_forms():
    initial = dict(opening_forms())['coeff2-packet-coefficient1-late-spread']
    lines = dict(variant='    packet.variant = variant;\n', c='    packet.control5C = 1;\n', d='    packet.control5D = 1;\n')
    for order in itertools.permutations(lines):
        body = initial
        for line in lines.values():
            body = body.replace(line, '')
        for at in ('packet.kind', 'packet.coefficient[2]'):
            yield 'bytes-' + '-'.join(order) + '-' + at.replace('.', '-').replace('[', '').replace(']', ''), body.replace(
                '    ' + at + ' =', ''.join(lines[k] for k in order) + '    ' + at + ' =', 1)


SELECTED = dict(opening_forms())['coeff2-packet-coefficient1-late-spread'].replace(
    '    packet.variant = variant;\n', '').replace('    packet.kind = kind;',
        '    packet.variant = variant;\n    packet.kind = kind;')
SELECTED = SELECTED.replace('    f32 verticalSpread;\n\n\n', '    f32 verticalSpread;\n\n')
RAW_SHA256 = '0209fc91d9d4d484ddb791c7e415c6cd550ba3ea973d39d0d87eb5b4524e17ce'
POOL = bytes.fromhex('3dcccccd3e6b851f3db851ecbe4ccccd36cccccd3f4ccccd40d5555600000000')
RELOCATIONS = {at: [('R_MIPS_HI16' if at in (108, 120, 136, 760) else 'R_MIPS_LO16', '.rodata')]
    for at in (108, 112, 120, 124, 136, 152, 760, 780)}
RELOCATIONS.update({at: [('R_MIPS_26', 'func_150ADA20')]
    for at in (288, 320, 352, 396, 424, 480, 508, 536, 564, 592, 648, 704)})
RELOCATIONS.update({388: [('R_MIPS_26', 'func_1518C900')], 944: [('R_MIPS_26', 'func_15168BE4')]})


def freeze(root, out):
    from unittest.mock import patch
    with patch.multiple(previous.previous, PATHS=PATHS, BASELINE=BASELINE):
        previous.previous.freeze(root, out)


def recovered_owner(before, selected=None):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_15171200() {\n    return 0;\n}':
        raise ValueError('Unknown random-burst predecessor')
    return before[:lo] + (SELECTED if selected is None else selected).rstrip() + before[hi:]


def measure(root, out, label='selected', selected=None):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out,
        recovered_owner((out / 'before-edge_wrapper_owner').read_text(), selected), label)
    text, functions, rel = parse_object(obj)
    if functions[FUNCTION]['size'] <= WORDS * 4:
        padded = out / (label + '-padded.s')
        padded.write_text(emit_padded_assembly(obj, root / PATHS['edge_wrapper_original'], filename=OWNER,
            word_patches_path=out / 'before-guards', rodata_symbol=POOL_ANCHOR))
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded.with_suffix('.o')), str(padded)],
            check=True, capture_output=True)
        link_obj = padded.with_suffix('.o')
    else:
        link_obj = obj
    data, functions = build.link_owner(root, out, link_obj, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>%dI' % WORDS, (root / 'conker/conker.us.bin').read_bytes(), ROM))
    text, functions, rel = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    row = dict(label=label, words=len(words), frame=(-words[0]) & 65535,
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        diagnostics=diagnostics, pool=sections(obj)['.rodata'][1].hex(),
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        stack_pointers=[(i * 4, w >> 16 & 31, w & 65535) for i, w in enumerate(words)
            if w >> 26 == 9 and w >> 21 & 31 == 29 and w >> 16 & 31 != 29],
        relocations={at - f['value']: rows for at, rows in rel.items() if f['value'] <= at < f['value'] + f['size']},
        different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def checked_object(obj):
    text, functions, rel = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    relative = {at - f['value']: rows for at, rows in rel.items() if f['value'] <= at < f['value'] + f['size']}
    pools = {n: d for n, (_, d) in sections(obj).items()
        if n.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and d}
    if f['size'] != 1024 or hashlib.sha256(raw).hexdigest() != RAW_SHA256 or relative != RELOCATIONS or pools != {'.rodata': POOL}:
        raise ValueError('Unknown random-burst compiler words, bindings or pool')
    return raw, relative


def qualify(root, out):
    obj, words, row = measure(root, out, 'qualified')
    checked_object(obj)
    if (row['words'], row['frame'], row['differences'], row['diagnostics'], row['stack_pointers']) != (256, 224, 0, '', [(276, 21, 124)]):
        raise ValueError('Random burst is not a direct match')
    if (',' + FUNCTION + ',').encode() in (out / 'before-guards').read_bytes():
        raise ValueError('Random burst must not acquire instruction guards')
    if (out / 'before-retail_rom').read_bytes()[0x24BA64:0x24BA80] != POOL[:28]:
        raise ValueError('Random-burst pool differs from original literal addresses')
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, out / 'qualified-padded.o', words, row


def slot_expected_image(before, rom):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']:
        raise ValueError('Unknown random-burst ELF predecessor')
    row = next(r for r in symbol_rows(before) if r[1] == FUNCTION)
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError('Unknown random-burst predecessor extent')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, 1024)
    result[at:at + 1024] = rom[ROM:ROM + 1024]
    struct.pack_into('>I', result, row[0] + 8, 1024)
    return bytes(result)


def expected_inputs(root, out):
    return dict(elf=slot_expected_image((out / 'before-elf').read_bytes(), (out / 'before-retail_rom').read_bytes()),
        edge_wrapper_owner=recovered_owner((out / 'before-edge_wrapper_owner').read_text()).encode())


def prelink_prediction(root, out):
    from unittest.mock import patch
    with patch.multiple(previous, qualify=qualify, PATHS=PATHS, BASELINE=BASELINE,
            slot_expected_image=slot_expected_image, serialize_symbols=lambda data: data):
        row = previous.prelink_prediction(root, out)
    predicted = {k: hashlib.sha256(v).hexdigest() for k, v in expected_inputs(root, out).items()}
    path = out / 'initial-prediction.json'
    if not path.exists():
        if {k: hashlib.sha256((root / p).read_bytes()).hexdigest() for k, p in PATHS.items()} != BASELINE:
            raise ValueError('Initial prediction must precede installation')
        path.write_text(json.dumps(predicted, indent=2) + '\n')
    if json.loads(path.read_text()) != predicted:
        raise ValueError('Changed random-burst initial prediction')
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--prelink', action='store_true')
    args = parser.parse_args()
    row = prelink_prediction(args.root, args.root / BUILD) if args.prelink else qualify(args.root, args.root / BUILD)[3]
    print(json.dumps(row, indent=2))


if __name__ == '__main__':
    main()
