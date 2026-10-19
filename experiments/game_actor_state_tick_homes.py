"""Recover measured actor-state tick homes using real declaration permutations."""

import argparse
import json
import re
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_state_tick_lifetimes as prior
from tools.experiments import game_matrix_route_layout_candidates as debug


BUILD = prior.BUILD + '/homes'
FUNCTION = prior.prior.FUNCTION
TARGET_HOMES = dict(changed=0x100, previousTimer=0xF8, active=0xEC, seen=0xE8, count=0xE4,
    groups=0xDC, latches=0xD8, actions=0xD4, states=0xCC, elapsed=0xC8, timers=0xC4,
    cooldowns=0xC0, timeouts=0xBC, events=0xB8, groupCounts=0xB0, scores=0xAC,
    idle=0xAB, reset=0x84, status=0x60, band=0x5C)


def declarations(body):
    start = body.index('{\n') + 2
    end = body.index('\n\n', start)
    rows = body[start:end].splitlines(keepends=True)
    result = {}
    for row in rows:
        match = re.fullmatch(r'    (?:s32|u32|s16|u16|s8|u8)\s+\**(\w+);\n?', row)
        if match is None or match[1] in result:
            raise ValueError('Unexpected actor-tick declaration: ' + row)
        result[match[1]] = row.rstrip('\n') + '\n'
    return start, end, result


def ordered(body, order):
    start, end, rows = declarations(body)
    if len(order) != len(rows) or set(order) != set(rows):
        raise ValueError('Actor-tick declaration permutation added/lost a real local')
    return body[:start] + ''.join(rows[n] for n in order).rstrip('\n') + body[end:]


def restore_spilled_cursors(body, indexed=False):
    cursors = {'timer': 'timers', 'cooldown': 'cooldowns', 'state': 'states',
               'event': 'events', 'action': 'actions'}
    _, end, rows = declarations(body)
    additions = ''.join('    s32 *' + n + ';\n' for n in cursors) + '    u8 *eventByte;'
    body = body[:end] + '\n' + additions + body[end:]
    for cursor, table in cursors.items():
        body = body.replace(table + '[slot]', '*' + cursor)
    body = body.replace('D_800E0BB8[slot]', '*eventByte')
    assignments = ''.join('                %s = %s;\n' % (cursor,
        table + ' + slot' if indexed else '(s32 *)((u8 *)' + table + ' + offset)')
        for cursor, table in cursors.items())
    assignments += '                eventByte = D_800E0BB8 + slot;\n'
    body = prior.replace(body, '                idle = 1;', assignments + '                idle = 1;')
    if not indexed:
        body = prior.replace(body, '                        *timer = 0;\n'
            '                        previousTimer = -1;',
            '                        timers[slot] = 0;\n                        previousTimer = -1;')
    return body


def compact_dead_scalars(body):
    body = prior.replace(body, '    s32 halfWidth;\n', '').replace('halfWidth', 'value')
    body = prior.replace(body, '    s32 *counter;\n', '')
    body = prior.replace(body, '                        counter = groupCounts + group;\n'
        '                        *counter -= 1;', '                        groupCounts[group] -= 1;')
    return prior.replace(body, '                                counter = groupCounts + owner;\n'
        '                                *counter += 1;', '                                groupCounts[owner] += 1;')


def compact_limit(body):
    body = prior.replace(body, '    s32 halfWidth;\n', '').replace('halfWidth', 'value')
    body = prior.replace(body, '    s16 limit;\n', '')
    body = prior.replace(body, '                    limit = D_800872C4[D_800E0BD0];\n', '')
    return prior.replace(body, 'limit != -1 && elapsed[slot] >= limit',
        'D_800872C4[D_800E0BD0] != -1 && elapsed[slot] >= D_800872C4[D_800E0BD0]')


def indexed_outputs(body):
    _, end, _ = declarations(body)
    head, tail = body[:end], body[end:]
    for name in ('reset', 'status', 'band'):
        tail = re.sub(r'\*' + name + r'\b', name + '[slot]', tail)
        tail = prior.replace(tail, '            ' + name + '++;\n', '')
    return head + tail


def retain_difficulty(body, variable):
    body = prior.replace(body, '                    if (D_800872D0[D_800E0BD0] < value)',
        '                    %s = D_800E0BD0;\n                    if (D_800872D0[%s] < value)' % (variable, variable))
    body = prior.replace(body, '                        previousTimer = -1;\n'
        '                        /* Read back through the retained byte cursor. */',
        '                        previousTimer = -1;\n                        %s = D_800E0BD0;\n'
        '                        /* Read back through the retained byte cursor. */' % variable)
    return prior.replace(body, '                    limit = D_800872C4[D_800E0BD0];',
                         '                    limit = D_800872C4[%s];' % variable)


def forms():
    body = prior.SELECTED
    _, _, rows = declarations(body)
    top = ['offset', 'slot', 'actor', 'first', 'bit', 'group', 'actorAction',
           'changed', 'owner', 'previousTimer', 'value', 'started', 'active', 'seen', 'count',
           'expired', 'groups', 'latches', 'actions', 'otherActor', 'states', 'elapsed',
           'timers', 'cooldowns', 'timeouts', 'events', 'context', 'groupCounts', 'scores', 'idle']
    rest = [n for n in rows if n not in top]
    result = [('observed-top-homes', ordered(body, top + rest))]
    compact = ['steering', 'limit', 'flags', 'halfWidth', 'counter', 'row', 'reset', 'status', 'band']
    result.append(('observed-top-compact-tail', ordered(body, top + compact)))
    swap = top.copy()
    swap[0], swap[1] = swap[1], swap[0]
    result.append(('observed-top-slot-first', ordered(body, swap + compact)))
    for name, candidate in result.copy():
        result.append((name + '-word-action', prior.replace(candidate, '    u8 actorAction;',
                                                           '    s32 actorAction;')))
    for label, indexed in (('byte', False), ('index', True)):
        body = restore_spilled_cursors(prior.SELECTED, indexed)
        _, _, expanded = declarations(body)
        tail = [n for n in expanded if n not in top]
        result.append(('spilled-' + label + '-cursors', ordered(body, top + tail)))
    body = restore_spilled_cursors(prior.SELECTED)
    tail = ['steering', 'limit', 'flags', 'halfWidth', 'counter', 'row', 'reset',
            'timer', 'cooldown', 'state', 'event', 'eventByte', 'status', 'band', 'action']
    result.append(('spilled-byte-homes', ordered(body, top + tail)))
    body = compact_dead_scalars(restore_spilled_cursors(prior.SELECTED))
    _, _, expanded = declarations(body)
    result.append(('spilled-byte-compact-scalars', ordered(body, top + [n for n in expanded if n not in top])))
    tail = ['steering', 'limit', 'flags', 'row', 'eventByte', 'reset', 'timer',
            'cooldown', 'state', 'event', 'status', 'band', 'action']
    result.append(('spilled-byte-compact-homes', ordered(body, top + tail)))
    body = compact_limit(restore_spilled_cursors(prior.SELECTED))
    _, _, expanded = declarations(body)
    result.append(('spilled-byte-inline-limit', ordered(body, top + [n for n in expanded if n not in top])))
    full = restore_spilled_cursors(prior.SELECTED)
    body = prior.replace(full, '    s32 halfWidth;\n', '').replace('halfWidth', 'value')
    _, _, expanded = declarations(body)
    result.append(('spilled-byte-reused-width', ordered(body, top + [n for n in expanded if n not in top])))
    body = prior.replace(full, '    s32 *counter;\n', '')
    body = prior.replace(body, '                        counter = groupCounts + group;\n'
        '                        *counter -= 1;', '                        groupCounts[group] -= 1;')
    body = prior.replace(body, '                                counter = groupCounts + owner;\n'
        '                                *counter += 1;', '                                groupCounts[owner] += 1;')
    _, _, expanded = declarations(body)
    result.append(('spilled-byte-inline-counters', ordered(body, top + [n for n in expanded if n not in top])))
    body = indexed_outputs(prior.SELECTED)
    result.append(('indexed-output-bases', ordered(body, top + [n for n in declarations(body)[2] if n not in top])))
    body = indexed_outputs(restore_spilled_cursors(prior.SELECTED))
    result.append(('spilled-byte-indexed-outputs', ordered(body, top + [n for n in declarations(body)[2] if n not in top])))
    base = result[0][1]
    result.append(('observed-homes-owner-difficulty', retain_difficulty(base, 'owner')))
    result.append(('observed-homes-limit-difficulty', retain_difficulty(base, 'limit')))
    return result


SELECTED = re.sub(r'\bowner\b', 'selector', dict(forms())['observed-homes-owner-difficulty'])
RAW_SHA256 = '260a9fc2acbfa79a5348dda1a6589ca3ac73b81ea6aeda4c90798a4f9c52fb51'
MATCHED_HOMES = {n: at for n, at in TARGET_HOMES.items() if n not in ('reset', 'status', 'band')}


def debug_homes(obj):
    with patch.object(debug.route, 'FUNCTION', FUNCTION):
        result = debug.debug_locals(obj)
    homes = {}
    for name, info in result['locals'].items():
        if info['storage'] != '5' or info['value'] >= 0:
            raise ValueError('Unexpected actor-tick local storage class: ' + name)
        homes[name] = result['frame'] + info['value']
    return result['frame'], homes


def compile_candidate(root, output, name, body):
    row, words = prior.compile_candidate(root, output, name, body)
    frame, homes = debug_homes(output / (name + '.o'))
    if frame != row['frame']:
        raise ValueError('Actor-tick debug/emitted frames disagree')
    row['homes'] = homes
    row['matched_homes'] = [n for n, at in TARGET_HOMES.items() if homes[n] == at]
    (output / (name + '-receipt.json')).write_text(json.dumps(row, indent=2) + '\n')
    return row, words


def qualify_owner(root, output):
    with patch.object(prior, 'SELECTED', SELECTED), patch.object(prior, 'RAW_SHA256', RAW_SHA256):
        return prior.qualify_owner(root, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--names', nargs='*')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD
    prior.prior.freeze(root, output)
    candidates = forms()
    if args.names:
        if not set(args.names) <= dict(candidates).keys():
            parser.error('unknown actor-tick home candidate')
        candidates = [(n, b) for n, b in candidates if n in args.names]
    for name, body in candidates:
        row, _ = compile_candidate(root, output, name, body)
        print(json.dumps({k: row[k] for k in ('name', 'body_words', 'frame', 'aligned_differences',
                                             'raw_sha256', 'matched_homes', 'diagnostics')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
