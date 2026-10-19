"""Screen real draw-index lifetimes and positive-count cursor initialization."""

import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_state_tick_homes as prior


BUILD = prior.BUILD + '/draw'


def draw_index(body, local):
    head, marker, tail = body.rpartition('        actor = D_800CC2D0;\n')
    if not marker:
        raise ValueError('Missing actor-tick draw-loop anchor')
    if local == 'drawIndex':
        head = prior.prior.replace(head, '    s32 halfWidth;\n',
                                  '    s32 halfWidth;\n    s32 drawIndex;\n')
    return head + marker + tail.replace('slot', local)


def positive_cursors(body):
    lines = ''.join('    %s = (s32 *)(D_800D23B0 + 0x%X);\n' % (name, offset)
                    for name, offset in (('reset', 0x1C), ('status', 0x39C), ('band', 0x9C)))
    return prior.prior.replace(body, lines + '    if (count > 0) {\n',
        '    if (count > 0) {\n' + ''.join('    ' + line for line in lines.splitlines(keepends=True)))


def byte_tables(body):
    for table in prior.prior.TABLES:
        body = body.replace(table + '[slot]', '*(s32 *)((u8 *)' + table + ' + offset)')
    return prior.prior.replace(body,
        '/* Read back through the retained byte cursor. */\n'
        '                        value = *(s32 *)((u8 *)timers + offset);',
        '/* Read back through the retained slot cursor. */\n'
        '                        value = timers[slot];')


def draw_homes(body):
    _, _, declarations = prior.declarations(body)
    order = list(declarations)
    i, j = order.index('selector'), order.index('status')
    order[i], order[j] = order[j], order[i]
    return prior.ordered(body, order)


def eager_addresses(body):
    body = prior.prior.replace(body, '    if (count > 0) {',
        '    otherActor = (u8 *)D_800D23B0 + 0x1C;\n'
        '    row = (u8 *)D_800D23B0 + 0x39C;\n'
        '    context = (u8 *)D_800D23B0 + 0x9C;\n'
        '    if (count > 0) {')
    for name, offset, local in (('reset', 0x1C, 'otherActor'), ('status', 0x39C, 'row'),
                                ('band', 0x9C, 'context')):
        body = prior.prior.replace(body, '        %s = (s32 *)(D_800D23B0 + 0x%X);' % (name, offset),
                                   '        %s = (s32 *)%s;' % (name, local))
    return body


def retained_latch(body, position='before-timer'):
    body = body.replace('*(s32 *)((u8 *)latches + offset)', '*(s32 *)context')
    anchor = {'before-actor': '                actor = D_800CC2D0 + slot * 0x32C;',
              'before-group': '                group = *(s32 *)((u8 *)groups + offset);',
              'before-timer': '                previousTimer = *(s32 *)((u8 *)timers + offset);'}[position]
    return prior.prior.replace(body, anchor, '                context = (u8 *)latches + offset;\n' + anchor)


def forms():
    result = [('positive-cursors', positive_cursors(prior.SELECTED))]
    for local in ('drawIndex', 'selector', 'first', 'group', 'value', 'count', 'expired', 'started'):
        body = draw_index(prior.SELECTED, local)
        result.append(('draw-' + local, body))
        result.append(('positive-draw-' + local, positive_cursors(body)))
    body = positive_cursors(draw_index(prior.SELECTED, 'selector'))
    body = byte_tables(body)
    result.append(('positive-draw-selector-byte-tables', body))
    result.append(('draw-home', draw_homes(body)))
    result.append(('word-action', body.replace('    u8 actorAction;', '    s32 actorAction;')))
    body = draw_homes(body).replace('    u8 actorAction;', '    s32 actorAction;')
    result.append(('draw-home-word-action', body))
    body = eager_addresses(body)
    result.append(('eager-addresses', body))
    for position in ('before-actor', 'before-group', 'before-timer'):
        result.append(('latch-' + position, retained_latch(body, position)))
    return result


SELECTED = eager_addresses(dict(forms())['draw-home-word-action'])
# Both lifetimes hold addresses/indices, not only a second actor or difficulty.
SELECTED = SELECTED.replace('otherActor', 'address').replace('selector', 'index')
SELECTED = retained_latch(SELECTED)
RAW_SHA256 = '9fa41b55435921115dfe029d37b330f90b787329f0b8b83dfb3630a3b242ffd9'
MATCHED_HOMES = dict(prior.MATCHED_HOMES, index=0xA0, actorAction=0x104)


def compile_candidate(root, output, name, body):
    row, words = prior.compile_candidate(root, output, name, body)
    row['matched_homes'] = [n for n, at in MATCHED_HOMES.items() if row['homes'].get(n) == at]
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
    prior.prior.prior.freeze(root, output)
    candidates = forms() + [('selected', SELECTED)]
    if args.names:
        if not set(args.names) <= dict(candidates).keys():
            parser.error('unknown actor-tick draw candidate')
        candidates = [(n, b) for n, b in candidates if n in args.names]
    for name, body in candidates:
        row, _ = compile_candidate(root, output, name, body)
        print(json.dumps({k: row[k] for k in ('name', 'body_words', 'frame', 'aligned_differences',
                                             'raw_sha256', 'matched_homes', 'diagnostics')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
