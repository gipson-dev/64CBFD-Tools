"""Screen real table/cursor lifetimes for the complete actor-state tick."""

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path

from tools.experiments import game_actor_state_tick_candidates as prior


BUILD = prior.BUILD + '/lifetimes'
TABLES = ('groups', 'latches', 'actions', 'states', 'elapsed', 'timers',
          'cooldowns', 'timeouts', 'events', 'groupCounts', 'scores')
CURSORS = {'timer': 'timers', 'score': 'scores', 'cooldown': 'cooldowns',
           'timeout': 'timeouts', 'elapsedTimer': 'elapsed', 'event': 'events',
           'action': 'actions', 'state': 'states', 'latch': 'latches'}


def replace(body, before, after):
    if body.count(before) != 1:
        raise ValueError('Changed actor-tick source anchor: ' + before)
    return body.replace(before, after)


def indexed_cursors(body):
    for cursor, table in CURSORS.items():
        body = replace(body, '%s = (s32 *)((u8 *)%s + offset);' % (cursor, table),
                       '%s = %s + slot;' % (cursor, table))
    return replace(body, 'group = *(s32 *)((u8 *)groups + offset);', 'group = groups[slot];')


def inline_cursors(body):
    for cursor, table in CURSORS.items():
        body = replace(body, '    s32 *' + cursor + ';\n', '')
        body = replace(body, '                %s = (s32 *)((u8 *)%s + offset);\n' % (cursor, table), '')
        body = re.sub(r'\*' + cursor + r'\b', table + '[slot]', body)
    body = replace(body, '    u8 *eventByte;\n', '')
    body = replace(body, '                eventByte = D_800E0BB8 + slot;\n', '')
    return body.replace('*eventByte', 'D_800E0BB8[slot]')


def byte_tables(body):
    for name in TABLES:
        body = replace(body, '    s32 *' + name + ';', '    u8 *' + name + ';')
        body = replace(body, '    ' + name + ' = (s32 *)', '    ' + name + ' = (u8 *)')
        body = body.replace('(u8 *)' + name + ' + offset', name + ' + offset')
    body = replace(body, 'counter = groupCounts + group;', 'counter = (s32 *)(groupCounts + group * 4);')
    body = replace(body, 'counter = groupCounts + owner;', 'counter = (s32 *)(groupCounts + owner * 4);')
    body = replace(body, 'owner = groups[value];', 'owner = *(s32 *)(groups + value * 4);')
    return replace(body, 'scores[drawIndex] / 60', '*(s32 *)(scores + drawIndex * 4) / 60')


def aggregate_tables(body):
    typedef = 'typedef struct {\n' + ''.join('    s32 *' + n + ';\n' for n in TABLES) + '} ActorTickTablesB3020;\n\n'
    for name in TABLES:
        body = replace(body, '    s32 *' + name + ';\n', '')
        body = re.sub(r'\b' + name + r'\b', 'tables.' + name, body)
    body = replace(body, '    u32 changed;', '    ActorTickTablesB3020 tables;\n    u32 changed;')
    return typedef + body


def for_loop(body):
    body = replace(body, '    if (count > 0) {\n        offset = 0;\n        do {',
        '    offset = 0;\n    for (; slot < count; slot++, band++, status++, reset++, offset += 4) {')
    return replace(body, '            slot++;\n            band++;\n            status++;\n'
        '            reset++;\n            offset += 4;\n        } while (slot != count);\n    }', '    }')


def scalar_cleanup(body, remove_limit=False):
    for declaration in ('    s32 drawIndex;\n', '    u8 *drawActor;\n', '    s32 halfWidth;\n',
                        '    s32 *counter;\n', '    s32 owner;\n', '    u8 *context;\n'):
        body = replace(body, declaration, '')
    body = body.replace('drawIndex', 'slot').replace('drawActor', 'actor').replace('halfWidth', 'value')
    body = replace(body, '                        counter = groupCounts + group;\n'
        '                        *counter -= 1;', '                        groupCounts[group] -= 1;')
    body = replace(body, '                            owner = groups[value];\n'
        '                            if (group != owner) {\n'
        '                                counter = groupCounts + owner;\n'
        '                                *counter += 1;',
        '                            if (group != groups[value]) {\n'
        '                                groupCounts[groups[value]] += 1;')
    body = replace(body, '    context = (u8 *)D_800D23B0;\n', '')
    body = re.sub(r'\bcontext\b', '(u8 *)D_800D23B0', body)
    if remove_limit:
        body = replace(body, '    s16 limit;\n', '')
        body = replace(body, '                    limit = D_800872C4[D_800E0BD0];\n', '')
        body = replace(body, 'limit != -1 && *elapsedTimer >= limit',
                       'D_800872C4[D_800E0BD0] != -1 && *elapsedTimer >= D_800872C4[D_800E0BD0]')
    return body


def forms():
    baseline = prior.BASELINE
    globals_body = baseline
    word_body = baseline
    for name in TABLES:
        assignment = next(line for line in baseline.splitlines() if line.startswith('    ' + name + ' ='))
        displacement = int(re.search(r'0x([0-9A-F]+)', assignment)[1], 16)
        globals_body = replace(globals_body, assignment,
            '    %s = (s32 *)(D_800D23B0 + 0x%X);' % (name, displacement))
        word_body = replace(word_body, assignment,
            '    %s = (s32 *)context + 0x%X;' % (name, displacement // 4))
    eager = globals_body
    for name, displacement in (('reset', 0x1C), ('status', 0x39C), ('band', 0x9C)):
        eager = replace(eager, '        %s = (s32 *)(context + 0x%X);\n' % (name, displacement), '')
    eager = replace(eager, '    if (count > 0) {',
        '    reset = (s32 *)(D_800D23B0 + 0x1C);\n'
        '    status = (s32 *)(D_800D23B0 + 0x39C);\n'
        '    band = (s32 *)(D_800D23B0 + 0x9C);\n'
        '    if (count > 0) {')
    eager_inline = inline_cursors(eager)
    reused = eager_inline.replace('    s32 drawIndex;\n', '').replace('    u8 *drawActor;\n', '')
    reused = reused.replace('drawIndex', 'slot').replace('drawActor', 'actor')
    registered = globals_body
    for cursor in CURSORS:
        registered = replace(registered, '    s32 *' + cursor + ';', '    register s32 *' + cursor + ';')
    integer = globals_body.replace('    u8 *context;', '    s32 context;')
    integer = integer.replace('context = (u8 *)D_800D23B0;', 'context = D_800D23B0;')
    actor_address = replace(reused, 'otherActor = D_800CC2D0 + value * 0x32C - 0x658;',
        'otherActor = value * 0x32C - 0x658 + D_800CC2D0;')
    reload_timer = replace(reused, '                        previousTimer = -1;\n'
        '                        value = timers[slot];',
        '                        previousTimer = -1;\n'
        '                        /* Read back through the retained byte cursor. */\n'
        '                        value = *(s32 *)((u8 *)timers + offset);')
    address_reload = replace(reload_timer, 'otherActor = D_800CC2D0 + value * 0x32C - 0x658;',
        'otherActor = value * 0x32C - 0x658 + D_800CC2D0;')
    return [('indexed-cursors', indexed_cursors(baseline)),
            ('inline-cursors', inline_cursors(baseline)),
            ('byte-table-bases', byte_tables(baseline)),
            ('aggregate-table-bases', aggregate_tables(baseline)),
            ('aggregate-inline-cursors', aggregate_tables(inline_cursors(baseline))),
            ('global-table-bases', globals_body),
            ('global-inline-cursors', inline_cursors(globals_body)),
            ('word-table-bases', word_body),
            ('word-inline-cursors', inline_cursors(word_body)),
            ('eager-all-bases', eager),
            ('eager-inline-cursors', eager_inline),
            ('eager-reused-cursors', reused),
            ('eager-reused-word-action', reused.replace('    u8 actorAction;', '    s32 actorAction;')),
            ('global-register-cursors', registered),
            ('global-register-scalars', registered.replace('    s32 slot;', '    register s32 slot;')
                .replace('    s32 offset;', '    register s32 offset;')),
            ('global-integer-context', integer),
            ('global-integer-inline', inline_cursors(integer)),
            ('for-captured-bases', for_loop(eager)),
            ('for-inline-cursors', for_loop(eager_inline)),
            ('for-reused-cursors', for_loop(reused)),
            ('reused-actor-address', actor_address),
            ('reused-timer-reload', reload_timer),
            ('reused-address-and-reload', address_reload),
            ('captured-scalars-cleanup', scalar_cleanup(globals_body)),
            ('captured-inline-limit', scalar_cleanup(globals_body, True)),
            ('eager-scalars-cleanup', scalar_cleanup(eager)),
            ('eager-inline-limit', scalar_cleanup(eager, True))]


SELECTED = dict(forms())['reused-timer-reload']
RAW_SHA256 = '78444a63df0e30b12773ae5adc217ab832ea09b1b9e9296da8c6e6a16eece5c9'


def opening(obj):
    """Read emitted pre-loop address definitions/homes, not a source assertion."""
    raw, _ = prior.payload(obj)
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    branches = [i for i, w in enumerate(words) if w >> 26 in (1, 4, 5, 6, 7, 20, 21, 22, 23)]
    if not branches:
        raise ValueError('Actor tick has no count branch')
    limit = branches[0] + 2
    offsets = {0xE64, 0x35C, 0x31C, 0x19C, 0x21C, 0x29C, 0x25C, 0x41C, 0x3DC, 0xDDC, 0x1574}
    definitions, stores = {}, []
    for index, word in enumerate(words[:limit]):
        op, rs, rt, imm = word >> 26, word >> 21 & 31, word >> 16 & 31, word & 65535
        if op == 9 and imm in offsets:
            definitions[rt] = (imm, index)
        elif op == 43 and rs == 29 and rt in definitions:
            offset, origin = definitions[rt]
            stores.append(dict(table_offset=offset, home=imm, address_word=origin, store_word=index))
        elif op in (9, 15, 32, 33, 35, 36, 37):
            definitions.pop(rt, None)
    return dict(first_count_branch_word=branches[0], eager_table_homes=stores)


def compile_candidate(root, output, name, body):
    row, words = prior.compile_candidate(root, output, name, body)
    row['opening'] = opening(output / (name + '.o'))
    row['source_sha256'] = hashlib.sha256(body.encode()).hexdigest()
    (output / (name + '-receipt.json')).write_text(json.dumps(row, indent=2) + '\n')
    return row, words


def qualify_owner(root, output):
    from tools.experiments.game_graphics_task_submit import same_functions
    from tools.tests.game_owner_pool import normalized_pools

    values = prior.freeze(root, output)
    before = values['conker/src/game/generated_B3020.c'].decode()
    lo, hi = prior.function_span(before, prior.FUNCTION)
    declarations = prior.DECLARATIONS.split('\n', 1)[1].replace(
        's32 func_1508CAD8(s32, s32, s32, s32, s32, s32);', 's32 func_1508CAD8();')
    unit = before[:lo] + declarations + '\n' + SELECTED + before[hi:]
    rows = []
    for label, normal in (('primary', False), ('normal', True)):
        a, da = prior.compile_unit(root, output, 'before-' + label, before, normal)
        b, db = prior.compile_unit(root, output, 'after-' + label, unit, normal)
        c, dc = prior.compile_unit(root, output, 'isolated-' + label,
                                  prior.DECLARATIONS + '\n' + SELECTED, normal)
        if da or db or dc or same_functions(a, b, (prior.FUNCTION,)) != 72:
            raise ValueError('Actor-tick lifetime changed another raw owner function')
        if normalized_pools(a) != normalized_pools(b) or prior.payload(b) != prior.payload(c):
            raise ValueError('Actor-tick lifetime changed pools/isolated words/bindings')
        raw, _ = prior.payload(b)
        if hashlib.sha256(raw).hexdigest() != RAW_SHA256:
            raise ValueError('Actor-tick lifetime raw source changed')
        rows.append(dict(profile=label, preserved_neighbors=72, pools_unchanged=True,
                         isolated_words_and_bindings_equal=True, words=678, frame=288,
                         eager_table_homes=11, installed=False))
    for name, data in values.items():
        if (root / name).read_bytes() != data:
            raise ValueError('Actor-tick lifetime modified production: ' + name)
    (output / 'owner-receipt.json').write_text(json.dumps(rows, indent=2) + '\n')
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--names', nargs='*')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD
    prior.freeze(root, output)
    candidates = forms()
    if args.names:
        if not set(args.names) <= dict(candidates).keys():
            parser.error('unknown lifetime candidate')
        candidates = [(n, b) for n, b in candidates if n in args.names]
    for name, body in candidates:
        row, _ = compile_candidate(root, output, name, body)
        print(json.dumps({k: v for k, v in row.items() if k != 'differences'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
