"""Real local-declaration and skip-path screens for the complete pickup update."""

import json
import itertools
from pathlib import Path
import struct

from tools.experiments import game_pickup_state_update_candidates as core
from tools.pad_generated_object import parse_object


BUILD = core.BUILD + '/lifetimes'


def shape(obj):
    text, functions, relocations = parse_object(obj)
    item = functions[core.FUNCTION]
    words = struct.unpack('>%dI' % (item['size'] // 4), text[item['value']:item['value'] + item['size']])
    bindings = {at - item['value']: rows for at, rows in relocations.items()
        if item['value'] <= at < item['value'] + item['size']}
    calls = {name: at // 4 for at, rows in bindings.items()
        for kind, name in rows if kind == 'R_MIPS_26' and name in ('func_15033E28', 'func_15086CBC')}

    def outputs(name, registers):
        i = calls[name]
        values = {}
        for w in words[max(0, i - 5):i + 2]:
            if w >> 26 == 9 and w >> 21 & 31 == 29 and w >> 16 & 31 in registers:
                values[w >> 16 & 31] = w & 65535
        if set(values) != set(registers):
            raise ValueError(('Unrecognized private output arguments', name, values))
        return [values[r] for r in registers]

    pointer_stores = [w & 65535 for w in words[16:40] if w >> 26 == 43 and w >> 21 & 31 == 29]
    zero_stores = [w & 65535 for w in words[:20] if w >> 16 == 0xAFA0]
    return dict(frame=(-words[0]) & 65535, player=zero_stores[0],
        pointers=pointer_stores, attached=outputs('func_15033E28', (5,))[0],
        coordinates=outputs('func_15086CBC', (5, 6, 7)))


def declarations(body, moved):
    marker = '    state = (u8 *)D_800D23B0;'
    head, tail = body.split(marker, 1)
    for line in moved:
        if head.count(line + '\n') != 1:
            raise ValueError('Not one real local declaration: ' + line)
        head = head.replace(line + '\n', '', 1)
    return head.replace('    s32 player;\n', '    s32 player;\n' + ''.join(s + '\n' for s in moved), 1) + marker + tail


def candidates():
    body = core.SELECTED
    head = body.split('    state = (u8 *)D_800D23B0;', 1)[0]
    scalars = [line for line in head.splitlines()
        if line.startswith(('    s32 ', '    s16 ')) and '*' not in line and 'player;' not in line]
    for count in range(len(scalars) + 1):
        yield 'scalar-prefix-' + str(count), declarations(body, scalars[:count])
    yield 'retail-declarations', retail_declarations(body)


def retail_declarations(body):
    marker = '    state = (u8 *)D_800D23B0;'
    head, tail = body.split(marker, 1)
    groups = (
        ('    s32 player;\n', ('    s32 count;',)),
        ('    f32 x;\n', ('    s32 desired;', '    s32 previous;', '    s32 animation;',
            '    s32 found;', '    s32 attachedCount;', '    s32 i;', '    s32 index;')),
        ('    s32 *owners;\n', ('    s32 owner;', '    s32 node;', '    s32 chosen;')),
        ('    s32 *kinds;\n', ('    s16 mode;',)),
    )
    for anchor, lines in groups:
        if head.count(anchor) != 1:
            raise ValueError('Not one declaration anchor: ' + anchor)
        for line in lines:
            if head.count(line + '\n') != 1:
                raise ValueError('Not one real scalar declaration: ' + line)
            head = head.replace(line + '\n', '', 1)
        head = head.replace(anchor, ''.join(line + '\n' for line in lines) + anchor, 1)
    return head + marker + tail


DIRECT_HOMES = retail_declarations(core.SELECTED)


def selector_lifetime(body):
    head, tail = body.split('    D_80087340++;', 1)
    if tail.count('            selectors += 4;') != 1 or tail.count('selectors[3]') != 1:
        raise ValueError('Unknown pickup selector cursor')
    tail = tail.replace('        scale = D_8009DA90;',
        '        scale = D_8009DA90;\n        scan = selectors;', 1)
    tail = tail.replace('selectors[3]', 'scan[3]').replace('            selectors += 4;', '            scan += 4;')
    return head + '    D_80087340++;' + tail


def retail_skip(body):
    condition = '            if (mode != 0xB9 || actor[0x128] == 0) {'
    if body.count(condition) != 1:
        raise ValueError('Unknown player skip predicate')
    return body.replace(condition,
        '            if (mode == 0xB9 && actor[0x128] != 0) {\n'
        '                /* Keep this player unchanged, including the cached count. */\n'
        '            } else {', 1)


def rotating_selector(body):
    old = '    D_80087340++;\n    if (D_80087340 >= count) {'
    if body.count(old) != 1:
        raise ValueError('Unknown signed rotating selector')
    return body.replace(old, '    chosen = (s8)(D_80087340 + 1);\n'
        '    D_80087340 = chosen;\n    if (chosen >= count) {', 1)


LIVE_CURSOR = selector_lifetime(retail_skip(DIRECT_HOMES))
SELECTED = rotating_selector(LIVE_CURSOR)


def role_candidates():
    marker = '    D_80087340++;'
    initial, tail = DIRECT_HOMES.split(marker, 1)
    for owner, effect, cleanup in itertools.product((False, True), repeat=3):
        head = initial
        if owner:
            head = head.replace('index = owners[player];', 'chosen = owners[player];').replace(
                'if (index != -1)', 'if (chosen != -1)').replace('desired = kinds[index];', 'desired = kinds[chosen];')
        if effect:
            begin = head.index('                    if (attachedCount != 0')
            end = head.index('                    if (animation != 0x55)', begin)
            segment = head[begin:end].replace('index', 'node')
            head = head[:begin] + segment + head[end:]
        if cleanup:
            begin = head.index('                    if (animation != 0x55)')
            segment = head[begin:].replace('index = *(s32 *)', 'count = *(s32 *)').replace(
                'if (index < 25)', 'if (count < 25)').replace('scan = D_800CC2D0 + index *', 'scan = D_800CC2D0 + count *')
            head = head[:begin] + segment
        yield 'roles-%d%d%d' % (owner, effect, cleanup), head + marker + tail


def skip_candidates():
    condition = '            if (mode != 0xB9 || actor[0x128] == 0) {'
    footer = '            player++;\n            actor += 0x32C;\n        } while (player < count);'
    for role, body in role_candidates():
        if role not in ('roles-000', 'roles-010', 'roles-111'):
            continue
        yield role + '-empty-else', body.replace(condition,
            '            if (mode == 0xB9 && actor[0x128] != 0) {\n            } else {', 1)
        yield role + '-skip-goto', body.replace(condition,
            '            if (mode == 0xB9 && actor[0x128] != 0) {\n'
            '                player++;\n                goto advance_actor;\n            } else {', 1).replace(
                footer, '            player++;\nadvance_actor:\n            actor += 0x32C;\n        } while (player < count);', 1)
        yield role + '-for-continue', body.replace('        do {\n            mode =',
            '        for (; player < count; player++, actor += 0x32C) {\n            mode =', 1).replace(
                condition, '            if (mode == 0xB9 && actor[0x128] != 0) {\n'
                '                continue;\n            } else {', 1).replace(footer, '        }', 1)


def constant_candidates():
    body = dict(skip_candidates())['roles-000-empty-else']
    head, tail = body.split('    D_80087340++;', 1)
    for a, b in (('node', 'chosen'), ('owner', 'chosen'), ('owner', 'node')):
        for hinted in (False, True):
            result = head.replace('        scale = 1.0f;',
                '        scale = 1.0f;\n        ' + b + ' = 0x22;\n        ' + a + ' = 0x2A;', 1)
            result = result.replace('index != 0x2A', 'index != ' + a).replace('index != 0x22', 'index != ' + b)
            if hinted:
                result = result.replace('    s32 ' + a + ';', '    register s32 ' + a + ';').replace(
                    '    s32 ' + b + ';', '    register s32 ' + b + ';')
            yield 'constants-' + a + '-' + b + '-' + str(hinted), result + '    D_80087340++;' + tail


def cursor_candidates():
    for name, body in skip_candidates():
        yield name + '-live-cursor', selector_lifetime(body)
    for position in ('after-index', 'before-index'):
        body = LIVE_CURSOR.replace('        scan = selectors;\n', '', 1)
        anchor = '    index = 0;\n'
        replacement = anchor + '    scan = selectors;\n' if position == 'after-index' else '    scan = selectors;\n' + anchor
        yield 'cursor-' + position, body.replace(anchor, replacement, 1)


def original(root, output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('PickupOriginal', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-pickup-update',
        (root / 'conker/asm/B3020.s').read_text(), core.FUNCTION)


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD / 'screen'
    rows = []
    for name, body in candidates():
        obj, _, row = core.compile_candidate(root, output, name, body)
        row.update(name=name, homes=shape(obj))
        rows.append(row)
        print(name, row)
    (output / 'screens.json').write_text(json.dumps(rows, indent=2) + '\n')
