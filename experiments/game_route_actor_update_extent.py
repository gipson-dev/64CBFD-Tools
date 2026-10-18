"""Diagnose route-caller extent by real calls; shape alignment is not normalization."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

from tools.experiments import game_route_actor_update_fit as prior
from tools.experiments.game_actor_command_finalizer_fitting import instruction_shape

source = prior.source
BUILD = 'conker/build/game-route-actor-update-extent'
SELECTED_NAME = 'rank-cursor-current'
RAW_SHA = '423ef8706eab06a130de88369c7b23596c1bf9e62f3da6caa915a7a6a0600320'
BINDING_SHA = '76dd7ba3dc3e16f662369c343b107ae67f362ae608efa54848615712a3e3721a'


def calls(words):
    return [(i, 0x10000000 | (word & 0x3FFFFFF) << 2) for i, word in enumerate(words) if word >> 26 == 3]


def shape(word):
    result = instruction_shape(word)
    op, rs, rt = word >> 26, word >> 21 & 31, word >> 16 & 31
    if rs == 29 and op in (9, 32, 33, 35, 36, 37, 40, 41, 43, 49, 53, 57, 61) and not (op == 9 and rt == 29):
        return result[:1] + ('private-home',) + result[2:]
    return result


def disassemble(out, name, words):
    binary = out / (name + '.bin')
    binary.write_bytes(struct.pack('>%dI' % len(words), *words))
    result = subprocess.run(['mips-linux-gnu-objdump', '-D', '-b', 'binary', '-m', 'mips:4000',
        '-EB', '--adjust-vma=' + hex(source.ENTRY), str(binary)], capture_output=True, text=True, check=True)
    (out / (name + '.txt')).write_text(result.stdout)
    return result.stdout


def call_blocks(truth, actual):
    a, b = calls(truth), calls(actual)
    if [target for _, target in a] != [target for _, target in b]:
        raise ValueError('Cannot anchor changed static helper-call sequence')
    result = []
    left = right = 0
    for ordinal, (end_a, end_b, target) in enumerate(
            [(i + 2, j + 2, target) for (i, target), (j, _) in zip(a, b)] + [(len(truth), len(actual), None)]):
        result.append(dict(block=ordinal, retail_start=left, raw_start=right,
            retail_words=end_a - left, raw_words=end_b - right,
            missing_words=(end_a - left) - (end_b - right), call=hex(target) if target else None))
        left, right = end_a, end_b
    return result


def analyze(root, out):
    values = source.freeze(root, out)
    obj = root / prior.BUILD / 'qualified-bound.o'
    prior.checked(obj)
    image, functions = source.prior.link_owner(root, out, obj, source.OWNER)
    f = functions[source.FUNCTION]
    actual = list(struct.unpack_from('>%dI' % (f['size'] // 4), image, f['value']))
    truth = list(struct.unpack_from('>604I', values['conker/conker.us.bin'], source.ROM))
    disassemble(out, 'retail', truth)
    disassemble(out, 'baseline589', actual)
    blocks, changes = call_blocks(truth, actual), []
    for row in blocks:
        ordinal = row['block']
        left, right = row['retail_start'], row['raw_start']
        end_a, end_b = left + row['retail_words'], right + row['raw_words']
        matcher = difflib.SequenceMatcher(None, list(map(shape, truth[left:end_a])),
            list(map(shape, actual[right:end_b])), autojunk=False)
        for tag, i, j, k, l in matcher.get_opcodes():
            if tag != 'equal':
                changes.append(dict(block=ordinal, tag=tag, retail=(left + i, left + j), raw=(right + k, right + l),
                    retail_words=['%08X' % v for v in truth[left + i:left + j]],
                    raw_words=['%08X' % v for v in actual[right + k:right + l]]))
    if sum(row['missing_words'] for row in blocks) != 15:
        raise ValueError('Changed pinned route-caller extent')
    result = dict(retail_words=len(truth), raw_words=len(actual), blocks=blocks,
        diagnostic_shape_differences=changes, shape_omits_registers_and_private_offsets=True,
        alignment_is_not_matching_or_a_normalizer=True, installed=False)
    (out / 'blocks.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def conversion_forms():
    original = prior.selected()
    assignments = [('            *(s16 *)(D_800D2104[actor[0x13F]] + %d) = (s32)%s;' % (offset, name), name)
        for offset, name in ((8, 'D_800D239C'), (10, 'D_800D23A0'), (12, 'D_800D23A4'))]
    for label, declaration, value in (
            ('scalar-conversion', '    s32 converted;\n', 'converted'),
            ('cell-conversion', '    struct { s32 value; } converted;\n', 'converted.value'),
            ('array-conversion', '    s32 converted[1];\n', 'converted[0]')):
        body = prior.replace_once(original, '    f32 gain;\n', '    f32 gain;\n' + declaration)
        for old, global_name in assignments:
            body = prior.replace_once(body, old,
                '            %s = (s32)%s;\n' % (value, global_name) +
                old.replace('(s32)' + global_name, value))
        yield label, body
    body = original
    for old, name in assignments:
        body = prior.replace_once(body, old, old.replace('(s32)' + name, name))
    yield 'narrow-float-to-short-control', body


def spill_forms():
    original = prior.selected()
    for label, old, dtype, member in (('rank-id-word', 'temporary', 's8', 'id'),
                                      ('rank-index-word', 'i', 's32', 'index'),
                                      ('loop-flag-word', 'again', 's32', 'flag')):
        declaration = '    union { volatile s32 word; %s %s; } conversionScratch;\n' % (dtype, member)
        body = prior.replace_once(original, '    %s %s;\n' % (dtype, old), declaration)
        body = re.sub(r'\b' + old + r'\b', 'conversionScratch.' + member, body)
        for offset, name in ((8, 'D_800D239C'), (10, 'D_800D23A0'), (12, 'D_800D23A4')):
            marker = '            *(s16 *)(D_800D2104[actor[0x13F]] + %d) = (s32)%s;' % (offset, name)
            body = prior.replace_once(body, marker,
                '            conversionScratch.word = (s32)%s;\n' % name +
                marker.replace('(s32)' + name, 'conversionScratch.word'))
        yield label, body
    body = dict(conversion_forms())['scalar-conversion'].replace('    s32 converted;', '    volatile s32 converted;')
    yield 'standalone-volatile-word-control', body


def ranking_forms():
    original = prior.selected()
    start = original.index('        do {\n            again = 1;')
    end = original.index('        for (i = 0; i < D_800D2398; i++) {', start)
    for name, next_index in (('local-next', 'next'), ('argument-next', 'recordIndex'),
                              ('active-next', 'active')):
        body = original
        if next_index == 'next':
            body = prior.replace_once(body, '    s32 i;\n', '    s32 i;\n    s32 next;\n')
        loop = '''        do {
            again = 1;
            cursor = (u8 *)scores;
            for (i = 0, NEXT = 1; i < (s32)recordOffset; i = NEXT, NEXT++, cursor += 4) {
                valueX = *(f32 *)cursor;
                if (valueX < *(f32 *)(cursor + 4)) {
                    temporary = order[NEXT];
                    previousError = scores[NEXT];
                    refresh = order[i];
                    order[i] = temporary;
                    *(f32 *)cursor = previousError;
                    again = 0;
                    scores[NEXT] = valueX;
                    order[NEXT] = refresh;
                }
            }
        } while (!again);
'''.replace('NEXT', next_index)
        a = body.index('        do {\n            again = 1;')
        b = body.index('        for (i = 0; i < D_800D2398; i++) {', a)
        yield 'rank-' + name, body[:a] + loop + body[b:]
    loop = original[start:end]
    loop = prior.replace_once(loop, '                    temporary = order[i + 1];',
        '                    valueX = scores[i];\n                    temporary = order[i + 1];')
    loop = prior.replace_once(loop, '                    valueX = scores[i + 1];',
        '                    previousError = scores[i + 1];\n                    refresh = order[i];')
    loop = prior.replace_once(loop, '                    order[i + 1] = order[i];\n                    order[i] = temporary;\n                    scores[i + 1] = scores[i];\n                    scores[i] = valueX;\n                    again = 0;',
        '                    order[i] = temporary;\n                    scores[i] = previousError;\n                    again = 0;\n                    scores[i + 1] = valueX;\n                    order[i + 1] = refresh;')
    yield 'rank-explicit-swap-order', original[:start] + loop + original[end:]


def cursor_forms():
    original = prior.selected()
    start = original.index('        do {\n            again = 1;')
    end = original.index('        for (i = 0; i < D_800D2398; i++) {', start)
    for name, independent, assign_first in (
            ('cursor-current', False, False), ('cursor-current-last', False, True),
            ('cursor-next', True, False), ('cursor-next-last', True, True)):
        next_index = 'recordIndex' if independent else 'i + 1'
        initialize = 'i = 0, recordIndex = 1' if independent else 'i = 0'
        advance = 'i = recordIndex, recordIndex++, cursor += 4' if independent else 'i++, cursor += 4'
        loop = '''        do {
            again = 1;
            cursor = (u8 *)scores;
            for (INITIALIZE; i < (s32)recordOffset; ADVANCE) {
                valueX = *(f32 *)cursor;
                if (valueX < *(f32 *)(cursor + 4)) {
                    temporary = order[NEXT];
                    order[NEXT] = order[i];
                    order[i] = temporary;
                    *(f32 *)cursor = scores[NEXT];
                    scores[NEXT] = valueX;
                    again = 0;
                }
            }
        } while (!again);
'''.replace('INITIALIZE', initialize).replace('ADVANCE', advance).replace('NEXT', next_index)
        if assign_first:
            loop = prior.replace_once(loop, '                    order[i] = temporary;\n', '')
            loop = prior.replace_once(loop, '                    again = 0;',
                '                    again = 0;\n                    order[i] = temporary;')
        yield 'rank-' + name, original[:start] + loop + original[end:]


def typed_forms():
    original = dict(cursor_forms())['rank-cursor-current']
    loop_start = original.index('        do {\n            again = 1;')
    prefix, loop = original[:loop_start], original[loop_start:]
    loop = loop.replace('cursor = (u8 *)scores', 'scoreCursor = scores')
    loop = loop.replace('cursor += 4', 'scoreCursor++')
    loop = loop.replace('*(f32 *)cursor', 'scoreCursor[0]')
    loop = loop.replace('*(f32 *)(cursor + 4)', 'scoreCursor[1]')
    for name, bank_cursor in (('separate', 'cursor'), ('record', 'record'), ('actor', 'actor')):
        head = prior.replace_once(prefix, '    u8 *cursor;\n',
            ('    u8 *cursor;\n' if bank_cursor == 'cursor' else '') + '    f32 *scoreCursor;\n')
        at = head.index('    if (recordOffset == 0) {\n')
        head = head[:at] + re.sub(r'\bcursor\b', bank_cursor, head[at:])
        yield 'rank-typed-' + name, head + loop


GROUPS = dict(conversions=conversion_forms, spills=spill_forms, ranking=ranking_forms,
              cursors=cursor_forms, typed=typed_forms)


def selected():
    return dict(cursor_forms())[SELECTED_NAME]


def check_payload(raw, bindings):
    binding_sha = hashlib.sha256(json.dumps(bindings, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if len(raw) != 2376 or hashlib.sha256(raw).hexdigest() != RAW_SHA or binding_sha != BINDING_SHA:
        raise ValueError('Changed complete ranking-cursor words or bindings')


def checked(obj):
    text, functions, relocations = source.parse_object(obj)
    f = functions[source.FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    bindings = {at - f['value']: value for at, value in relocations.items()
                if f['value'] <= at < f['value'] + f['size']}
    check_payload(raw, bindings)
    return raw, bindings


def qualify(root, out):
    values = source.freeze(root, out)
    baseline, diagnostics = source.prior.compile_profile(root, out,
        values['conker/src/game/generated_B3020.c'].decode(), 'owner-before')
    if diagnostics:
        raise ValueError('Unexpected ranking-cursor baseline diagnostics')
    obj, words, row = source.measure(root, out, 'qualified-cursor', selected(), baseline)
    checked(obj)
    if (row['words'], row['frame'], row['differences'], row['diagnostics']) != (594, 456, 481, ''):
        raise ValueError('Changed ranking-cursor qualification shape')
    truth = list(struct.unpack_from('>604I', values['conker/conker.us.bin'], source.ROM))
    if words[:15] != truth[:15] or words[-11:] != truth[-11:]:
        raise ValueError('Changed recovered frame/save layout')
    row.update(call_anchored_blocks=call_blocks(truth, words), first15_words_exact=True,
        last11_words_exact=True, frame_restored=True, saved_register_layout_restored=True,
        extent_restored=False, missing_words=10)
    (out / 'qualified-cursor.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def screen(root, out, group='conversions'):
    values = source.freeze(root, out)
    before = values['conker/src/game/generated_B3020.c'].decode()
    baseline, diagnostics = source.prior.compile_profile(root, out, before, 'owner-before')
    if diagnostics:
        raise ValueError('Unexpected extent baseline diagnostics')
    rows = []
    for name, body in GROUPS[group]():
        _, words, row = source.measure(root, out, name, body, baseline)
        truth = list(struct.unpack_from('>604I', values['conker/conker.us.bin'], source.ROM))
        row['call_anchored_blocks'] = call_blocks(truth, words)
        row['first15_words_exact'] = words[:15] == truth[:15]
        row['last11_words_exact'] = words[-11:] == truth[-11:]
        row['narrowed_C_domain_control_only'] = name == 'narrow-float-to-short-control'
        row['volatile_member_not_original_qualifier_claim'] = group == 'spills'
        rows.append(row)
        print(json.dumps({key: row[key] for key in ('name', 'words', 'frame', 'differences', 'raw_sha256', 'diagnostics', 'neighbors')}), flush=True)
    receipt = dict(conversions='conversion', spills='spill', ranking='ranking',
                   cursors='cursor', typed='typed')[group] + '-screens.json'
    (out / receipt).write_text(json.dumps(rows, indent=2) + '\n')
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    for name in GROUPS:
        mode.add_argument('--' + name, dest='group', action='store_const', const=name)
    mode.add_argument('--qualify', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.qualify:
        print(json.dumps(qualify(root, root / BUILD)[2], indent=2))
    elif args.group:
        screen(root, root / BUILD, args.group)
    else:
        value = analyze(root, root / BUILD)
        print(json.dumps({k: v for k, v in value.items() if k != 'diagnostic_shape_differences'}, indent=2))
