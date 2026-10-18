"""Test disjoint conversion/projection lifetimes, without invented qualifiers."""
import argparse
import json
from pathlib import Path
import re
import struct

from tools.experiments import game_route_actor_update_extent as prior

source = prior.source
BUILD = 'conker/build/game-route-actor-update-storage'


def coordinate_carrier(body, name):
    for offset, value in ((8, 'D_800D239C'), (10, 'D_800D23A0'), (12, 'D_800D23A4')):
        marker = '            *(s16 *)(D_800D2104[actor[0x13F]] + %d) = (s32)%s;' % (offset, value)
        body = prior.prior.replace_once(body, marker,
            '            %s = (s32)%s;\n' % (name, value) + marker.replace('(s32)' + value, name))
    return body


def conversion_forms():
    body = prior.selected()
    for name in ('i', 'again'):
        yield 'converted-' + name, coordinate_carrier(body, name)
    value = prior.prior.replace_once(body, '    s8 temporary;\n', '    s32 temporary;\n')
    yield 'converted-rank-id32', coordinate_carrier(value, 'temporary')
    marker = '        if (recordIndex < D_800D2398) {\n'
    start = body.index(marker) + len(marker)
    stop = body.index('    } else {\n        *(f32 *)record = 0.0f;', start)
    value = body[:start] + coordinate_carrier(body[start:stop], 'recordIndex') + body[stop:]
    yield 'converted-dead-argument-control', value
    for name, declaration in (('converted', '    s32 converted;\n'),
                              ('converted[0]', '    s32 converted[1];\n')):
        value = prior.prior.replace_once(body, '    f32 gain;\n', '    f32 gain;\n' + declaration)
        yield 'converted-' + ('array' if '[' in name else 'scalar'), coordinate_carrier(value, name)


def projection_forms():
    body = prior.selected()
    marker = '    } else {\n        *(f32 *)record = 0.0f;'
    head, tail = body.split(marker)
    head = prior.prior.replace_once(head, '    f32 positionX;\n', '    f32 startZ;\n    f32 positionX;\n')
    tail = re.sub(r'\bgain\b', 'startZ', tail)
    body = head + marker + tail
    yield 'projection-separate-startZ', body
    for old, new in (('cursor', 'actor'), ('temporary', 'refresh'), ('i', 'active')):
        value = prior.prior.merge_names(body, ((old, new),))
        yield 'projection-startZ-reuse-' + old, value


GROUPS = dict(conversions=conversion_forms, projection=projection_forms)


def screen(root, out, group):
    values = source.freeze(root, out)
    baseline, diagnostics = source.prior.compile_profile(root, out,
        values['conker/src/game/generated_B3020.c'].decode(), 'owner-before')
    if diagnostics:
        raise ValueError('Unexpected storage screen baseline diagnostics')
    truth = list(struct.unpack_from('>604I', values['conker/conker.us.bin'], source.ROM))
    rows = []
    for name, body in GROUPS[group]():
        _, words, row = source.measure(root, out, name, body, baseline)
        row.update(call_anchored_blocks=prior.call_blocks(truth, words),
            first15_words_exact=words[:15] == truth[:15], last11_words_exact=words[-11:] == truth[-11:],
            incoming_argument_write_control_only=name == 'converted-dead-argument-control')
        prior.disassemble(out, name, words)
        rows.append(row)
        print(json.dumps({key: row[key] for key in ('name', 'words', 'frame', 'differences',
            'raw_sha256', 'diagnostics', 'neighbors', 'first15_words_exact', 'last11_words_exact')}), flush=True)
    (out / (group + '-screens.json')).write_text(json.dumps(rows, indent=2) + '\n')
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', choices=GROUPS, default='conversions')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    screen(root, root / BUILD, args.group)
