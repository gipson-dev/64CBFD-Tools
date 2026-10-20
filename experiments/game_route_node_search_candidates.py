"""Recover the complete five-neighbor route search without installing it."""

import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path
from unittest.mock import patch

from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner, function_span
from tools.pad_generated_object import parse_object


FUNCTION, ENTRY, ROM, WORDS = 'func_15086364', 0x15086364, 0xB3814, 539
SOURCE, OWNER = 'conker/src/game/generated_B3020.c', 'generated_B3020'
BUILD = 'conker/build/game-route-node-search'
INPUTS = {
    SOURCE: 'be56a04b3aa3c7b1d3f2b1d03e8da6170f79c6ba5ca430cffd392a832963feb8',
    'conker/retail_word_patches.us.csv': 'c1b76ce25dbd18ca06aee817299da8588024ba0e48006a7ca20aabb6dffe4a15',
    'conker/build/conker.us.elf': '51a5f15b5a0834290ea21451d45c3d24d8327930c92a1d8337c0c72f81c82948',
    'conker/conker.us.bin': 'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
    'conker/asm/B3020.s': '26ef139d5592329ed22f9287267c13fefadf7f17290bc5ef1085cbe20e80b187',
    'conker/Makefile': 'cf6de057267055cf5ad789e72426b7433c0bfe37d04ae56c241332cf2f2febf4',
    'conker/progress.csv': '16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be',
}
DECLARATIONS = '''#include <ultra64.h>
extern s16 D_80087290;
extern u8 D_80087298;
extern u8 *D_800D2350;
extern s32 D_800D2354;
s32 func_15086C70(s32);
f32 func_15086BD0(s32, s32);
'''

# Capacities follow the five contiguous retail workspace ranges, not donor types.
INITIAL = '''/* Search five-neighbor routes, then choose a waypoint and accumulate distance. */
s32 func_15086364(s32 start, s8 goalCount, s8 avoidCount, u8 *goals, u8 *avoid) {
    s32 costs[200];
    u8 frontier[200];
    u8 parents[200];
    u8 path[64];
    u8 special[64];
    u8 *nodes;
    u8 *node;
    u8 *cursor;
    u8 *other;
    s32 frontierCount;
    s32 pathCount;
    s32 selected;
    s32 minimum;
    s32 current;
    s32 next;
    s32 penalty;
    s32 proposed;
    s32 currentCost;
    s32 hole;
    s32 found;
    s32 i;
    s32 edge;
    s32 index;
    s32 previous;
    s32 answer;
    s32 chosen;
    f32 dx;
    f32 dy;
    f32 dz;
    f32 distance;

    D_80087298 = 0xFF;
    D_800D2354 = 0;
    if (goalCount <= 0) {
        return 0xFF;
    }
    if (start < 0 || start >= D_80087290) {
        return 0xFF;
    }
    found = 0;
    for (i = 0; i < goalCount; i++) {
        if (start == goals[i]) {
            found = 1;
        }
    }
    frontierCount = 0;
    if (found != 0) {
        D_80087298 = start;
        return start;
    }
    for (i = 0; i < D_80087290; i++) {
        costs[i] = 1000000;
    }
    nodes = D_800D2350;
    node = nodes + start * 16;
    cursor = node;
    edge = 0;
    do {
        next = cursor[9];
        edge++;
        if (next != 0xFF) {
            penalty = 0;
            for (i = 0; i < avoidCount; i++) {
                if (next == avoid[i]) {
                    penalty = 5000;
                }
            }
            frontier[frontierCount] = next;
            other = nodes + next * 16;
            parents[cursor[9]] = start;
            dx = (f32)(*(s16 *)(node + 0) - *(s16 *)(other + 0));
            dy = (f32)(*(s16 *)(node + 2) - *(s16 *)(other + 2));
            dz = (f32)(*(s16 *)(node + 4) - *(s16 *)(other + 4));
            frontierCount++;
            /* Only the opening edge is narrowed to a signed halfword. */
            costs[cursor[9]] = (s16)(s32)sqrtf((dx * dx + dy * dy) + dz * dz) + penalty;
        }
        cursor++;
    } while (edge != 5);
    pathCount = 0;
    for (;;) {
        minimum = 1000000;
        selected = 0xFF;
        for (i = 0; i < frontierCount; i++) {
            if (frontier[i] != 0xFF && costs[frontier[i]] < minimum) {
                minimum = costs[frontier[i]];
                selected = i;
            }
        }
        if (selected == 0xFF) {
            break;
        }
        if (frontierCount == selected + 1) {
            frontierCount--;
        }
        current = frontier[selected];
        frontier[selected] = 0xFF;
        found = 0;
        for (i = 0; i < goalCount; i++) {
            if (current == goals[i]) {
                found = 1;
            }
        }
        if (found != 0) {
            D_80087298 = current;
            next = current;
            while (next != start) {
                path[pathCount] = next;
                next = parents[next];
                pathCount++;
            }
            path[pathCount] = next;
            pathCount++;
            break;
        }
        node = nodes + current * 16;
        currentCost = costs[current];
        cursor = node;
        edge = 0;
        do {
            next = cursor[9];
            edge++;
            if (next != 0xFF && next != start) {
                penalty = 0;
                for (i = 0; i < avoidCount; i++) {
                    if (next == avoid[i]) {
                        penalty = 5000;
                    }
                }
                other = nodes + next * 16;
                dx = (f32)(*(s16 *)(node + 0) - *(s16 *)(other + 0));
                dy = (f32)(*(s16 *)(node + 2) - *(s16 *)(other + 2));
                dz = (f32)(*(s16 *)(node + 4) - *(s16 *)(other + 4));
                proposed = (s32)sqrtf((dx * dx + dy * dy) + dz * dz) + currentCost + penalty;
                if (proposed < costs[next]) {
                    hole = 0xFF;
                    for (i = 0; i < frontierCount; i++) {
                        if (hole == 0xFF && frontier[i] == 0xFF) {
                            hole = i;
                        }
                        if (next == frontier[i]) {
                            costs[next] = proposed;
                            parents[next] = current;
                            i = frontierCount + 10;
                        }
                    }
                    if (i == frontierCount) {
                        parents[next] = current;
                        costs[next] = proposed;
                        if (hole == 0xFF) {
                            hole = frontierCount;
                            frontierCount++;
                        }
                        frontier[hole] = next;
                    }
                }
            }
            cursor++;
        } while (edge != 5);
    }
    if (pathCount < 2) {
        return 0xFF;
    }
    index = pathCount - 2;
    answer = path[index];
    for (i = 0; i <= index + 1; i++) {
        special[i] = func_15086C70(path[i]) != 0;
    }
    distance = 0.0f;
    chosen = 0;
    if (special[index] != 0 &&
        (special[index + 1] == 0 || (index > 0 && special[index - 1] == 0))) {
        chosen = 1;
    }
    while (index > 0) {
        previous = index - 1;
        if (special[index - 1] != 0) {
            while (previous >= 0 && special[previous] != 0) {
                previous--;
            }
            previous++;
        }
        distance += func_15086BD0(path[index], path[previous]);
        if (chosen == 0) {
            chosen = 1;
            if (special[index] != 0) {
                answer = path[previous];
            }
        }
        index = previous;
    }
    D_800D2354 = (s32)distance;
    return answer;
}
'''


def workspace_source(body, first_scalars):
    head, tail = body.split('    D_80087298 =', 1)
    lines = head.splitlines(keepends=True)
    arrays = [line for line in lines[2:] if '[' in line]
    scalars = [line for line in lines[2:] if line.strip() and '[' not in line]
    if len(arrays) != 5 or not 0 <= first_scalars <= len(scalars):
        raise ValueError('Unknown route-search workspace declarations')
    return ''.join(lines[:2] + scalars[:first_scalars] + arrays + scalars[first_scalars:]) + '\n    D_80087298 =' + tail


def candidates():
    yield 'initial', INITIAL
    opening = '''    found = 0;
    for (i = 0; i < goalCount; i++) {
        if (start == goals[i]) {
            found = 1;
        }
    }
    frontierCount = 0;
    if (found != 0) {'''
    inverted = opening.replace('found = 0;', 'found = 1;', 1).replace(
        '            found = 1;', '            found = 0;', 1).replace('if (found != 0)', 'if (found == 0)')
    if INITIAL.count(opening) != 1:
        raise ValueError('Unknown route-search opening membership scan')
    for mask in range(1, 16):
        body = INITIAL
        if mask & 1:
            body = body.replace(opening, inverted)
        if mask & 2:
            body = body.replace('    s32 answer;', '    u8 answer;')
        if mask & 4:
            body = body.replace('    s32 index;\n', '').replace('index', 'pathCount')
        if mask & 8:
            body = body.replace('    s32 answer;\n', '').replace('    u8 answer;\n', '').replace('answer', 'current')
        yield 'lifetimes-%02d' % mask, body


SELECTED = workspace_source(dict(candidates())['lifetimes-13'], 21).replace(
    '    for (i = 0; i < D_80087290; i++) {\n        costs[i] = 1000000;\n    }',
    '    if (D_80087290 > 0) {\n        other = (u8 *)costs;\n        cursor = other + D_80087290 * 4;\n        do {\n            *(s32 *)other = 1000000;\n            other += 4;\n        } while (other < cursor);\n    }')
# Exchange two real word-sized homes without moving any workspace array.
SELECTED = SELECTED.replace('    s32 proposed;', '    f32 distance;', 1).replace(
    '    f32 dz;\n    f32 distance;', '    f32 dz;\n    s32 proposed;', 1)
SELECTED_NORMAL_SHA = '76c2344e05cad317bd98cd766b95a2d6d6b43fc1e9970c0bf80bce195224d27f'


def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    values = {}
    for name, digest in INPUTS.items():
        data = (root / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('Route-search input changed: ' + name)
        path = output / ('before-' + name.replace('/', '_'))
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Route-search snapshot changed: ' + name)
        if not path.exists():
            path.write_bytes(data)
        values[name] = data
    return values


def payload(obj):
    text, functions, bindings = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, w in enumerate(words) if w == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero route-search alignment tail')
    return raw[:end * 4], {at - f['value']: rows for at, rows in bindings.items()
                          if f['value'] <= at < f['value'] + end * 4}


def compile_profile(root, output, unit, name, normal=False):
    run, commands = subprocess.run, []

    def profile(argv, **kwargs):
        if argv[0] == str(root / 'ido/ido5.3_recomp/cc'):
            argv = list(argv)
            if not normal:
                argv.insert(argv.index('-O2'), '-Wo,-loopunroll,0')
            commands.append(argv)
        return run(argv, **kwargs)

    with patch.object(subprocess, 'run', side_effect=profile):
        obj, diagnostics = compile_owner(root, output, unit, name)
    if len(commands) != 1:
        raise ValueError('Unexpected route-search compiler invocation')
    (output / (name + '-command.json')).write_text(json.dumps(commands[0], indent=2) + '\n')
    return obj, diagnostics


def recovered_owner(before, body=SELECTED):
    lo, hi = function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_15086364() {\n    return 0;\n}':
        raise ValueError('Unknown route-search predecessor')
    result = before[:lo] + DECLARATIONS.split('\n', 1)[1] + '\n' + body + before[hi:]
    return result.replace('s32 func_15086364();',
                          's32 func_15086364(s32, s8, s8, u8 *, u8 *);')


def compile_candidate(root, output, name='selected', body=SELECTED, normal=False, whole=False):
    values = freeze(root, output)
    unit = recovered_owner(values[SOURCE].decode(), body) if whole else DECLARATIONS + '\n' + body
    obj, diagnostics = compile_profile(root, output, unit, name, normal)
    raw, bindings = payload(obj)
    image, functions = link_owner(root, output, obj, OWNER)
    at = functions[FUNCTION]['value']
    words = list(struct.unpack_from('>%dI' % (len(raw) // 4), image, at))
    truth = struct.unpack_from('>539I', values['conker/conker.us.bin'], ROM)
    row = dict(words=len(words), frame=(-words[0]) & 65535,
               differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
               bindings=sum(map(len, bindings.values())), raw_SHA256=hashlib.sha256(raw).hexdigest(),
               diagnostics=diagnostics, normal=normal, installed=False, matching_credit=0)
    (output / (name + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--normal', action='store_true')
    parser.add_argument('--names', nargs='*', default=['selected'])
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    forms = dict(candidates(), selected=SELECTED)
    if not set(args.names) <= forms.keys():
        parser.error('Unknown route-search candidate')
    for name in args.names:
        _, _, row = compile_candidate(root, root / BUILD, name, forms[name], normal=args.normal)
        print(json.dumps(dict(row, name=name)), flush=True)


if __name__ == '__main__':
    main()
