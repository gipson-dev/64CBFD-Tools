"""Recover the route search's shared outer-loop selection/scan sentinel."""

import argparse
import json
from pathlib import Path

from tools.experiments import game_route_node_search_candidates as prior


BUILD = prior.BUILD + '/loop'
FUNCTION, ENTRY, ROM, WORDS = prior.FUNCTION, prior.ENTRY, prior.ROM, prior.WORDS
LOOP = '''    do {
        minimum = 1000000;
        selected = 0xFF;
        for (i = 0; i < frontierCount; i++) {
            if (frontier[i] != 0xFF && costs[frontier[i]] < minimum) {
                minimum = costs[frontier[i]];
                selected = i;
            }
        }
        if (selected != 0xFF) {
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
                selected = 0xFF;
            } else {
                node = nodes + current * 16;
                currentCost = costs[current];
                cursor = node;
                edge = 0;
                selected = 0;
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
                            for (selected = 0; selected < frontierCount; selected++) {
                                if (hole == 0xFF && frontier[selected] == 0xFF) {
                                    hole = selected;
                                }
                                if (next == frontier[selected]) {
                                    costs[next] = proposed;
                                    parents[next] = current;
                                    selected = frontierCount + 10;
                                }
                            }
                            if (selected == frontierCount) {
                                parents[next] = current;
                                costs[next] = proposed;
                                if (hole == 0xFF) {
                                    hole = frontierCount;
                                    frontierCount++;
                                }
                                frontier[hole] = next;
                            }
                            selected = 0;
                        }
                    }
                    cursor++;
                } while (edge != 5);
            }
        }
    } while (selected != 0xFF);
'''


def replace_loop(loop):
    before = prior.SELECTED
    opening, closing = '    for (;;) {\n', '    if (pathCount < 2) {'
    if before.count(opening) != 1 or before.count(closing) != 1:
        raise ValueError('Unknown route-search outer-loop predecessor')
    lo, hi = before.index(opening), before.index(closing)
    return before[:lo] + loop + before[hi:]


SENTINEL = replace_loop(LOOP)


def coordinate_captures(body):
    old = '''                        penalty = 0;
                        for (i = 0; i < avoidCount; i++) {'''
    new = '''                        s32 originX = *(s16 *)(node + 0);
                        s32 originY = *(s16 *)(node + 2);
                        s32 originZ = *(s16 *)(node + 4);
                        penalty = 0;
                        for (i = 0; i < avoidCount; i++) {'''
    if body.count(old) != 1:
        raise ValueError('Unknown route-search relaxation scan')
    body = body.replace(old, new)
    start = body.index('                        s32 originX')
    for axis, offset in (('X', 0), ('Y', 2), ('Z', 4)):
        old = '*(s16 *)(node + %d) - *(s16 *)(other + %d)' % (offset, offset)
        new = 'origin%s - *(s16 *)(other + %d)' % (axis, offset)
        body = body[:start] + body[start:].replace(old, new, 1)
    return body


SELECTED = coordinate_captures(SENTINEL)
NORMAL_SHA = '1afc816d05f80feb62d85d47c0aa69bc6c0bfbadd49377851b170b211e129443'


def candidates():
    yield 'shared-sentinel', SENTINEL
    yield 'captured-coordinates', SELECTED
    separate = LOOP.replace('                            for (selected =', '                            for (i =')
    start, stop = separate.index('                            for (i ='), separate.index('                            selected = 0;')
    separate = separate[:start] + separate[start:stop].replace('selected', 'i') + separate[stop:]
    yield 'separate-scan', replace_loop(separate)
    yield 'do-forever', prior.SELECTED.replace('    for (;;) {', '    do {', 1).replace(
        '    }\n    if (pathCount < 2)', '    } while (1);\n    if (pathCount < 2)', 1)


def compile_candidate(root, output, name='selected', body=SELECTED, normal=True, whole=False):
    return prior.compile_candidate(root, output, name, body, normal, whole)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--names', nargs='*')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.names is not None and not set(args.names) <= dict(candidates()).keys():
        parser.error('Unknown route-search loop candidate')
    for name, body in candidates():
        if args.names is None or name in args.names:
            _, _, row = compile_candidate(root, root / BUILD, name, body)
            print(json.dumps(dict(row, name=name)), flush=True)


if __name__ == '__main__':
    main()
